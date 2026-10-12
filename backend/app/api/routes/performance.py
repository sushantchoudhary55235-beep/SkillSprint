"""Performance endpoints (docs/API_Specification.md §16).

All metrics are computed server-side from attempts/answers/submissions.
Students can only access their own performance.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.services.performance import PerformanceService
from app.utils.responses import success_response

router = APIRouter(prefix="/performance", tags=["performance"])


def _get_service(db: Session = Depends(get_db)) -> PerformanceService:
    return PerformanceService(db)


@router.get("/me")
def my_performance(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_overall(user.student_profile)
    return success_response(data=data, message="Overall performance retrieved")


@router.get("/me/summary")
def my_summary(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_summary(user.student_profile)
    return success_response(data=data, message="Performance summary retrieved")


@router.get("/topics")
def topic_performance(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_topics(user.student_profile)
    return success_response(data=data, message="Topic performance retrieved")


@router.get("/difficulties")
def difficulty_performance(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_by_difficulty(user.student_profile)
    return success_response(data=data, message="Difficulty performance retrieved")


@router.get("/companies")
def company_performance(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_by_company(user.student_profile)
    return success_response(data=data, message="Company performance retrieved")


@router.get("/trends")
def performance_trends(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
    limit: int = Query(default=20, ge=1, le=50),
):
    data = service.get_trends(user.student_profile)
    return success_response(data=data[-limit:], message="Performance trends retrieved")


@router.get("/strengths")
def strengths(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_strengths(user.student_profile)
    return success_response(data=data, message="Strengths retrieved")


@router.get("/weaknesses")
def weaknesses(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.get_weaknesses(user.student_profile)
    return success_response(data=data, message="Weaknesses retrieved")


@router.get("/snapshots")
def snapshots(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    data = service.repo.list_snapshots(user.student_profile.id)
    return success_response(data=data, message="Performance snapshots retrieved")


@router.get("/readiness")
def readiness_breakdown(
    user: Annotated[object, Depends(require_student)],
    service: PerformanceService = Depends(_get_service),
):
    """Transparent readiness score: five documented components + weights."""
    from app.services.readiness import compute_readiness

    data = compute_readiness(service.db, user.student_profile)
    return success_response(data=data, message="Readiness breakdown retrieved")
