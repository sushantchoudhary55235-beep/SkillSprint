"""Schemas for AI question generation & evaluation (Phase 15C)."""
from pydantic import BaseModel, Field

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


class AIQuestionGenerateRequest(BaseModel):
    """Student selects Company + Topic + Difficulty (Phase 15C step 1)."""

    company: str | None = Field(default=None, max_length=100)
    topic_id: int | None = None
    topic_name: str | None = Field(default=None, max_length=100)
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")


class AIQuestionEvaluateRequest(BaseModel):
    """Answer submission for an AI-generated question (never persisted).

    The answer key lives in a server-side ticket issued at generate time; the
    client sends ``ticket`` plus its chosen answer. ``correct_answer`` is
    accepted for backwards compatibility but is IGNORED for grading — a
    client can no longer self-grade (Phase 15C security hardening).
    """

    ticket: str = Field(min_length=10, max_length=128)
    student_answer: str = Field(min_length=1, max_length=300)
    correct_answer: str | None = Field(default=None, max_length=300)  # IGNORED (compat)
    time_taken_seconds: int | None = Field(default=None, ge=0, le=3600)
