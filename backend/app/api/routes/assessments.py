"""Assessment endpoints (docs/API_Specification.md §14).

Phase 6 scope: assessment CRUD, attempt start, answer submission, scoring, results, history.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_student
from app.db.session import get_db
from app.schemas.assessment import (
    AttemptAnswerRequest,
    AssessmentCreate,
    AssessmentUpdate,
)
from app.services.assessment import AssessmentService
from app.utils.responses import success_response

router = APIRouter(tags=["assessments"])


def _get_assessment_service(db: Session = Depends(get_db)) -> AssessmentService:
    return AssessmentService(db)


# ============================================================ ADMIN CRUD

@router.get("/admin/assessments")
def admin_list_assessments(
    user: Annotated[object, Depends(require_admin)],
    service: AssessmentService = Depends(_get_assessment_service),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    data = service.list_all(page=page, limit=limit)
    return success_response(data=data, message="Assessments retrieved")


@router.get("/admin/assessments/{assessment_id}")
def admin_get_assessment(
    assessment_id: int,
    user: Annotated[object, Depends(require_admin)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    data = service.get_detail(assessment_id)
    return success_response(data=data, message="Assessment retrieved")


@router.post("/admin/assessments", status_code=201)
def admin_create_assessment(
    data: AssessmentCreate,
    user: Annotated[object, Depends(require_admin)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    result = service.create(data, user)
    return success_response(data=result, message="Assessment created", status_code=201)


@router.patch("/admin/assessments/{assessment_id}")
def admin_update_assessment(
    assessment_id: int,
    data: AssessmentUpdate,
    user: Annotated[object, Depends(require_admin)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    assessment = service.update(assessment_id, data)
    return success_response(
        data={"id": assessment.id, "title": assessment.title, "is_active": assessment.is_active},
        message="Assessment updated",
    )


# ============================================================ STUDENT - LIST

@router.get("/assessments")
def list_assessments(
    service: AssessmentService = Depends(_get_assessment_service),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Public: students see active assessments."""
    data = service.list_active(page=page, limit=limit)
    return success_response(data=data, message="Assessments retrieved")


@router.get("/assessments/{assessment_id}")
def get_assessment_detail(
    assessment_id: int,
    service: AssessmentService = Depends(_get_assessment_service),
):
    """Public: students see assessment details (without answers)."""
    data = service.get_detail(assessment_id)
    return success_response(data=data, message="Assessment retrieved")


# ============================================================ STUDENT - ATTEMPT

@router.post("/assessments/{assessment_id}/start", status_code=201)
def start_assessment(
    assessment_id: int,
    user: Annotated[object, Depends(require_student)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    data = service.start_attempt(assessment_id, user.student_profile)
    return success_response(data=data, message="Assessment started", status_code=201)


@router.post("/attempts/{attempt_id}/answer")
def submit_answer(
    attempt_id: int,
    data: AttemptAnswerRequest,
    user: Annotated[object, Depends(require_student)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    result = service.submit_answer(attempt_id, data, user.student_profile)
    return success_response(data=result, message="Answer submitted")


@router.post("/attempts/{attempt_id}/submit")
def submit_assessment(
    attempt_id: int,
    user: Annotated[object, Depends(require_student)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    data = service.submit_attempt(attempt_id, user.student_profile)
    return success_response(data=data, message="Assessment submitted")


@router.get("/attempts/{attempt_id}/result")
def get_result(
    attempt_id: int,
    user: Annotated[object, Depends(require_student)],
    service: AssessmentService = Depends(_get_assessment_service),
):
    data = service.get_result(attempt_id, user.student_profile)
    return success_response(data=data, message="Result retrieved")


@router.get("/students/me/attempts")
def my_attempts(
    user: Annotated[object, Depends(require_student)],
    service: AssessmentService = Depends(_get_assessment_service),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    data = service.get_history(user.student_profile, page=page, limit=limit)
    return success_response(data=data, message="Attempt history retrieved")
