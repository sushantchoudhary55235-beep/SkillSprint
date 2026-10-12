"""Coding practice endpoints (docs/API_Specification.md §19).

Student routes require authentication; problem management is admin-only
(Phase 13 adds admin CRUD on the same underlying service).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.schemas.coding import SubmissionRequest
from app.services.coding import CodingService
from app.utils.responses import success_response

router = APIRouter(prefix="/coding", tags=["coding"])


def _get_service(db: Session = Depends(get_db)) -> CodingService:
    return CodingService(db)


@router.get("/problems")
def list_problems(
    user: Annotated[object, Depends(require_student)],
    service: CodingService = Depends(_get_service),
    difficulty: str | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
):
    data = service.list_problems(
        difficulty=difficulty, topic_id=topic_id, student=user.student_profile,
        page=page, limit=limit,
    )
    return success_response(data=data, message="Coding problems retrieved")


@router.get("/problems/{problem_id}")
def get_problem(
    problem_id: int,
    user: Annotated[object, Depends(require_student)],
    service: CodingService = Depends(_get_service),
):
    data = service.get_problem(problem_id, student=user.student_profile)
    return success_response(data=data, message="Coding problem retrieved")


@router.post("/problems/{problem_id}/submit")
def submit_solution(
    problem_id: int,
    req: SubmissionRequest,
    user: Annotated[object, Depends(require_student)],
    service: CodingService = Depends(_get_service),
):
    """Judge a submission server-side; the client never decides the verdict."""
    data = service.submit(problem_id, user.student_profile, req.language, req.source_code)
    return success_response(data=data, message="Submission judged")


@router.get("/submissions/me")
def my_submissions(
    user: Annotated[object, Depends(require_student)],
    service: CodingService = Depends(_get_service),
    problem_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    data = service.submission_history(
        user.student_profile, problem_id=problem_id, page=page, limit=limit
    )
    return success_response(data=data, message="Submissions retrieved")


@router.get("/performance/me")
def my_coding_performance(
    user: Annotated[object, Depends(require_student)],
    service: CodingService = Depends(_get_service),
):
    data = service.performance(user.student_profile)
    return success_response(data=data, message="Coding performance retrieved")
