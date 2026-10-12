"""Coding practice schemas (docs/API_Specification.md §19)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- Student views ----------

class TestCasePublic(BaseModel):
    """Visible (sample) test case only — hidden cases never serialize."""

    model_config = ConfigDict(from_attributes=True)

    input_data: str | None
    expected_output: str | None


class CodingProblemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    difficulty: str
    topic_id: int | None


class CodingProblemDetail(BaseModel):
    id: int
    title: str
    description: str | None
    difficulty: str
    topic_id: int | None
    input_format: str | None
    output_format: str | None
    constraints: str | None
    sample_test_cases: list[TestCasePublic]
    solved: bool = False


class SubmissionRequest(BaseModel):
    language: str = Field(pattern=r"^[a-z]+$", max_length=30)
    source_code: str = Field(min_length=1, max_length=50_000)


class CaseResultOut(BaseModel):
    index: int
    verdict: str
    time_ms: int
    hidden: bool
    stdin: str | None = None
    expected: str | None = None
    actual: str | None = None
    stderr: str | None = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    language: str
    status: str
    passed_test_cases: int
    total_test_cases: int
    execution_time_ms: int | None
    error_message: str | None
    created_at: datetime


class SubmissionResultOut(BaseModel):
    id: int
    problem_id: int
    language: str
    status: str
    passed_test_cases: int
    total_test_cases: int
    execution_time_ms: int | None
    error_message: str | None
    results: list[CaseResultOut]


class SubmissionHistoryItem(BaseModel):
    id: int
    problem_id: int
    language: str
    status: str
    passed_test_cases: int
    total_test_cases: int
    created_at: datetime
