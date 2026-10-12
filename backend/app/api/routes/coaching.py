"""Coaching endpoints: smart dashboard, daily plan, skill gap, trends, revision.

All data is computed server-side from real activity (Feature Groups 1, 2, 3,
7, 10, 11). Students can only access their own coaching data.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.services.coaching import CoachingService
from app.services.content import ContentService
from app.utils.responses import success_response

router = APIRouter(prefix="/coaching", tags=["coaching"])


def _get_service(db: Session = Depends(get_db)) -> CoachingService:
    return CoachingService(db)


@router.get("/dashboard")
def coaching_dashboard(
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
):
    """'What should I do today?' — plan, weakest topics, readiness, continue-learning."""
    data = service.dashboard(user.student_profile, user)
    return success_response(data=data, message="Coaching dashboard retrieved")


@router.get("/daily-plan")
def daily_plan(
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
):
    data = service.daily_plan(user.student_profile)
    return success_response(data=data, message="Daily plan retrieved")


@router.get("/skill-gap")
def skill_gap(
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
):
    data = service.skill_gap(user.student_profile)
    return success_response(data=data, message="Skill gap analysis retrieved")


@router.get("/trends")
def progress_trends(
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
    days: int = Query(default=7, ge=0, le=30, description="7, 30, or 0 = all time"),
):
    data = service.progress_trends(user.student_profile, days=days)
    return success_response(data=data, message="Progress trends retrieved")


@router.get("/revision")
def revision_feed(
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
):
    data = service.revision_feed(user.student_profile)
    return success_response(data=data, message="Revision feed retrieved")


@router.post("/revision/practice", status_code=201)
def revision_practice(
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
    count: int = Query(default=5, ge=5, le=15),
):
    """Quick Revision: start a practice session from wrong-answer topics."""
    result = service.revision_practice(user.student_profile, count)
    if result.get("session") is None:
        return success_response(data=result, message=result.get("message", "No revision targets"), status_code=200)
    return success_response(data=result, message="Revision session started", status_code=201)


@router.get("/companies/{company_id}/profile")
def company_profile(
    company_id: int,
    user: Annotated[object, Depends(require_student)],
    service: CoachingService = Depends(_get_service),
):
    data = service.company_profile(user.student_profile, company_id)
    if data is None:
        return success_response(data=None, message="Company not found", status_code=404)
    return success_response(data=data, message="Company preparation profile retrieved")
