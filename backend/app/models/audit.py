"""Reset audit log (Phase 2 — Danger Zone security).

Permanent record of student data reset operations. Survives the reset itself
(unlike activity_events which are wiped during reset).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base, JSON_TYPE


class ResetAuditLog(Base):
    __tablename__ = "reset_audit_logs"
    __table_args__ = (
        # Index for querying by student
        # Index for time-range queries
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    # SUCCESS or FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # Per-table deletion counts (JSONB on PostgreSQL, JSON on SQLite)
    rows_deleted: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    # Populated only on FAILED
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional correlation ID for request tracing
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)