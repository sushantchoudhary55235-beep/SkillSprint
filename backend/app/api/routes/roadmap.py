"""Roadmap endpoints (docs/API_Specification.md §18)."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.services.roadmap import RoadmapService
from app.utils.responses import success_response

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


def _get_service(db: Session = Depends(get_db)) -> RoadmapService:
    return RoadmapService(db)


@router.get("/me")
def my_roadmap(
    user: Annotated[object, Depends(require_student)],
    service: RoadmapService = Depends(_get_service),
):
    data = service.get_or_generate(user.student_profile)
    return success_response(data=data, message="Roadmap retrieved")


@router.post("/generate")
def regenerate(
    user: Annotated[object, Depends(require_student)],
    service: RoadmapService = Depends(_get_service),
):
    data = service.generate(user.student_profile)
    return success_response(data=data, message="Roadmap regenerated")


@router.get("/items")
def roadmap_items(
    user: Annotated[object, Depends(require_student)],
    service: RoadmapService = Depends(_get_service),
):
    data = service.get_or_generate(user.student_profile)
    return success_response(data=data.items, message="Roadmap items retrieved")


@router.patch("/items/{item_id}")
def update_item(
    item_id: int,
    status: str,
    user: Annotated[object, Depends(require_student)],
    service: RoadmapService = Depends(_get_service),
):
    if status not in ("NOT_STARTED", "IN_PROGRESS", "COMPLETED"):
        raise ValidationError("status must be NOT_STARTED, IN_PROGRESS, or COMPLETED")
    item = service.update_item_status(user.student_profile, item_id, status)
    if item is None:
        raise NotFoundError(f"Roadmap item {item_id} not found")
    return success_response(
        data={"id": item.id, "status": item.status, "completed_at": item.completed_at},
        message="Roadmap item updated",
    )
