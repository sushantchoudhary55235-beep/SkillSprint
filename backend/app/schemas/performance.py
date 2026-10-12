"""Performance analysis schemas (docs/API_Specification.md §16).

All numeric metrics are computed by the backend from attempts, answers,
practice sessions, and coding submissions — never accepted from clients.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Classification thresholds (docs/Phases.md §11: deterministic rules).
STRONG_THRESHOLD = 80.0  # accuracy >= 80 → strong
WEAK_THRESHOLD = 60.0    # accuracy < 60 → weak; 60–79 → moderate


def classify_accuracy(accuracy: float | None) -> str:
    """Deterministic accuracy classification: strong/moderate/weak/new."""
    if accuracy is None:
        return "new"
    if accuracy >= STRONG_THRESHOLD:
        return "strong"
    if accuracy >= WEAK_THRESHOLD:
        return "moderate"
    return "weak"


class TopicPerformanceItem(BaseModel):
    topic_id: int
    topic_name: str
    category: str | None = None
    total_attempts: int = 0
    correct: int = 0
    incorrect: int = 0
    accuracy: float | None = None
    recent_accuracy: float | None = None
    historical_accuracy: float | None = None
    trend: str = "NEW"  # IMPROVING | STABLE | DECLINING | NEW
    classification: str = "new"


class DifficultyPerformanceItem(BaseModel):
    difficulty: str  # easy | medium | hard
    total_attempts: int = 0
    correct: int = 0
    accuracy: float | None = None
    classification: str = "new"


class CompanyPerformanceItem(BaseModel):
    company_id: int
    company_name: str
    total_attempts: int = 0
    correct: int = 0
    accuracy: float | None = None
    classification: str = "new"


class OverallPerformance(BaseModel):
    total_questions_attempted: int = 0
    correct: int = 0
    incorrect: int = 0
    unanswered: int = 0
    overall_accuracy: float | None = None
    practice_sessions: int = 0
    practice_accuracy: float | None = None
    assessment_attempts: int = 0
    assessment_avg_score: float | None = None
    coding_attempted: int = 0
    coding_solved: int = 0
    classification: str = "new"


class TrendPoint(BaseModel):
    label: str
    score: float | None = None
    accuracy: float | None = None
    date: datetime | None = None


class StrengthItem(BaseModel):
    topic_id: int
    topic_name: str
    accuracy: float
    total_attempts: int
    classification: str


class WeaknessItem(StrengthItem):
    pass


class PerformanceSummary(BaseModel):
    overall: OverallPerformance
    topics: list[TopicPerformanceItem]
    by_difficulty: list[DifficultyPerformanceItem]
    by_company: list[CompanyPerformanceItem]
    strengths: list[StrengthItem]
    weaknesses: list[WeaknessItem]
    trends: list[TrendPoint] = Field(default_factory=list)


class TopicPerformanceDB(BaseModel):
    """Row of topic_performance table as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    total_attempts: int
    correct_answers: int
    incorrect_answers: int
    accuracy: float | None
    trend: str
    last_attempted_at: datetime | None


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int | None
    overall_score: float | None
    accuracy: float | None
    readiness_score: float | None
    created_at: datetime
