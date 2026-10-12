"""missions and student_missions (docs/Database_design_docs.md §22–23).

StudentMission rows are DATE-SCOPED for DAILY missions: one row per
(student, mission, assigned_date) so missions genuinely reset each day.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    mission_type: Mapped[str] = mapped_column(String(50), nullable=False, default="DAILY")
    target_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    badge_id: Mapped[int | None] = mapped_column(ForeignKey("badges.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class StudentMission(Base):
    __tablename__ = "student_missions"
    __table_args__ = (
        UniqueConstraint("student_id", "mission_id", "assigned_date", name="uq_student_mission_day"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), nullable=False, index=True)
    # The day this assignment belongs to (UTC). DAILY missions reset by date.
    assigned_date: Mapped[date | None] = mapped_column(Date, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
