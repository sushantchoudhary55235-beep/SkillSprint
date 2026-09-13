"""topic_performance and performance_snapshots (docs/Database_design_docs.md §17–18)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class TopicPerformance(Base):
    """Aggregated per-topic performance; derived data, recomputable from answers."""

    __tablename__ = "topic_performance"
    __table_args__ = (UniqueConstraint("student_id", "topic_id", name="uq_topic_performance_pair"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False, index=True)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incorrect_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    average_time_seconds: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    trend: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("assessments.id"))
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    readiness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
