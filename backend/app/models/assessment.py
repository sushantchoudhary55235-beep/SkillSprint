"""assessments, assessment_questions, attempts, answers (docs/Database_design_docs.md §13–16)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BIGINT_PK, Base


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK_TEST")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    assessment_questions = relationship(
        "AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan"
    )


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=1)

    assessment = relationship("Assessment", back_populates="assessment_questions")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    score: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    total_marks: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unattempted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS", index=True)

    answers = relationship(
        "Answer", back_populates="attempt", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    selected_option_id: Mapped[int | None] = mapped_column(ForeignKey("question_options.id"))
    answer_text: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column()
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    attempt = relationship("Attempt", back_populates="answers")
