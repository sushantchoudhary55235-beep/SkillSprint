"""Question and QuestionOption schemas (docs/API_Specification.md §11)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Question Option ----------

class QuestionOptionCreate(BaseModel):
    option_text: str = Field(min_length=1, max_length=500)
    option_order: int = Field(ge=1, le=10)
    is_correct: bool = False


class QuestionOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    option_text: str
    option_order: int


class QuestionOptionReadAdmin(BaseModel):
    """Admin view includes is_correct."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    option_text: str
    option_order: int
    is_correct: bool


# ---------- Question ----------

class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1, max_length=5000)
    question_type: str = Field(default="MCQ", max_length=30)
    topic_id: int
    company_id: int | None = None
    difficulty: str = Field(pattern=r"^(easy|medium|hard)$", description="easy, medium, or hard")
    explanation: str | None = None
    options: list[QuestionOptionCreate] = Field(min_length=2, max_length=10)


class QuestionRead(BaseModel):
    """Public question view — no is_correct leak."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    question_type: str
    topic_id: int
    company_id: int | None
    difficulty: str
    explanation: str | None
    status: str
    created_at: datetime
    options: list[QuestionOptionRead]


class QuestionReadAdmin(BaseModel):
    """Admin view includes is_correct on options and source metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    question_type: str
    topic_id: int
    company_id: int | None
    difficulty: str
    explanation: str | None
    source_type: str
    created_by: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    options: list[QuestionOptionReadAdmin]


class QuestionUpdate(BaseModel):
    """Partial update for admin editing."""

    question_text: str | None = Field(default=None, min_length=1, max_length=5000)
    question_type: str | None = Field(default=None, max_length=30)
    topic_id: int | None = None
    company_id: int | None = None
    difficulty: str | None = Field(default=None, pattern=r"^(easy|medium|hard)$")
    explanation: str | None = None


class QuestionStatusUpdate(BaseModel):
    """Admin approve / reject / archive a question."""

    status: str = Field(pattern=r"^(approved|rejected|archived)$")


class QuestionListParams(BaseModel):
    """Query-string parameters for listing questions."""

    topic_id: int | None = None
    company_id: int | None = None
    difficulty: str | None = None
    category: str | None = None
    question_type: str | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
