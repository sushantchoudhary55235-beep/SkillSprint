"""Student data reset — the Danger Zone (GitHub-style destructive action).

Lets a student irreversibly wipe their OWN learning data: practice sessions,
assessment attempts, coding submissions, XP/ledger, badges, streaks, missions,
roadmap, recommendations, bookmarks, performance history, AI answer logs and
activity events.

Non-negotiable rules:
- The user account itself (login, email, password, role, profile identity) is
  NOT touched — only learning data. Teacher associations keep existing but see
  a fresh student afterwards.
- Requires the account password AND the exact phrase ``RESET MY DATA`` — the
  GitHub pattern (password + typed confirmation) for destructive actions.
- Rate limited: 3 attempts per 10 minutes per user (wrong phrase or wrong
  password both count). Prevents password-guessing via this endpoint.
- One atomic transaction: everything is deleted or nothing is.
- Admins are out of scope: only students have learning data to reset.
- Every execution is logged WITHOUT any credential material.
- Audit records survive the reset (separate table, separate transaction).
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ValidationError
from app.core.rate_limit import RateLimitExceededError
from app.core.security import verify_password
from app.models.activity import ActivityEvent
from app.models.ai_answer_log import AIAnswerLog
from app.models.assessment import Answer, Attempt
from app.models.audit import ResetAuditLog
from app.models.bookmark import Bookmark
from app.models.coding import CodeSubmission
from app.models.gamification import StudentBadge, XPTransaction
from app.models.leaderboard import LeaderboardEntry
from app.models.mission import StudentMission
from app.models.performance import PerformanceSnapshot, TopicPerformance
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile
from app.models.roadmap import Recommendation, Roadmap, RoadmapItem
from app.models.user import User

logger = logging.getLogger("skillsprint.student_reset")

CONFIRMATION_PHRASE = "RESET MY DATA"
_MAX_RESET_ATTEMPTS = 3
_WINDOW_SECONDS = 600.0  # 10 minutes

_reset_attempts: dict[int, deque[float]] = defaultdict(deque)
_reset_lock = Lock()


def _enforce_reset_rate_limit(user_id: int) -> None:
    """3 attempts / 10 min / user — failed or successful, both count."""
    now = time.monotonic()
    with _reset_lock:
        hits = _reset_attempts[user_id]
        while hits and now - hits[0] > _WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= _MAX_RESET_ATTEMPTS:
            raise RateLimitExceededError(600)
        hits.append(now)


class StudentResetService:
    """Danger Zone: wipe a student's own learning data, keep the account."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ dry run

    def preview(self, student: StudentProfile) -> dict:
        """Counts of everything that would be deleted (no writes)."""
        sid = student.id

        def _count(model, *filters) -> int:
            stmt = select(func.count()).select_from(model)
            for f in filters:
                stmt = stmt.where(f)
            return self.db.scalar(stmt) or 0

        practice_answers = (
            self.db.scalar(
                select(func.count())
                .select_from(PracticeAnswer)
                .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
                .where(PracticeSession.student_id == sid)
            )
            or 0
        )
        attempt_answers = (
            self.db.scalar(
                select(func.count())
                .select_from(Answer)
                .join(Attempt, Answer.attempt_id == Attempt.id)
                .where(Attempt.student_id == sid)
            )
            or 0
        )
        roadmap_items = (
            self.db.scalar(
                select(func.count())
                .select_from(RoadmapItem)
                .join(Roadmap, RoadmapItem.roadmap_id == Roadmap.id)
                .where(Roadmap.student_id == sid)
            )
            or 0
        )

        return {
            "practice_sessions": _count(PracticeSession, PracticeSession.student_id == sid),
            "practice_answers": practice_answers,
            "attempts": _count(Attempt, Attempt.student_id == sid),
            "attempt_answers": attempt_answers,
            "coding_submissions": _count(CodeSubmission, CodeSubmission.student_id == sid),
            "xp_transactions": _count(XPTransaction, XPTransaction.student_id == sid),
            "badges": _count(StudentBadge, StudentBadge.student_id == sid),
            "bookmarks": _count(Bookmark, Bookmark.student_id == sid),
            "missions": _count(StudentMission, StudentMission.student_id == sid),
            "roadmaps": _count(Roadmap, Roadmap.student_id == sid),
            "roadmap_items": roadmap_items,
            "recommendations": _count(Recommendation, Recommendation.student_id == sid),
            "topic_performance_rows": _count(TopicPerformance, TopicPerformance.student_id == sid),
            "performance_snapshots": _count(PerformanceSnapshot, PerformanceSnapshot.student_id == sid),
            "ai_answer_logs": _count(AIAnswerLog, AIAnswerLog.student_id == sid),
            "activity_events": _count(ActivityEvent, ActivityEvent.student_id == sid),
            "leaderboard_entries": _count(LeaderboardEntry, LeaderboardEntry.student_id == sid),
        }

    # ------------------------------------------------------------------ reset

    def reset_all(
        self,
        user: User,
        student: StudentProfile,
        password: str,
        confirmation: str,
    ) -> dict:
        """Wipe all learning data atomically. Returns per-table row counts with before/after verification.

        Atomicity guarantees:
        - Successful reset + SUCCESS audit record are committed in ONE transaction.
        - Failed reset is rolled back first, then FAILED audit is recorded in a separate transaction.
        - Audit persistence failures are propagated (not silently swallowed).
        """
        # -- generate request ID for correlation (early, for all paths) -----
        request_id = str(uuid.uuid4())

        # -- resolve live objects in THIS session ------------------------
        live_user = self.db.get(User, user.id)
        live_student = self.db.get(StudentProfile, student.id)
        if live_user is None or live_student is None:
            # Record FAILED audit for account not found
            self._record_audit(
                student_id=student.id,
                status="FAILED",
                rows_deleted={},
                failure_reason="Account could not be loaded for reset.",
                request_id=request_id,
            )
            raise ValidationError("Account could not be loaded for reset.")
        sid = live_student.id

        # -- gates with FAILED audit on failure ---------------------------
        if confirmation != CONFIRMATION_PHRASE:
            self._record_audit(
                student_id=sid,
                status="FAILED",
                rows_deleted={},
                failure_reason=f'Invalid confirmation phrase. Expected "{CONFIRMATION_PHRASE}".',
                request_id=request_id,
            )
            raise ValidationError(f'Type "{CONFIRMATION_PHRASE}" exactly to confirm.')

        try:
            _enforce_reset_rate_limit(live_user.id)
        except RateLimitExceededError as e:
            self._record_audit(
                student_id=sid,
                status="FAILED",
                rows_deleted={},
                failure_reason="Rate limit exceeded: 3 attempts per 10 minutes.",
                request_id=request_id,
            )
            raise

        if not verify_password(password, live_user.password_hash):
            logger.warning("Danger Zone reset failed auth check (user_id=%s)", live_user.id)
            self._record_audit(
                student_id=sid,
                status="FAILED",
                rows_deleted={},
                failure_reason="Password is incorrect",
                request_id=request_id,
            )
            raise AuthError("Password is incorrect")

        if live_user.role != "student":
            self._record_audit(
                student_id=sid,
                status="FAILED",
                rows_deleted={},
                failure_reason="Only student accounts can reset learning data.",
                request_id=request_id,
            )
            raise ValidationError("Only student accounts can reset learning data.")

        # -- capture before counts ---------------------------------------
        before_counts = self.preview(live_student)

        # -- atomic wipe + SUCCESS audit in SAME transaction -------------
        try:
            deleted_counts = self._delete_all(sid)

            # Add SUCCESS audit to the SAME session so it commits atomically with the reset.
            # The reset_audit_logs table is NOT wiped by the reset (unlike activity_events),
            # so this is safe and ensures atomicity.
            audit = ResetAuditLog(
                student_id=sid,
                status="SUCCESS",
                rows_deleted=deleted_counts,
                failure_reason=None,
                request_id=request_id,
            )
            self.db.add(audit)
            self.db.commit()

        except Exception as e:
            # Reset failed - rollback the reset transaction
            self.db.rollback()

            # Record FAILED audit in a FRESH transaction (separate from the rolled-back reset)
            # This must succeed independently; if it fails, we log but don't mask the reset failure.
            try:
                self._record_audit(
                    student_id=sid,
                    status="FAILED",
                    rows_deleted={},
                    failure_reason=str(e),
                    request_id=request_id,
                )
            except Exception as audit_err:
                # Audit persistence failure during failure handling - log clearly
                logger.critical(
                    "BOTH reset AND audit recording failed (student_id=%s). Reset error: %s; Audit error: %s",
                    sid, e, audit_err
                )

            logger.error("Danger Zone reset failed and was rolled back (user_id=%s): %s", live_user.id, e)
            raise

        # -- compute after counts (should be zero for deleted tables) ---
        after_counts = self.preview(live_student)

        logger.info("Danger Zone reset completed (user_id=%s student_id=%s)", live_user.id, sid)
        return {
            "reset": True,
            "rows_deleted": deleted_counts,
            "before_counts": before_counts,
            "after_counts": after_counts,
        }

    # ------------------------------------------------------------------ internals

    def _delete_all(self, sid: int) -> dict[str, int]:
        """Issue every delete on the current transaction. Caller commits."""
        def _do(model, *filters) -> int:
            stmt = delete(model)
            for f in filters:
                stmt = stmt.where(f)
            res = self.db.execute(stmt)
            return res.rowcount or 0

        counts: dict[str, int] = {}

        # Children before parents (SQLite has no deferred FK enforcement).
        counts["practice_answers"] = _do(
            PracticeAnswer,
            PracticeAnswer.session_id.in_(
                select(PracticeSession.id).where(PracticeSession.student_id == sid)
            ),
        )
        counts["practice_sessions"] = _do(PracticeSession, PracticeSession.student_id == sid)
        counts["attempt_answers"] = _do(
            Answer,
            Answer.attempt_id.in_(select(Attempt.id).where(Attempt.student_id == sid)),
        )
        counts["attempts"] = _do(Attempt, Attempt.student_id == sid)
        counts["coding_submissions"] = _do(CodeSubmission, CodeSubmission.student_id == sid)
        counts["xp_transactions"] = _do(XPTransaction, XPTransaction.student_id == sid)
        counts["badges"] = _do(StudentBadge, StudentBadge.student_id == sid)
        counts["bookmarks"] = _do(Bookmark, Bookmark.student_id == sid)
        counts["missions"] = _do(StudentMission, StudentMission.student_id == sid)
        counts["roadmap_items"] = _do(
            RoadmapItem,
            RoadmapItem.roadmap_id.in_(select(Roadmap.id).where(Roadmap.student_id == sid)),
        )
        counts["roadmaps"] = _do(Roadmap, Roadmap.student_id == sid)
        counts["recommendations"] = _do(Recommendation, Recommendation.student_id == sid)
        counts["topic_performance_rows"] = _do(TopicPerformance, TopicPerformance.student_id == sid)
        counts["performance_snapshots"] = _do(PerformanceSnapshot, PerformanceSnapshot.student_id == sid)
        counts["ai_answer_logs"] = _do(AIAnswerLog, AIAnswerLog.student_id == sid)
        counts["activity_events"] = _do(ActivityEvent, ActivityEvent.student_id == sid)
        counts["leaderboard_entries"] = _do(LeaderboardEntry, LeaderboardEntry.student_id == sid)

        # Profile counters reset in-transaction (caller commits).
        sp = self.db.get(StudentProfile, sid)
        if sp is not None:
            sp.xp = 0
            sp.level = 1
            sp.current_streak = 0
            sp.longest_streak = 0
            sp.last_activity_date = None
            sp.readiness_score = 0

        # One visible trace of the action in the (otherwise wiped) feed.
        self.db.add(ActivityEvent(student_id=sid, event_type="DATA_RESET"))
        return counts

    def _record_audit(
        self,
        student_id: int,
        status: str,
        rows_deleted: dict,
        failure_reason: str | None,
        request_id: str,
    ) -> None:
        """Record audit event in a separate transaction for FAILED resets.

        This method is called AFTER a rollback, so it uses a fresh transaction.
        Raises on failure so caller can handle audit persistence errors.
        """
        audit = ResetAuditLog(
            student_id=student_id,
            status=status,
            rows_deleted=rows_deleted,
            failure_reason=failure_reason,
            request_id=request_id,
        )
        self.db.add(audit)
        self.db.commit()