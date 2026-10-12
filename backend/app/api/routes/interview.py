"""Interview preparation endpoints (Feature Group 6).

Static question bank + two clearly-labelled feedback layers (deterministic
scoring vs optional AI prose). Students only.

Audit fix (M4): the AI-backed evaluate path consumes the same per-user rate
limiter as every other Gemini endpoint so AI cost is bounded.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.core.rate_limit import ai_limiter
from app.db.session import get_db
from app.services.interview import InterviewService
from app.utils.responses import success_response

router = APIRouter(prefix="/interview", tags=["interview"])


def _get_service(db: Session = Depends(get_db)) -> InterviewService:
    return InterviewService(db)


def _enforce_ai_rate_limit(user: Annotated[object, Depends(require_student)]) -> object:
    """Shared AI budget so /interview/evaluate costs like other AI endpoints."""
    ai_limiter.check(user.id)
    return user


class InterviewAnswerRequest(BaseModel):
    category: str = Field(max_length=30)
    question_id: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=8000)


@router.get("/config")
def interview_config(
    user: Annotated[object, Depends(require_student)],
    service: InterviewService = Depends(_get_service),
):
    data = service.get_config()
    return success_response(data=data, message="Interview configuration retrieved")


@router.get("/questions")
def interview_questions(
    user: Annotated[object, Depends(require_student)],
    service: InterviewService = Depends(_get_service),
    category: str = Query(max_length=30),
    difficulty: str = Query(default="easy"),
    experience_level: str = Query(default="fresher", max_length=20),
    count: int = Query(default=5, ge=1, le=10),
):
    data = service.get_questions(
        category=category.upper(), difficulty=difficulty.lower(),
        experience=experience_level.lower(), count=count,
    )
    if data is None:
        return success_response(data=None, message="Invalid category or difficulty", status_code=422)
    return success_response(data=data, message="Interview questions retrieved")


@router.post("/evaluate")
def interview_evaluate(
    req: InterviewAnswerRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    service: InterviewService = Depends(_get_service),
):
    data = service.evaluate(category=req.category.upper(), question_id=req.question_id, answer=req.answer)
    if data is None:
        return success_response(data=None, message="Invalid category, question, or empty answer", status_code=422)
    return success_response(data=data, message="Interview feedback generated")
