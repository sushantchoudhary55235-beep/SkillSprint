"""Recommendation repository: persistence for generated recommendations."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.roadmap import Recommendation


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, recommendation_id: int) -> Recommendation | None:
        return self.db.get(Recommendation, recommendation_id)

    def list_for_student(
        self, student_id: int, status: str | None = None, limit: int = 20
    ) -> list[Recommendation]:
        stmt = (
            select(Recommendation)
            .where(Recommendation.student_id == student_id)
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(Recommendation.status == status)
        else:
            stmt = stmt.where(Recommendation.status == "ACTIVE")
        return list(self.db.scalars(stmt).all())

    def deactivate_all(self, student_id: int) -> None:
        """Expire existing active recommendations before regenerating."""
        for rec in self.db.scalars(
            select(Recommendation).where(
                Recommendation.student_id == student_id,
                Recommendation.status == "ACTIVE",
            )
        ):
            rec.status = "EXPIRED"
            self.db.add(rec)

    def add(self, rec: Recommendation) -> Recommendation:
        self.db.add(rec)
        self.db.flush()
        return rec

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)
