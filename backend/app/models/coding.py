"""coding_problems, test_cases, code_submissions (docs/Database_design_docs.md §29–31)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="EASY")
    input_format: Mapped[str | None] = mapped_column(Text)
    output_format: Mapped[str | None] = mapped_column(Text)
    constraints: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class TestCase(Base):
    """Judge data; hidden cases must never be exposed to students."""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_data: Mapped[str | None] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)
    is_hidden: Mapped[bool] = mapped_column(default=True, nullable=False)
    time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=256)


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("coding_problems.id"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    passed_test_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_test_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    memory_used_mb: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
