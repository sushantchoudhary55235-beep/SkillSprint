"""Recommendation endpoints (docs/API_Specification.md §17)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.schemas.recommendation import RecommendationOut
from app.services.recommendation import PersonalizationService
from app.utils.responses import success_response

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _get_service(db: Session = Depends(get_db)) -> PersonalizationService:
    return PersonalizationService(db)


@router.get("/me")
def my_recommendations(
    user: Annotated[object, Depends(require_student)],
    service: PersonalizationService = Depends(_get_service),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Active personalized recommendations; generated on first access."""
    recs = service.get_active_recommendations(user.student_profile)[:limit]
    data = [
        RecommendationOut(
            id=r.id,
            topic_id=r.topic_id,
            topic_name=r.topic_name,
            recommendation_type=r.recommendation_type,
            reason=r.reason,
            priority=r.priority,
            recommended_difficulty=r.recommended_difficulty,
            status=r.status,
            created_at=r.created_at,
        )
        for r in recs
    ]
    return success_response(data={"recommendations": data, "total": len(data)},
                            message="Recommendations retrieved")


@router.post("/generate")
def regenerate(
    user: Annotated[object, Depends(require_student)],
    service: PersonalizationService = Depends(_get_service),
):
    """Force regeneration from latest performance (used after assessments)."""
    recs = service.generate_recommendations(user.student_profile)
    return success_response(data={"total": len(recs)}, message="Recommendations regenerated")


@router.post("/{recommendation_id}/complete")
def complete(
    recommendation_id: int,
    user: Annotated[object, Depends(require_student)],
    service: PersonalizationService = Depends(_get_service),
):
    rec = service.complete_recommendation(user.student_profile, recommendation_id)
    if rec is None:
        return success_response(data={"id": recommendation_id, "status": "NOT_FOUND", "completed": False},
                                message="Recommendation not found", status_code=404)
    return success_response(
        data={"id": rec.id, "status": rec.status, "completed": rec.status == "COMPLETED"},
        message="Recommendation completed" if rec.status == "COMPLETED" else "Recommendation already processed",
    )
