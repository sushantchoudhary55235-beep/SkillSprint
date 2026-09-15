"""Teacher endpoints (docs/API_Specification.md §21).

Phase 4 scope: teacher question submission (questions start in PENDING status
for admin approval).
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_teacher
from app.db.session import get_db
from app.schemas.question import QuestionCreate, QuestionReadAdmin
from app.services.question import QuestionService
from app.utils.responses import success_response

router = APIRouter(prefix="/teachers", tags=["teachers"])


def _get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(db)


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
