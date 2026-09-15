"""Assessment and attempt schemas (docs/API_Specification.md §14)."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Assessment (admin CRUD) ----------

class AssessmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    assessment_type: str = Field(default="MOCK_TEST", max_length=30)
    duration_minutes: int = Field(default=30, ge=5, le=180)
    company_id: int | None = None
    question_ids: list[int] = Field(min_length=1, max_length=100)


class AssessmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    assessment_type: str | None = Field(default=None, max_length=30)
    duration_minutes: int | None = Field(default=None, ge=5, le=180)
    company_id: int | None = None
    is_active: bool | None = None
    question_ids: list[int] | None = None


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    assessment_type: str
    duration_minutes: int
    question_count: int
    company_id: int | None
    is_active: bool
    created_at: datetime


class AssessmentReadDetail(AssessmentRead):
    question_ids: list[int]


# ---------- Attempt ----------

class AttemptStartResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    started_at: datetime
    duration_minutes: int
    question_count: int
    questions: list[dict]


class AttemptAnswerRequest(BaseModel):
    question_id: int
    selected_option_id: int | None = None
    time_taken_seconds: int | None = Field(default=None, ge=0)


class AttemptAnswerResponse(BaseModel):
    question_id: int
    is_correct: bool
    correct_option_id: int


class AttemptSubmitResponse(BaseModel):
    attempt_id: int
    score: float
    total_questions: int
    correct: int
    incorrect: int
    unattempted: int
    accuracy: float
    time_taken_seconds: int
    topic_performance: list[dict]


class AttemptResultResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    status: str
    score: float
    total_questions: int
    correct_count: int
    incorrect_count: int
    unattempted_count: int
    accuracy: float
    started_at: datetime
    submitted_at: datetime | None
    time_taken_seconds: int | None
    topic_performance: list[dict]


class AttemptHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    assessment_title: str
    score: float | None
    correct_count: int
    incorrect_count: int
    unattempted_count: int
    accuracy: float | None
    status: str
    started_at: datetime
    submitted_at: datetime | None


# ---------- Question for attempt ----------

class QuestionForAttempt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    question_type: str
    difficulty: str
    options: list[dict]


# ---------- Admin list ----------

class AssessmentListResponse(BaseModel):
    assessments: list[AssessmentRead]
    total: int
    page: int
    limit: int
