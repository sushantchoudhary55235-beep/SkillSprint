"""Gamification Engine (docs/Phases.md §14).

Deterministic, server-side-only rewards:
- XP via the auditable ``xp_transactions`` ledger (profile.xp is the cached sum)
- Levels from a fixed threshold curve (backend authoritative)
- Streaks from qualifying learning activity (practice/assessment completion)
- Missions whose progress updates from real activity
- Badges awarded once, by rule evaluation — never by client request

Clients cannot POST XP; every award flows through award_xp() from a
validated server-side event.
"""
from datetime import date, datetime, timedelta, timezone

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.models.assessment import Attempt
from app.models.gamification import Badge, StudentBadge, XPTransaction
from app.models.mission import Mission, StudentMission
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile

# ------------------------------------------------------------------ XP rules
XP_COMPLETE_SESSION_BONUS = 25
XP_CORRECT_ANSWER = 5
XP_DAILY_QUIZ_BONUS = 50
XP_ASSESSMENT_COMPLETE = 100

logger = logging.getLogger("skillsprint.gamification")
XP_BADGE_DEFAULT = 50
XP_STREAK_MILESTONE = 25  # per 7-day milestone reached

# ------------------------------------------------------------------ levels
# Level thresholds: L1=0, L2=100, L3=250, L4=450 ... then +500/level.
LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200, 4000]
_LEVEL_STEP_BEYOND = 500

# ------------------------------------------------------------------ streaks
STREAK_MILESTONE_DAYS = 7


def level_for_xp(xp: int) -> int:
    """Deterministic level curve (docs/Phases.md §14.2)."""
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = i + 1
        else:
            break
    else:
        xp_over = xp - LEVEL_THRESHOLDS[-1]
        level = len(LEVEL_THRESHOLDS) + xp_over // _LEVEL_STEP_BEYOND
    return level


def level_progress(xp: int) -> tuple[int, int]:
    """(current level xp floor, next level xp needed).

    Within the table: floor = thresholds[lvl-1], ceiling = thresholds[lvl].
    Beyond the table each level spans _LEVEL_STEP_BEYOND XP (level 11:
    4000→4500, level 12: 4500→5000, ...).
    """
    lvl = level_for_xp(xp)
    if lvl <= len(LEVEL_THRESHOLDS):
        floor = LEVEL_THRESHOLDS[lvl - 1]
        ceiling = (
            LEVEL_THRESHOLDS[lvl]
            if lvl < len(LEVEL_THRESHOLDS)
            else LEVEL_THRESHOLDS[-1] + _LEVEL_STEP_BEYOND
        )
    else:
        # lvl 11 covers 4000–4500 (handled above); lvl 12+: 4500–5000, ...
        floor = LEVEL_THRESHOLDS[-1] + (lvl - len(LEVEL_THRESHOLDS)) * _LEVEL_STEP_BEYOND
        ceiling = floor + _LEVEL_STEP_BEYOND
    return floor, ceiling


class GamificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ XP

    def award_xp(
        self,
        student: StudentProfile,
        amount: int,
        activity_type: str,
        reference_id: int | None = None,
        description: str | None = None,
    ) -> int:
        """Append to the XP ledger and update the cached profile total.

        Duplicate protection: the same (student, activity_type, reference_id)
        cannot be rewarded twice.
        """
        if amount <= 0:
            return student.xp
        if reference_id is not None:
            dup = self.db.scalar(
                select(XPTransaction.id).where(
                    XPTransaction.student_id == student.id,
                    XPTransaction.activity_type == activity_type,
                    XPTransaction.reference_id == reference_id,
                )
            )
            if dup is not None:
                return student.xp

        self.db.add(XPTransaction(
            student_id=student.id,
            activity_type=activity_type,
            reference_id=reference_id,
            xp_amount=amount,
            description=description,
        ))
        try:
            self.db.flush()
        except IntegrityError:
            # DB-level idempotency: a concurrent request inserted the same
            # (student, activity_type, reference_id) first. Roll back THIS
            # flush only and treat as already-awarded.
            self.db.rollback()
            return student.xp
        student.xp += amount
        new_level = level_for_xp(student.xp)
        leveled_up = new_level > student.level
        student.level = new_level
        # Observability (Phase 23): every reward is traceable via the ledger
        # (authoritative) and one log line (auditing). Never logs tokens.
        logger.info(
            "XP awarded: student_id=%s amount=%s activity=%s reference_id=%s level=%s",
            student.id, amount, activity_type, reference_id, student.level,
        )
        if leveled_up:
            self.record_activity(student.id, "LEVEL_UP", reference_id=new_level,
                                 metadata={"level": new_level})
        return student.xp

    def xp_summary(self, student: StudentProfile) -> dict:
        floor, ceiling = level_progress(student.xp)
        return {
            "xp": student.xp,
            "level": student.level,
            "current_level_floor": floor,
            "next_level_xp": ceiling,
            "xp_to_next_level": max(0, ceiling - student.xp),
            "progress_percent": (
                round((student.xp - floor) / (ceiling - floor) * 100, 1)
                if ceiling > floor else 100.0
            ),
        }

    # ============================================================ STREAKS

    def _today(self) -> date:
        return datetime.now(timezone.utc).date()

    def touch_streak(self, student: StudentProfile) -> int:
        """Register a qualifying learning day; idempotent within the same day."""
        today = self._today()
        if student.last_activity_date == today:
            return student.current_streak
        if student.last_activity_date == today - timedelta(days=1):
            student.current_streak += 1
        else:
            student.current_streak = 1
        student.last_activity_date = today
        if student.current_streak > student.longest_streak:
            student.longest_streak = student.current_streak

        # Streak milestone XP: every 7 consecutive days
        if student.current_streak > 0 and student.current_streak % STREAK_MILESTONE_DAYS == 0:
            self.award_xp(
                student,
                XP_STREAK_MILESTONE,
                "STREAK_MILESTONE",
                reference_id=student.current_streak,
                description=f"{student.current_streak}-day streak",
            )
        self.record_activity(student.id, "STREAK_DAY", reference_id=student.current_streak)
        return student.current_streak

    # ============================================================ ACTIVITY LOG

    def record_activity(
        self,
        student_id: int,
        event_type: str,
        reference_id: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.db.add(ActivityEvent(
            student_id=student_id,
            event_type=event_type,
            reference_id=reference_id,
            metadata_json=metadata,
        ))

    # ============================================================ MISSIONS

    def ensure_daily_missions(self, student: StudentProfile) -> list[StudentMission]:
        """Assign today's active DAILY missions to the student (idempotent).

        Daily missions are DATE-SCOPED: a new StudentMission row is created
        for each new day, so missions actually reset daily (previously a
        completed mission could never be completed again). Yesterday's rows
        remain as history; today's row is reused when it already exists.
        """
        today = self._today()
        missions = list(self.db.scalars(
            select(Mission).where(Mission.is_active.is_(True), Mission.mission_type == "DAILY")
        ))
        out = []
        for mission in missions:
            sm = self.db.scalar(
                select(StudentMission).where(
                    StudentMission.student_id == student.id,
                    StudentMission.mission_id == mission.id,
                    StudentMission.assigned_date == today,
                )
            )
            if sm is None:
                sm = StudentMission(
                    student_id=student.id,
                    mission_id=mission.id,
                    assigned_date=today,
                    progress=0,
                    status="NOT_STARTED",
                )
                self.db.add(sm)
                self.db.flush()
            out.append(sm)
        return out

    def update_mission_progress(
        self, student: StudentProfile, mission_type_event: str, increment: int = 1
    ) -> None:
        """Advance TODAY'S missions whose mission_type matches the event.

        Activity only ever counts toward the current day's mission rows
        (assigned_date == today), so yesterday's completed missions can't be
        double-rewarded and today's missions start from zero.
        """
        today = self._today()
        missions = list(self.db.scalars(
            select(Mission).where(Mission.is_active.is_(True), Mission.mission_type == mission_type_event)
        ))
        for mission in missions:
            sm = self.db.scalar(
                select(StudentMission).where(
                    StudentMission.student_id == student.id,
                    StudentMission.mission_id == mission.id,
                    StudentMission.assigned_date == today,
                )
            )
            if sm is None:
                sm = StudentMission(
                    student_id=student.id,
                    mission_id=mission.id,
                    assigned_date=today,
                    progress=0,
                    status="NOT_STARTED",
                )
                self.db.add(sm)
                self.db.flush()
            if sm.status == "COMPLETED":
                continue
            sm.progress = min(sm.progress + increment, mission.target_value)
            if sm.status == "NOT_STARTED":
                sm.status = "IN_PROGRESS"
                sm.started_at = datetime.now(timezone.utc)
            if sm.progress >= mission.target_value:
                sm.status = "COMPLETED"
                sm.completed_at = datetime.now(timezone.utc)
                self.award_xp(
                    student, mission.xp_reward, "MISSION_COMPLETE",
                    reference_id=sm.id, description=f"Mission complete: {mission.title}",
                )
                self.record_activity(student.id, "MISSION_COMPLETED", reference_id=mission.id)

    def list_student_missions(self, student: StudentProfile) -> list[dict]:
        self.ensure_daily_missions(student)
        self.db.commit()
        rows = self.db.execute(
            select(StudentMission, Mission)
            .join(Mission, StudentMission.mission_id == Mission.id)
            .where(
                StudentMission.student_id == student.id,
                StudentMission.assigned_date == self._today(),
            )
            .order_by(Mission.id)
        ).all()
        return [
            {
                "id": sm.id,
                "mission_id": m.id,
                "title": m.title,
                "description": m.description,
                "mission_type": m.mission_type,
                "target_value": m.target_value,
                "progress": sm.progress,
                "status": sm.status,
                "xp_reward": m.xp_reward,
            }
            for sm, m in rows
        ]

    # ============================================================ BADGES

    def evaluate_badges(self, student: StudentProfile) -> list[Badge]:
        """Check all badge rules; award newly-earned ones (once)."""
        earned: list[Badge] = []
        for badge in self.db.scalars(select(Badge).where(Badge.is_active.is_(True))):
            already = self.db.scalar(
                select(StudentBadge.id).where(
                    StudentBadge.student_id == student.id,
                    StudentBadge.badge_id == badge.id,
                )
            )
            if already is not None:
                continue
            if self._badge_earned(student, badge):
                self.db.add(StudentBadge(student_id=student.id, badge_id=badge.id))
                if badge.xp_reward > 0:
                    self.award_xp(
                        student, badge.xp_reward, "BADGE_AWARDED",
                        reference_id=badge.id, description=f"Badge: {badge.name}",
                    )
                earned.append(badge)
        if earned:
            self.record_activity(
                student.id, "BADGES_AWARDED",
                metadata={"badges": [b.name for b in earned]},
            )
        return earned

    def _badge_earned(self, student: StudentProfile, badge: Badge) -> bool:
        criteria = badge.criteria_type
        value = badge.criteria_value
        if criteria == "FIRST_ASSESSMENT":
            return self.db.scalar(
                select(func.count(Attempt.id)).where(
                    Attempt.student_id == student.id, Attempt.status == "SUBMITTED")
            ) >= max(1, value)
        if criteria == "QUESTIONS_ANSWERED":
            from app.models.assessment import Answer

            practice_answered = self.db.scalar(
                select(func.count(PracticeAnswer.id))
                .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
                .where(PracticeSession.student_id == student.id,
                       PracticeSession.status == "COMPLETED")
            ) or 0

            assessment_answered = self.db.scalar(
                select(func.count(Answer.id))
                .join(Attempt, Answer.attempt_id == Attempt.id)
                .where(Attempt.student_id == student.id)
            ) or 0
            return (practice_answered + assessment_answered) >= value
        if criteria == "STREAK_DAYS":
            return student.current_streak >= value or student.longest_streak >= value
        if criteria == "PERFECT_SCORE":
            best = self.db.scalar(
                select(func.max(Attempt.score)).where(
                    Attempt.student_id == student.id, Attempt.status == "SUBMITTED")
            )
            return best is not None and float(best) >= value
        if criteria == "CODING_SOLVED":
            from app.models.coding import CodeSubmission

            solved = self.db.scalar(
                select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                    CodeSubmission.student_id == student.id,
                    CodeSubmission.status == "ACCEPTED",
                )
            ) or 0
            return solved >= value
        if criteria == "PRACTICE_SESSIONS":
            sessions = self.db.scalar(
                select(func.count(PracticeSession.id)).where(
                    PracticeSession.student_id == student.id,
                    PracticeSession.status == "COMPLETED",
                )
            ) or 0
            return sessions >= value
        return False

    def list_student_badges(self, student: StudentProfile) -> dict:
        rows = self.db.execute(
            select(StudentBadge, Badge)
            .join(Badge, StudentBadge.badge_id == Badge.id)
            .where(StudentBadge.student_id == student.id)
            .order_by(StudentBadge.earned_at.desc())
        ).all()
        return {
            "earned": [
                {
                    "id": sb.id,
                    "badge_id": b.id,
                    "name": b.name,
                    "description": b.description,
                    "icon": b.icon,
                    "earned_at": sb.earned_at,
                }
                for sb, b in rows
            ],
            "total_available": self.db.scalar(
                select(func.count(Badge.id)).where(Badge.is_active.is_(True))
            ) or 0,
        }

    # ============================================================ ACTIVITY FEED

    def recent_activity(self, student: StudentProfile, limit: int = 10) -> list[ActivityEvent]:
        stmt = (
            select(ActivityEvent)
            .where(ActivityEvent.student_id == student.id)
            .order_by(ActivityEvent.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
