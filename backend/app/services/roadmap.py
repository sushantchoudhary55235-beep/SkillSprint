"""Personalized Roadmap (docs/Phases.md §13).

Converts recommendations (Phase 8) into a visible, persisted learning roadmap.
The roadmap is regenerated from live performance whenever the student's data
changes — it is derived data, never hand-authored by clients.
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Topic
from app.models.performance import PerformanceSnapshot
from app.models.roadmap import Roadmap, RoadmapItem
from app.models.profile import StudentProfile
from app.schemas.roadmap import RoadmapItemOut, RoadmapOut


class RoadmapService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ PUBLIC API

    def get_or_generate(self, student: StudentProfile) -> RoadmapOut:
        """Return the roadmap, regenerating from latest performance if stale.

        Staleness: a roadmap with zero items, or one whose updated_at predates
        the student's most recent performance snapshot.
        """
        roadmap = self._get_roadmap(student.id)
        if roadmap is None or self._is_stale(student, roadmap):
            return self.generate(student)
        return self._serialize(roadmap)

    def generate(self, student: StudentProfile) -> RoadmapOut:
        """Rebuild the roadmap from the student's topic performance.

        Ordering: HIGH priority (weak) topics first, then MEDIUM, then LOW
        (strong → take topic test). Ties break by accuracy ascending, then
        topic_id for determinism.
        """
        from app.services.performance import PerformanceService
        from app.schemas.performance import classify_accuracy

        topics = PerformanceService(self.db).get_topics(student)
        ranked = [
            t for t in topics
            if t.accuracy is not None and t.total_attempts >= 3
        ]
        priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        priority_of = self._priority_of

        items_spec: list[dict] = []
        for t in ranked:
            classification = classify_accuracy(t.accuracy)
            priority = priority_of(classification)
            if classification == "strong":
                action = "Take a topic test to validate mastery"
                target = 90.0
                difficulty = None
            elif classification == "moderate":
                action = f"Practice {t.topic_name} at medium difficulty until 80% accurate"
                target = 80.0
                difficulty = "medium"
            else:
                difficulty = "easy" if t.accuracy < 45 else "medium"
                action = f"Practice {difficulty} questions in {t.topic_name} to reach 60% accuracy"
                target = 60.0
            items_spec.append({
                "topic_id": t.topic_id,
                "topic_name": t.topic_name,
                "priority": priority,
                "reason": action,
                "target_accuracy": target,
                "recommended_difficulty": difficulty,
                "accuracy": t.accuracy,
            })

        items_spec.sort(key=lambda s: (
            priority_rank[s["priority"]], s["accuracy"], s["topic_id"],
        ))

        roadmap = self._get_roadmap(student.id)
        if roadmap is None:
            roadmap = Roadmap(student_id=student.id, title="My Placement Roadmap")
            self.db.add(roadmap)
            self.db.flush()
        else:
            # Replace items (roadmap_items is derived, recomputable data).
            for old in self.db.scalars(
                select(RoadmapItem).where(RoadmapItem.roadmap_id == roadmap.id)
            ):
                self.db.delete(old)
            self.db.flush()

        for i, spec in enumerate(items_spec, 1):
            item = RoadmapItem(
                roadmap_id=roadmap.id,
                topic_id=spec["topic_id"],
                sequence_order=i,
                status="NOT_STARTED",
                priority=spec["priority"],
                reason=spec["reason"],
                target_accuracy=Decimal(str(spec["target_accuracy"])),
            )
            self.db.add(item)

        self._update_progress(roadmap)
        roadmap.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(roadmap)
        return self._serialize(roadmap)

    def update_item_status(self, student: StudentProfile, item_id: int, status: str) -> RoadmapItem | None:
        """Student marks an item in-progress/completed (not_started reset allowed)."""
        item = self.db.get(RoadmapItem, item_id)
        if item is None:
            return None
        roadmap = self.db.get(Roadmap, item.roadmap_id)
        if roadmap is None or roadmap.student_id != student.id:
            return None
        if status not in ("NOT_STARTED", "IN_PROGRESS", "COMPLETED"):
            return None
        item.status = status
        item.completed_at = datetime.now(timezone.utc) if status == "COMPLETED" else None
        self._update_progress(roadmap)
        self.db.commit()
        self.db.refresh(item)
        return item

    # ============================================================ HELPERS

    @staticmethod
    def _priority_of(classification: str) -> str:
        return {"weak": "HIGH", "moderate": "MEDIUM", "strong": "LOW"}.get(classification, "MEDIUM")

    def _get_roadmap(self, student_id: int) -> Roadmap | None:
        return self.db.scalar(select(Roadmap).where(Roadmap.student_id == student_id))

    def _is_stale(self, student: StudentProfile, roadmap: Roadmap) -> bool:
        item_count = self.db.scalar(
            select(func.count(RoadmapItem.id)).where(RoadmapItem.roadmap_id == roadmap.id)
        ) or 0
        if item_count == 0:
            return True
        latest_snapshot = self.db.scalar(
            select(PerformanceSnapshot.created_at)
            .where(PerformanceSnapshot.student_id == student.id)
            .order_by(PerformanceSnapshot.created_at.desc())
            .limit(1)
        )
        if latest_snapshot is None:
            return False
        updated = roadmap.updated_at
        if updated is None:
            return True
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        if latest_snapshot.tzinfo is None:
            latest_snapshot = latest_snapshot.replace(tzinfo=timezone.utc)
        return latest_snapshot > updated

    def _update_progress(self, roadmap: Roadmap) -> None:
        items = list(self.db.scalars(
            select(RoadmapItem).where(RoadmapItem.roadmap_id == roadmap.id)
        ))
        if not items:
            roadmap.overall_progress = Decimal("0")
            return
        done = sum(1 for i in items if i.status == "COMPLETED")
        roadmap.overall_progress = Decimal(round(done / len(items) * 100, 2))

    def _serialize(self, roadmap: Roadmap) -> RoadmapOut:
        items = list(self.db.scalars(
            select(RoadmapItem)
            .where(RoadmapItem.roadmap_id == roadmap.id)
            .order_by(RoadmapItem.sequence_order)
        ))
        topic_ids = {i.topic_id for i in items}
        names: dict[int, str] = {}
        if topic_ids:
            rows = self.db.execute(select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids))).all()
            names = {tid: name for tid, name in rows}

        item_outs = [
            RoadmapItemOut(
                id=i.id,
                topic_id=i.topic_id,
                topic_name=names.get(i.topic_id),
                sequence_order=i.sequence_order,
                status=i.status,
                priority=i.priority,
                reason=i.reason,
                target_accuracy=float(i.target_accuracy) if i.target_accuracy is not None else None,
                completed_at=i.completed_at,
            )
            for i in items
        ]
        return RoadmapOut(
            id=roadmap.id,
            title=roadmap.title,
            overall_progress=float(roadmap.overall_progress or 0),
            items=item_outs,
            generated_at=roadmap.updated_at or roadmap.created_at,
        )
