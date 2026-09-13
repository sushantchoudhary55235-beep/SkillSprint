"""leaderboards and leaderboard_entries (docs/Database_design_docs.md §27–28)."""
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    scope: Mapped[str] = mapped_column(String(30), nullable=False)  # GLOBAL/CLASS/TEACHER
    period_type: Mapped[str] = mapped_column(String(30), nullable=False)  # DAILY/WEEKLY/MONTHLY/ALL_TIME
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("leaderboard_id", "student_id", name="uq_leaderboard_entries_pair"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    leaderboard_id: Mapped[int] = mapped_column(
        ForeignKey("leaderboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
