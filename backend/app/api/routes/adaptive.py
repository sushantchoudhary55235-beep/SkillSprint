"""Adaptive difficulty endpoint (Feature Group 4).

Read-only recommendation computed from the student's rolling answer window.
Practice start still honours explicit user choice (see the service).
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.services.adaptive import AdaptiveDifficultyService
from app.utils.responses import success_response

router = APIRouter(prefix="/adaptive", tags=["adaptive"])


def _get_service(db: Session = Depends(get_db)) -> AdaptiveDifficultyService:
    return AdaptiveDifficultyService(db)


@router.get("/difficulty")
def recommended_difficulty(
    user: Annotated[object, Depends(require_student)],
    service: AdaptiveDifficultyService = Depends(_get_service),
):
    """Adaptive difficulty recommendation with a documented, transparent reason."""
    data = service.recommend(user.student_profile)
    return success_response(data=data, message="Adaptive difficulty retrieved")
