"""Teacher endpoints (docs/API_Specification.md §21).

Phase 4 scope: teacher question submission (questions start in PENDING status
for admin approval).
Phase 12 scope: student association by Student ID and the teacher dashboard
(metrics come from the Phase 7 performance engine; access is isolated to
students explicitly associated via ``teacher_students``).
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_teacher
from app.db.session import get_db
from app.schemas.question import QuestionCreate, QuestionReadAdmin
from app.services.question import QuestionService
from app.services.teacher import TeacherService
from app.utils.responses import success_response

router = APIRouter(prefix="/teachers", tags=["teachers"])


def _get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(db)


def _get_teacher_service(db: Session = Depends(get_db)) -> TeacherService:
    return TeacherService(db)


class AddStudentRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=30, description="Public Student ID (SS…) of the student to associate")


@router.post("/questions", status_code=201)
def submit_question(
    data: QuestionCreate,
    user: Annotated[object, Depends(require_teacher)],
    service: QuestionService = Depends(_get_question_service),
):
    """Teacher submits a question for admin review.

    The question is created with status=PENDING and must be approved
    by an admin before it becomes visible to students.
    """
    question = service.submit(data, user)
    return success_response(
        data=QuestionReadAdmin.model_validate(question),
        message="Question submitted for review",
        status_code=201,
    )


# ============================================================ STUDENT ASSOCIATION (Phase 12)

def _teacher_profile(user):
    """Resolve the TeacherProfile for the current user, or 404."""
    from app.core.exceptions import NotFoundError

    profile = user.teacher_profile
    if profile is None:
        raise NotFoundError("Teacher profile not found")
    return profile


@router.post("/students", status_code=201)
def add_student(
    req: AddStudentRequest,
    user: Annotated[object, Depends(require_teacher)],
    service: TeacherService = Depends(_get_teacher_service),
):
    """Associate a student by their public Student ID."""
    link = service.add_student(_teacher_profile(user), req.student_id)
    return success_response(
        data={
            "id": link.id,
            "student_profile_id": link.student_id,
            "status": link.status,
        },
        message="Student associated",
        status_code=201,
    )


@router.get("/students")
def list_students(
    user: Annotated[object, Depends(require_teacher)],
    service: TeacherService = Depends(_get_teacher_service),
):
    """All associated students with headline performance metrics."""
    data = service.list_students(_teacher_profile(user))
    return success_response(data=data, message="Students retrieved")


@router.get("/dashboard")
def teacher_dashboard(
    user: Annotated[object, Depends(require_teacher)],
    service: TeacherService = Depends(_get_teacher_service),
):
    """Class overview: totals, averages, per-student metrics, class-wide weak topics."""
    data = service.dashboard(_teacher_profile(user))
    return success_response(data=data, message="Teacher dashboard retrieved")


@router.get("/students/{student_profile_id}")
def student_detail(
    student_profile_id: int,
    user: Annotated[object, Depends(require_teacher)],
    service: TeacherService = Depends(_get_teacher_service),
):
    """Full performance view for one ASSOCIATED student (403 otherwise)."""
    data = service.get_associated_student(_teacher_profile(user), student_profile_id)
    return success_response(data=data, message="Student detail retrieved")


@router.delete("/students/{student_profile_id}", status_code=200)
def remove_student(
    student_profile_id: int,
    user: Annotated[object, Depends(require_teacher)],
    service: TeacherService = Depends(_get_teacher_service),
):
    """Remove (soft-delete) a student association."""
    service.remove_student(_teacher_profile(user), student_profile_id)
    return success_response(
        data={"student_profile_id": student_profile_id, "status": "REMOVED"},
        message="Student association removed",
    )
