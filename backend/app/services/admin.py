"""Admin service (docs/Phases.md §17 — Phase 13).

Centralized platform control: user management, platform analytics and
gamification configuration visibility. All metrics are computed server-side
from real rows — the admin dashboard never trusts client-reported numbers.

Observability (Phase 23): privileged account operations are logged. User
emails are identifiers, not secrets, so they appear in the log line; no
credential or token material is ever logged.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, Attempt
from app.models.content import Company, Topic
from app.models.coding import CodingProblem, CodeSubmission
from app.models.gamification import Badge, StudentBadge, XPTransaction
from app.models.performance import TopicPerformance
from app.models.profile import StudentProfile, TeacherProfile
from app.models.question import Question
from app.models.user import User
from app.core.exceptions import ValidationError

logger = logging.getLogger("skillsprint.admin")


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ USER MANAGEMENT

    def list_users(
        self,
        *,
        role: str | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        stmt = select(User)
        count_stmt = select(func.count(User.id))
        if role is not None:
            stmt = stmt.where(User.role == role.lower())
            count_stmt = count_stmt.where(User.role == role.lower())
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
            count_stmt = count_stmt.where(User.is_active.is_(is_active))
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where((User.name.ilike(pattern)) | (User.email.ilike(pattern)))
            count_stmt = count_stmt.where((User.name.ilike(pattern)) | (User.email.ilike(pattern)))

        total = self.db.scalar(count_stmt) or 0
        rows = self.db.scalars(
            stmt.order_by(User.id).offset((page - 1) * limit).limit(limit)
        ).all()
        return {
            "users": [self._user_row(u) for u in rows],
            "total": total,
            "page": page,
            "limit": limit,
        }

    @staticmethod
    def _user_row(u: User) -> dict:
        return {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }

    def set_user_active(self, user_id: int, is_active: bool) -> User:
        """Activate/deactivate a user; deactivation revokes API access (401 on next request)."""
        user = self.db.get(User, user_id)
        if user is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"User {user_id} not found")
        if user.role == "admin" and not is_active:
            # Prevent locking out all admins.
            active_admins = self.db.scalar(
                select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))
            ) or 0
            if active_admins <= 1:
                raise ValidationError("Cannot deactivate the last active admin")
        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        logger.info("Admin account state changed: user_id=%s role=%s is_active=%s", user.id, user.role, is_active)
        return user

    # ============================================================ PLATFORM ANALYTICS

    def analytics(self) -> dict:
        total_students = self.db.scalar(select(func.count(StudentProfile.id))) or 0
        total_teachers = self.db.scalar(select(func.count(TeacherProfile.id))) or 0
        total_questions = self.db.scalar(select(func.count(Question.id))) or 0
        pending_questions = self.db.scalar(
            select(func.count(Question.id)).where(Question.status == "PENDING")
        ) or 0
        total_assessments = self.db.scalar(select(func.count(Assessment.id))) or 0
        total_attempts = self.db.scalar(select(func.count(Attempt.id))) or 0
        total_submissions = self.db.scalar(select(func.count(CodeSubmission.id))) or 0

        # Active students: distinct students with any attempt in the last 7 days.
        from datetime import datetime, timedelta, timezone

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_students = self.db.scalar(
            select(func.count(func.distinct(Attempt.student_id)))
            .where(Attempt.started_at >= week_ago)
        ) or 0

        avg_accuracy = self.db.scalar(
            select(func.avg(Attempt.accuracy)).where(Attempt.status == "SUBMITTED")
        )

        # Popular topics: most-practiced by answer volume.
        popular_topics = self.db.execute(
            select(TopicPerformance.topic_id, Topic.name, func.count(TopicPerformance.id))
            .join(Topic, TopicPerformance.topic_id == Topic.id)
            .group_by(TopicPerformance.topic_id, Topic.name)
            .order_by(func.count(TopicPerformance.id).desc())
            .limit(5)
        ).all()

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_questions": total_questions,
            "pending_questions": pending_questions,
            "total_assessments": total_assessments,
            "total_attempts": total_attempts,
            "total_code_submissions": total_submissions,
            "active_students_7d": active_students,
            "average_accuracy": round(float(avg_accuracy), 2) if avg_accuracy is not None else None,
            "popular_topics": [
                {"topic_id": tid, "topic_name": name, "students_tracked": count}
                for tid, name, count in popular_topics
            ],
        }

    # ============================================================ GAMIFICATION CONFIG

    def gamification_config(self) -> dict:
        """Expose the deterministic reward rules (read-only; backend-authoritative)."""
        from app.services.gamification import (
            LEVEL_THRESHOLDS,
            STREAK_MILESTONE_DAYS,
            XP_ASSESSMENT_COMPLETE,
            XP_BADGE_DEFAULT,
            XP_COMPLETE_SESSION_BONUS,
            XP_CORRECT_ANSWER,
            XP_DAILY_QUIZ_BONUS,
            XP_STREAK_MILESTONE,
        )

        badges = self.db.scalars(select(Badge).order_by(Badge.id)).all()
        return {
            "xp_rules": {
                "complete_session": XP_COMPLETE_SESSION_BONUS,
                "correct_answer": XP_CORRECT_ANSWER,
                "daily_quiz": XP_DAILY_QUIZ_BONUS,
                "assessment_complete": XP_ASSESSMENT_COMPLETE,
                "badge_default": XP_BADGE_DEFAULT,
                "streak_milestone": XP_STREAK_MILESTONE,
            },
            "level_thresholds": LEVEL_THRESHOLDS,
            "streak_milestone_days": STREAK_MILESTONE_DAYS,
            "badges": [
                {
                    "id": b.id,
                    "name": b.name,
                    "description": b.description,
                    "icon": b.icon,
                    "criteria_type": b.criteria_type,
                    "criteria_value": b.criteria_value,
                    "xp_reward": b.xp_reward,
                    "is_active": b.is_active,
                }
                for b in badges
            ],
        }

    # ============================================================ STUDENT ANALYTICS (Phase 15D)

    def students_overview(self) -> list[dict]:
        """Every student with headline metrics for the admin analytics view."""
        from app.services.performance import PerformanceService

        rows = self.db.execute(
            select(StudentProfile, User)
            .join(User, StudentProfile.user_id == User.id)
            .order_by(StudentProfile.id)
        ).all()
        perf = PerformanceService(self.db)
        out = []
        for profile, user in rows:
            overall = perf.get_overall(profile)
            out.append({
                "student_profile_id": profile.id,
                "student_id": profile.student_id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active,
                "accuracy": overall.overall_accuracy,
                "questions_attempted": overall.total_questions_attempted,
                "assessment_avg_score": overall.assessment_avg_score,
                "problems_solved": overall.coding_solved,
                "streak_days": profile.current_streak,
                "xp": profile.xp,
                "level": profile.level,
                "readiness_score": float(profile.readiness_score or 0),
            })
        return out

    def question_analytics(self) -> dict:
        """Most-attempted topics, per-topic accuracy and difficulty distribution."""
        topic_rows = self.db.execute(
            select(
                TopicPerformance.topic_id,
                Topic.name,
                func.sum(TopicPerformance.total_attempts),
                func.sum(TopicPerformance.correct_answers),
            )
            .join(Topic, TopicPerformance.topic_id == Topic.id)
            .group_by(TopicPerformance.topic_id, Topic.name)
            .order_by(func.sum(TopicPerformance.total_attempts).desc())
            .limit(20)
        ).all()
        topics = []
        for tid, name, attempts, correct in topic_rows:
            attempts = int(attempts or 0)
            correct = int(correct or 0)
            topics.append({
                "topic_id": tid,
                "topic_name": name,
                "total_attempts": attempts,
                "accuracy": round(correct / attempts * 100, 2) if attempts else None,
            })

        difficulty_rows = self.db.execute(
            select(Question.difficulty, func.count(Question.id))
            .group_by(Question.difficulty)
        ).all()
        difficulty_distribution = {
            (diff or "unknown"): int(count) for diff, count in difficulty_rows
        }
        return {
            "topics": topics,
            "difficulty_distribution": difficulty_distribution,
        }

    def coding_analytics(self) -> dict:
        """Per-problem pass rates, most-attempted problems, language distribution."""
        problem_rows = self.db.execute(
            select(
                CodeSubmission.problem_id,
                CodingProblem.title,
                CodingProblem.difficulty,
                func.count(CodeSubmission.id),
                func.sum(func.coalesce(CodeSubmission.passed_test_cases, 0)),
                func.sum(func.coalesce(CodeSubmission.total_test_cases, 0)),
            )
            .join(CodingProblem, CodeSubmission.problem_id == CodingProblem.id)
            .group_by(CodeSubmission.problem_id, CodingProblem.title, CodingProblem.difficulty)
            .order_by(func.count(CodeSubmission.id).desc())
            .limit(50)
        ).all()
        problems = []
        for pid, title, difficulty, subs, passed, total in problem_rows:
            subs = int(subs)
            passed = int(passed or 0)
            total = int(total or 0)
            problems.append({
                "problem_id": pid,
                "title": title,
                "difficulty": difficulty,
                "submissions": subs,
                "pass_rate": round(passed / total * 100, 2) if total else None,
            })

        lang_rows = self.db.execute(
            select(CodeSubmission.language, func.count(CodeSubmission.id))
            .group_by(CodeSubmission.language)
        ).all()
        language_distribution = {lang: int(count) for lang, count in lang_rows}
        return {
            "problems": problems,
            "language_distribution": language_distribution,
        }

    def popular_topics_week(self, limit: int = 10) -> list[dict]:
        """Top attempted topics (by answers) in the trailing 7 days."""
        from datetime import datetime, timedelta, timezone

        from app.models.assessment import Answer
        from app.models.practice import PracticeAnswer

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        counts: dict[int, int] = {}

        practice_rows = self.db.execute(
            select(Question.topic_id, func.count(PracticeAnswer.id))
            .join(PracticeAnswer, PracticeAnswer.question_id == Question.id)
            .where(PracticeAnswer.created_at >= week_ago, Question.topic_id.isnot(None))
            .group_by(Question.topic_id)
        ).all()
        for tid, count in practice_rows:
            counts[tid] = counts.get(tid, 0) + int(count)

        assessment_rows = self.db.execute(
            select(Question.topic_id, func.count(Answer.id))
            .join(Answer, Answer.question_id == Question.id)
            .where(Answer.created_at >= week_ago, Question.topic_id.isnot(None))
            .group_by(Question.topic_id)
        ).all()
        for tid, count in assessment_rows:
            counts[tid] = counts.get(tid, 0) + int(count)

        ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
        names: dict[int, str] = {}
        if ranked:
            rows = self.db.execute(
                select(Topic.id, Topic.name).where(Topic.id.in_([tid for tid, _ in ranked]))
            ).all()
            names = {tid: name for tid, name in rows}
        return [
            {"topic_id": tid, "topic_name": names.get(tid, "Unknown"), "attempts": count}
            for tid, count in ranked
        ]

    def toggle_badge(self, badge_id: int, is_active: bool) -> Badge:
        """Enable/disable a badge rule (active badges are auto-awarded)."""
        badge = self.db.get(Badge, badge_id)
        if badge is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Badge {badge_id} not found")
        badge.is_active = is_active
        self.db.commit()
        self.db.refresh(badge)
        return badge

    def toggle_topic(self, topic_id: int, is_active: bool) -> Topic:
        """Convenience wrapper used by the admin UI status toggle."""
        topic = self.db.get(Topic, topic_id)
        if topic is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Topic {topic_id} not found")
        topic.is_active = is_active
        self.db.commit()
        self.db.refresh(topic)
        return topic
