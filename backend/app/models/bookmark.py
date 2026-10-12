"""bookmarks table (Feature Group 12 — Saved Questions).

A bookmark is a lightweight pointer to existing content (question, coding
problem, or a free-form concept note). The underlying question/problem is NOT
duplicated — only its id is referenced, per the rule "avoid duplicating the
underlying question unnecessarily".
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        # One bookmark per (student, type, target) — prevents duplicate saves.
        UniqueConstraint("student_id", "bookmark_type", "question_id", "problem_id", name="uq_bookmark_target"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # QUESTION | PROBLEM | CONCEPT
    bookmark_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("coding_problems.id", ondelete="CASCADE"), index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
