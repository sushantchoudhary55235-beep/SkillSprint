"""Roadmap schemas (Phase 9 — Personalized Roadmap)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoadmapItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    topic_name: str | None = None
    sequence_order: int
    status: str  # NOT_STARTED | IN_PROGRESS | COMPLETED
    priority: str  # HIGH | MEDIUM | LOW
    reason: str | None
    target_accuracy: float | None
    recommended_difficulty: str | None = None
    completed_at: datetime | None


class RoadmapOut(BaseModel):
    id: int
    title: str
    overall_progress: float
    items: list[RoadmapItemOut]
    generated_at: datetime


class RoadmapItemUpdate(BaseModel):
    status: str | None = None

    class Config:
        extra = "forbid"
