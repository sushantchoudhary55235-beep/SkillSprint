"""Personalization Engine (docs/Phases.md §12).

Answers "what should this student learn next?" using deterministic rules on
top of the Phase 7 performance engine — never AI, never client input.

Rules (configurable thresholds):
    accuracy < 60            → weak     → practice easy/medium, HIGH priority
    60 <= accuracy < 80      → moderate → practice medium, MEDIUM priority
    accuracy >= 80           → strong   → topic test / harder practice, LOW priority

Priority score = weakness (primary) + recency (recent bad performance) +
importance (topic usage across assessments) + practice starvation.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Topic
from app.models.profile import StudentProfile
from app.models.roadmap import Recommendation
from app.repositories.recommendation import RecommendationRepository
from app.schemas.performance import classify_accuracy  # noqa: F401  (re-exported for tests)

# Deterministic recommendation rules (docs/Phases.md §12).
WEAK_ACCURACY = 60.0
STRONG_ACCURACY = 80.0
MIN_ATTEMPTS_FOR_RECOMMENDATION = 3

# XP values for recommendation types (Phase 10 will use these ids too).
TYPE_PRACTICE = "PRACTICE_TOPIC"
TYPE_ASSESSMENT = "TAKE_TOPIC_TEST"
TYPE_COMPANY_TEST = "TAKE_COMPANY_TEST"


class PersonalizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RecommendationRepository(db)

    # ============================================================ PUBLIC API

    def generate_recommendations(self, student: StudentProfile) -> list:
        """Regenerate the student's active recommendations from live performance.

        Deterministic: same performance data → same recommendations.
        Existing ACTIVE recommendations are expired, then up to 5 new ones are
        created (never duplicated for the same topic+type while active).
        """
        from app.services.performance import PerformanceService

        perf = PerformanceService(self.db)
        topics = perf.get_topics(student)
        overall = perf.get_overall(student)

        self.repo.deactivate_all(student.id)

        candidates: list[dict] = []
        for t in topics:
            if t.total_attempts < MIN_ATTEMPTS_FOR_RECOMMENDATION:
                continue
            score = self._priority_score(t, overall)
            if score <= 0:
                continue
            candidates.append({"topic": t, "score": score})

        # Highest priority first; tie-break on topic_id for determinism.
        candidates.sort(key=lambda c: (-c["score"], c["topic"].topic_id))

        created = []
        seen_pairs: set[tuple[int, str]] = set()
        for cand in candidates[:5]:
            t = cand["topic"]
            rec_type, difficulty, reason = self._build_rule(t)
            pair = (t.topic_id, rec_type)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            rec = self.repo.add(
                Recommendation(
                    student_id=student.id,
                    topic_id=t.topic_id,
                    recommendation_type=rec_type,
                    reason=reason,
                    priority=self._priority_label(cand["score"]),
                    recommended_difficulty=difficulty,
                    status="ACTIVE",
                )
            )
            created.append(rec)

        self.repo.commit()
        for rec in created:
            self.repo.refresh(rec)
        return created

    def get_active_recommendations(self, student: StudentProfile) -> list:
        recs = self.repo.list_for_student(student.id, status="ACTIVE")
        if not recs:
            recs = self.generate_recommendations(student)
        return self._attach_topic_names(recs)

    def complete_recommendation(self, student: StudentProfile, rec_id: int):
        rec = self.repo.get(rec_id)
        if rec is None or rec.student_id != student.id:
            return None
        if rec.status == "ACTIVE":
            rec.status = "COMPLETED"
            self.repo.commit()
            self.repo.refresh(rec)
        return rec

    # ============================================================ RULES

    def _build_rule(self, t) -> tuple[str, str, str]:
        """Deterministic (type, difficulty, reason) for a topic's classification."""
        acc = t.accuracy if t.accuracy is not None else 0.0
        name = t.topic_name
        if acc < WEAK_ACCURACY:
            difficulty = "easy" if acc < 45 else "medium"
            return (
                TYPE_PRACTICE,
                difficulty,
                f"Your accuracy in {name} is {acc:.0f}%, below the 60% target. "
                f"Practice {difficulty} questions to build fundamentals.",
            )
        if acc < STRONG_ACCURACY:
            return (
                TYPE_PRACTICE,
                "medium",
                f"Your accuracy in {name} is {acc:.0f}%. Keep practicing medium "
                f"questions to reach the 80% mastery threshold.",
            )
        return (
            TYPE_ASSESSMENT,
            None,
            f"You have mastered {name} ({acc:.0f}% accuracy). Take a topic test "
            f"to validate and unlock harder practice.",
        )

    def _priority_score(self, t, overall) -> float:
        """Higher = more urgent. Weakness dominates; recency and usage nudge."""
        acc = t.accuracy if t.accuracy is not None else 100.0
        score = max(0.0, 100.0 - acc)  # weakness: 0..100
        if acc >= STRONG_ACCURACY:
            # Strong topics still get a (LOW-priority) validation recommendation.
            score = max(score, 5.0)

        # Recency: a declining trend on a weak topic is more urgent.
        if t.trend == "DECLINING":
            score += 10
        elif t.trend == "IMPROVING":
            score -= 5

        # Practice starvation: many attempts without improvement.
        if t.total_attempts >= 20:
            score += 5

        # Overall context: struggling overall raises every priority slightly.
        if overall.overall_accuracy is not None and overall.overall_accuracy < WEAK_ACCURACY:
            score += 5
        return score

    @staticmethod
    def _priority_label(score: float) -> str:
        if score >= 45:
            return "HIGH"
        if score >= 20:
            return "MEDIUM"
        return "LOW"

    # ============================================================ HELPERS

    def _attach_topic_names(self, recs: list) -> list:
        from app.models.content import Topic

        topic_ids = {r.topic_id for r in recs}
        names: dict[int, str] = {}
        if topic_ids:
            rows = self.db.execute(
                select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids))
            ).all()
            names = {tid: name for tid, name in rows}
        for r in recs:
            r.topic_name = names.get(r.topic_id)
        return recs
