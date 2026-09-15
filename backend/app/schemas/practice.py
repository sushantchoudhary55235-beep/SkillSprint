"""Practice session schemas (docs/API_Specification.md §12)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Start ----------

class PracticeStartRequest(BaseModel):
    topic_id: int | None = None
    company_id: int | None = None
    difficulty: str | None = Field(default=None, pattern=r"^(easy|medium|hard)$")
    question_count: int = Field(default=10, ge=1, le=50)


class QuestionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    option_text: str
    option_order: int


class QuestionForPractice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    question_type: str
    difficulty: str
    options: list[QuestionOptionOut]


class PracticeStartData(BaseModel):
    session_id: int
    mode: str
    topic_id: int | None
    company_id: int | None
    difficulty: str | None
    question_count: int
    questions: list[QuestionForPractice]


# ---------- Answer ----------

class PracticeAnswerRequest(BaseModel):
    question_id: int
    selected_option_id: int | None = None
    time_taken_seconds: int | None = Field(default=None, ge=0)


class PracticeAnswerData(BaseModel):
    question_id: int
    is_correct: bool
    correct_option_id: int
    explanation: str | None = None


# ---------- Complete ----------

class PracticeCompleteData(BaseModel):
    session_id: int
    score: int
    correct: int
    incorrect: int
    unattempted: int
    accuracy: float
    total_time_seconds: int
    xp_earned: int


# ---------- History ----------

class PracticeSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    topic_id: int | None
    company_id: int | None
    difficulty: str | None
    question_count: int
    correct_count: int
    incorrect_count: int
    score: int | None
    xp_earned: int
    status: str
    created_at: datetime
    completed_at: datetime | None


class PracticeHistoryData(BaseModel):
    sessions: list[PracticeSessionSummary]
    total: int
    page: int
    limit: int


# ---------- Progress ----------

class TopicProgressItem(BaseModel):
    topic_id: int
    topic_name: str
    total_attempts: int
    correct_answers: int
    accuracy: float
    trend: str


class OverallProgressData(BaseModel):
    total_questions_attempted: int
    total_correct: int
    total_incorrect: int
    overall_accuracy: float
    total_sessions: int
    topic_progress: list[TopicProgressItem]
    xp: int
    level: int
    current_streak: int


# ---------- Dashboard ----------

class DashboardData(BaseModel):
    student_id: str
    name: str
    email: str
    xp: int
    level: int
    current_streak: int
    readiness_score: float
    total_questions_attempted: int
    total_correct: int
    overall_accuracy: float
    recent_sessions: list[PracticeSessionSummary]
    topic_progress: list[TopicProgressItem]
