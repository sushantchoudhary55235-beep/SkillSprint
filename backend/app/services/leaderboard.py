"""Leaderboards (docs/Phases.md §14.6).

Ranks students by XP earned within a period, computed from the validated
``xp_transactions`` ledger. Ties share the same rank (competition ranking:
1,2,2,4). Persisted into ``leaderboards``/``leaderboard_entries`` so rankings
are stable between refreshes.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.gamification import XPTransaction
from app.models.leaderboard import Leaderboard, LeaderboardEntry
from app.models.profile import StudentProfile
from app.models.user import User

PERIODS = ("WEEKLY", "MONTHLY", "ALL_TIME")


def _period_start(period: str, today: date) -> date | None:
    if period == "WEEKLY":
        # ISO week starts Monday
        return today - timedelta(days=today.weekday())
    if period == "MONTHLY":
        return today.replace(day=1)
    return None  # ALL_TIME


class LeaderboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def refresh(self, period: str) -> Leaderboard:
        """Recompute and persist the leaderboard for a period."""
        if period not in PERIODS:
            raise ValueError(f"Unknown period {period}")
        today = datetime.now(timezone.utc).date()
        start = _period_start(period, today)

        stmt = select(
            XPTransaction.student_id,
            func.sum(XPTransaction.xp_amount).label("xp"),
        ).group_by(XPTransaction.student_id)
        if start is not None:
            stmt = stmt.where(XPTransaction.created_at >= datetime.combine(start, datetime.min.time()))
        rows = self.db.execute(stmt).all()

        # Sort by xp desc, then student_id asc for deterministic tie order.
        rows.sort(key=lambda r: (-int(r.xp or 0), r.student_id))

        board = self.db.scalar(select(Leaderboard).where(Leaderboard.period_type == period))
        if board is None:
            board = Leaderboard(
                name=f"{period.title()} XP Leaderboard",
                scope="GLOBAL",
                period_type=period,
                start_date=start,
                end_date=today,
            )
            self.db.add(board)
            self.db.flush()
        else:
            board.start_date = start
            board.end_date = today

        for old in self.db.scalars(
            select(LeaderboardEntry).where(LeaderboardEntry.leaderboard_id == board.id)
        ):
            self.db.delete(old)
        self.db.flush()

        # Competition ranking: ties share rank; next distinct score skips ahead.
        rank = 0
        prev_xp: int | None = None
        for position, (student_id, xp) in enumerate(rows, 1):
            xp_val = int(xp or 0)
            if xp_val != prev_xp:
                rank = position
                prev_xp = xp_val
            self.db.add(LeaderboardEntry(
                leaderboard_id=board.id, student_id=student_id, score=xp_val, rank=rank,
            ))
        self.db.commit()
        self.db.refresh(board)
        return board

    def get(self, period: str = "WEEKLY", limit: int = 50) -> dict:
        """Return the persisted leaderboard, refreshing it first."""
        board = self.refresh(period)
        entries = list(self.db.scalars(
            select(LeaderboardEntry)
            .where(LeaderboardEntry.leaderboard_id == board.id)
            .order_by(LeaderboardEntry.rank, LeaderboardEntry.student_id)
            .limit(limit)
        ))
        student_ids = [e.student_id for e in entries]
        names: dict[int, tuple[str, str]] = {}
        if student_ids:
            rows = self.db.execute(
                select(StudentProfile.id, User.name, StudentProfile.student_id)
                .join(User, StudentProfile.user_id == User.id)
                .where(StudentProfile.id.in_(student_ids))
            ).all()
            names = {pid: (name, sid) for pid, name, sid in rows}
        return {
            "period_type": period,
            "start_date": board.start_date,
            "end_date": board.end_date,
            "entries": [
                {
                    "rank": e.rank,
                    "student_profile_id": e.student_id,
                    "name": names.get(e.student_id, ("Unknown", ""))[0],
                    "student_id": names.get(e.student_id, ("", ""))[1],
                    "xp": e.score,
                }
                for e in entries
            ],
        }

    def my_rank(self, student: StudentProfile, period: str = "WEEKLY") -> dict:
        """Direct ledger aggregation — no full-board materialization."""
        if period not in PERIODS:
            raise ValueError(f"Unknown period {period}")
        today = datetime.now(timezone.utc).date()
        start = _period_start(period, today)
        stmt = select(func.sum(XPTransaction.xp_amount)).where(
            XPTransaction.student_id == student.id
        )
        if start is not None:
            stmt = stmt.where(
                XPTransaction.created_at >= datetime.combine(start, datetime.min.time())
            )
        xp = int(self.db.scalar(stmt) or 0)

        better = select(func.count(func.distinct(XPTransaction.student_id))).where(
            XPTransaction.xp_amount.isnot(None)
        )
        better_subq = (
            select(XPTransaction.student_id, func.sum(XPTransaction.xp_amount).label("xp"))
            .group_by(XPTransaction.student_id)
        )
        if start is not None:
            better_subq = better_subq.where(
                XPTransaction.created_at >= datetime.combine(start, datetime.min.time())
            )
        better_subq = better_subq.subquery()
        rank = self.db.scalar(
            select(func.count()).select_from(better_subq).where(better_subq.c.xp > xp)
        )
        return {
            "rank": (rank + 1) if (xp > 0 or rank) else None,
            "xp": xp,
            "student_profile_id": student.id,
        }
