"""Danger Zone account endpoints (GitHub-style destructive action).

- GET  /api/account/reset/preview — counts of everything a reset would delete.
- POST /api/account/reset         — irreversibly wipe the student's learning
  data. Requires the account password AND the exact confirmation phrase.

Student-only. The account (login/email/role) is never touched.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.services.student_reset import CONFIRMATION_PHRASE, StudentResetService
from app.utils.responses import success_response

router = APIRouter(prefix="/account", tags=["account"])


def _get_service(db: Session = Depends(get_db)) -> StudentResetService:
    return StudentResetService(db)


class ResetRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirmation: str = Field(min_length=1, max_length=64)


@router.get("/reset/preview")
def reset_preview(
    user: Annotated[object, Depends(require_student)],
    service: StudentResetService = Depends(_get_service),
):
    """What a reset would delete — powers the Danger Zone summary."""
    data = service.preview(user.student_profile)
    return success_response(data=data, message="Reset preview retrieved")


@router.post("/reset")
def reset_account(
    req: ResetRequest,
    user: Annotated[object, Depends(require_student)],
    service: StudentResetService = Depends(_get_service),
):
    """Danger Zone: irreversibly wipe all learning data for THIS account."""
    result = service.reset_all(
        user=user,
        student=user.student_profile,
        password=req.password,
        confirmation=req.confirmation,
    )
    return success_response(data=result, message="All learning data has been reset")
