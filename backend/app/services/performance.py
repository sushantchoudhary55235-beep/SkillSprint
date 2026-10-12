"""Performance Analysis Engine (docs/Phases.md §11).

Converts raw student activity into deterministic performance metrics:
overall, per-topic, per-difficulty, per-company, trends, strengths, weaknesses.

The backend computes everything; clients and AI never supply metrics.
"""
from sqlalchemy.orm import Session

from app.models.profile import StudentProfile
from app.repositories.performance import PerformanceRepository
from app.schemas.performance import (
    CompanyPerformanceItem,
    DifficultyPerformanceItem,
    OverallPerformance,
    PerformanceSummary,
    StrengthItem,
    TopicPerformanceItem,
    TrendPoint,
    WeaknessItem,
    classify_accuracy,
)


class PerformanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PerformanceRepository(db)

    # ============================================================ READ APIs

    def get_overall(self, student: StudentProfile) -> OverallPerformance:
        stats = self.repo.get_overall(student.id)
        return OverallPerformance(
            **stats,
            classification=classify_accuracy(stats["overall_accuracy"]),
        )

    def get_topics(self, student: StudentProfile) -> list[TopicPerformanceItem]:
        aggregates = self.repo.get_topic_aggregates(student.id)
        return [TopicPerformanceItem(**{**a, "classification": classify_accuracy(a["accuracy"])}) for a in aggregates]

    def get_by_difficulty(self, student: StudentProfile) -> list[DifficultyPerformanceItem]:
        aggregates = self.repo.get_difficulty_aggregates(student.id)
        return [
            DifficultyPerformanceItem(**a, classification=classify_accuracy(a["accuracy"]))
            for a in aggregates
        ]

    def get_by_company(self, student: StudentProfile) -> list[CompanyPerformanceItem]:
        aggregates = self.repo.get_company_aggregates(student.id)
        return [
            CompanyPerformanceItem(**a, classification=classify_accuracy(a["accuracy"]))
            for a in aggregates
        ]

    def get_trends(self, student: StudentProfile) -> list[TrendPoint]:
        rows = self.repo.get_attempt_trend(student.id)
        return [TrendPoint(**r) for r in rows]

    def get_strengths(self, student: StudentProfile, limit: int = 5) -> list[StrengthItem]:
        topics = self.get_topics(student)
        strong = [
            StrengthItem(
                topic_id=t.topic_id,
                topic_name=t.topic_name,
                accuracy=t.accuracy,
                total_attempts=t.total_attempts,
                classification=t.classification,
            )
            for t in topics
            if t.classification == "strong" and t.total_attempts >= 3
        ]
        strong.sort(key=lambda s: (-s.accuracy, -s.total_attempts))
        return strong[:limit]

    def get_weaknesses(self, student: StudentProfile, limit: int = 5) -> list[WeaknessItem]:
        topics = self.get_topics(student)
        # Weakest first, but require a minimum sample so one bad guess is not a "weakness".
        weak = [
            WeaknessItem(
                topic_id=t.topic_id,
                topic_name=t.topic_name,
                accuracy=t.accuracy,
                total_attempts=t.total_attempts,
                classification=t.classification,
            )
            for t in topics
            if t.classification == "weak" and t.total_attempts >= 3
        ]
        weak.sort(key=lambda s: (s.accuracy, -s.total_attempts))
        return weak[:limit]

    def get_summary(self, student: StudentProfile) -> PerformanceSummary:
        return PerformanceSummary(
            overall=self.get_overall(student),
            topics=self.get_topics(student),
            by_difficulty=self.get_by_difficulty(student),
            by_company=self.get_by_company(student),
            strengths=self.get_strengths(student),
            weaknesses=self.get_weaknesses(student),
            trends=self.get_trends(student),
        )

    # ============================================================ WRITE PATHS

    def rebuild_topic_performance(self, student: StudentProfile) -> list:
        """Recompute and persist topic_performance rows from raw answers."""
        aggregates = self.repo.get_topic_aggregates(student.id)
        return self.repo.upsert_topic_performance(student, aggregates)

    def snapshot_after_assessment(
        self,
        student: StudentProfile,
        *,
        assessment_id: int | None,
        score: float | None,
        accuracy: float | None,
    ) -> None:
        """Record a performance snapshot and refresh topic aggregates.

        Called by the assessment service after a successful submission so that
        history is captured at the moment new performance data exists.
        """
        self.repo.add_snapshot(
            student.id,
            assessment_id=assessment_id,
            overall_score=score,
            accuracy=accuracy,
            readiness_score=float(student.readiness_score) if student.readiness_score is not None else None,
        )
        self.rebuild_topic_performance(student)
