"""questions and question_options tables (docs/Database_design_docs.md §11–12)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BIGINT_PK, Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MCQ")
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    explanation: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ADMIN")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    options = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan",
        order_by="QuestionOption.option_order",
    )


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_order: Mapped[int] = mapped_column(nullable=False, default=1)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    question = relationship("Question", back_populates="options")
