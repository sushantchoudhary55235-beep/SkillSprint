"""Recommendation schemas (Phase 8 — Personalization Engine)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    topic_name: str | None = None
    recommendation_type: str
    reason: str | None
    priority: str
    recommended_difficulty: str | None
    status: str
    created_at: datetime


class RecommendationListData(BaseModel):
    recommendations: list[RecommendationOut]
    total: int


class RecommendationCompleteOut(BaseModel):
    id: int
    status: str
    completed: bool
