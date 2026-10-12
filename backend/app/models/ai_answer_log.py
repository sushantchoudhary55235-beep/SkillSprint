"""AI answer log (Phase 15C).

Records ONLY the outcome of answering an AI-generated question (topic,
correctness, timestamp, XP awarded) — the question text itself is never
persisted (deliberate project decision). The reference_id of the XP ledger
transaction links to this row.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class AIAnswerLog(Base):
    __tablename__ = "ai_answer_logs"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topics.id"), nullable=True, index=True
    )
    topic_name: Mapped[str | None] = mapped_column(String(100))
    difficulty: Mapped[str | None] = mapped_column(String(20))
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer)
    xp_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
