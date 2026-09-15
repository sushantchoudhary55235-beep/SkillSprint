"""Student self-service endpoints (docs/API_Specification.md §9).

Phase 3 scope: profile endpoint proves student-role RBAC.
Phase 5 scope: dashboard, practice start/answer/complete, history, progress, daily quiz.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.schemas.practice import (
    DashboardData,
    OverallProgressData,
    PracticeAnswerData,
    PracticeAnswerRequest,
    PracticeCompleteData,
    PracticeHistoryData,
    PracticeStartData,
    PracticeStartRequest,
)
from app.services.practice import PracticeService
from app.utils.responses import success_response

router = APIRouter(prefix="/students", tags=["students"])


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def _get_practice_service(db: Session = Depends(get_db)) -> PracticeService:
    return PracticeService(db)


class StudentProfileOut(BaseModel):
    student_id: str
    name: str
    email: str
    xp: int
    level: int
    current_streak: int
    readiness_score: float


# ============================================================ PROFILE

@router.get("/profile")
def get_student_profile(
    user: Annotated[object, Depends(require_student)],
    db: Annotated[Session, Depends(get_db_session)],
):
    profile = user.student_profile
    return success_response(
        data=StudentProfileOut(
            student_id=profile.student_id,
            name=user.name,
            email=user.email,
            xp=profile.xp,
            level=profile.level,
            current_streak=profile.current_streak,
            readiness_score=float(profile.readiness_score),
        ),
        message="Student profile retrieved",
    )


# ============================================================ DASHBOARD

@router.get("/dashboard")
def get_dashboard(
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
):
    data = service.get_dashboard(user.student_profile, user)
    return success_response(data=data, message="Dashboard retrieved")


# ============================================================ PRACTICE

@router.post("/practice/start", status_code=201)
def start_practice(
    req: PracticeStartRequest,
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
):
    data = service.start_session(req, user.student_profile)
    return success_response(data=data, message="Practice session started", status_code=201)


@router.post("/practice/{session_id}/answer")
def submit_answer(
    session_id: int,
    req: PracticeAnswerRequest,
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
):
    data = service.submit_answer(session_id, req, user.student_profile)
    return success_response(data=data, message="Answer submitted")


@router.post("/practice/{session_id}/complete")
def complete_practice(
    session_id: int,
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
):
    data = service.complete_session(session_id, user.student_profile)
    return success_response(data=data, message="Practice session completed")


# ============================================================ HISTORY

@router.get("/practice/history")
def practice_history(
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    data = service.get_history(user.student_profile, page=page, limit=limit)
    return success_response(data=data, message="Practice history retrieved")


# ============================================================ PROGRESS

@router.get("/progress")
def get_progress(
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
):
    data = service.get_progress(user.student_profile)
    return success_response(data=data, message="Progress retrieved")


# ============================================================ DAILY QUIZ

@router.post("/quiz/daily/start", status_code=201)
def start_daily_quiz(
    user: Annotated[object, Depends(require_student)],
    service: PracticeService = Depends(_get_practice_service),
):
    data = service.start_daily_quiz(user.student_profile)
    return success_response(data=data, message="Daily quiz started", status_code=201)
