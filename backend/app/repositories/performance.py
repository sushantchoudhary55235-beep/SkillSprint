"""Repository for performance aggregation queries.

Raw sources of truth (per docs/Database_design_docs.md §17–18):
- ``answers``          — assessment answers, joined to questions for topic/difficulty
- ``practice_answers`` — practice answers, joined via practice_sessions
- ``attempts``         — assessment outcomes (scores, accuracy)
- ``code_submissions`` — coding performance

Aggregated storage: ``topic_performance`` and ``performance_snapshots``.
"""
from datetime import datetime

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.assessment import Answer, Attempt
from app.models.coding import CodeSubmission
from app.models.content import Company, Topic
from app.models.performance import PerformanceSnapshot, TopicPerformance
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile
from app.models.question import Question


class PerformanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ RAW ANSWER ROWS

    def _assessment_answer_rows(self, student_id: int):
        """(row_id, question_id, topic_id, difficulty, company_id, is_correct, selected, created_at).

        row_id orders answers chronologically within identical timestamps.
        """
        stmt = (
            select(
                Answer.id,
                Answer.question_id,
                Question.topic_id,
                Question.difficulty,
                Question.company_id,
                Answer.is_correct,
                Answer.selected_option_id,
                Answer.created_at,
            )
            .join(Attempt, Answer.attempt_id == Attempt.id)
            .join(Question, Answer.question_id == Question.id)
            .where(Attempt.student_id == student_id)
            .where(Attempt.status.in_(["SUBMITTED", "EXPIRED"]))
            .order_by(Answer.id)
        )
        return self.db.execute(stmt).all()

    def _practice_answer_rows(self, student_id: int):
        """Same tuple shape as assessment rows, for completed practice sessions."""
        stmt = (
            select(
                PracticeAnswer.id,
                PracticeAnswer.question_id,
                Question.topic_id,
                Question.difficulty,
                Question.company_id,
                PracticeAnswer.is_correct,
                PracticeAnswer.selected_option_id,
                PracticeAnswer.created_at,
            )
            .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
            .join(Question, PracticeAnswer.question_id == Question.id)
            .where(PracticeSession.student_id == student_id)
            .where(PracticeSession.status == "COMPLETED")
            .order_by(PracticeAnswer.id)
        )
        return self.db.execute(stmt).all()

    # ============================================================ OVERALL

    def get_overall(self, student_id: int) -> dict:
        practice_rows = self._practice_answer_rows(student_id)
        assessment_rows = self._assessment_answer_rows(student_id)
        all_rows = list(practice_rows) + list(assessment_rows)

        attempted = sum(1 for r in all_rows if r[6] is not None)
        unanswered = sum(1 for r in all_rows if r[6] is None)
        correct = sum(1 for r in all_rows if r[5])
        incorrect = attempted - correct

        total = correct + incorrect
        accuracy = round(correct / total * 100, 2) if total > 0 else None

        practice_attempted_rows = [r for r in practice_rows if r[6] is not None]
        practice_correct = sum(1 for r in practice_attempted_rows if r[5])
        p_total = len(practice_attempted_rows)
        practice_accuracy = round(practice_correct / p_total * 100, 2) if p_total > 0 else None

        session_count = self.db.scalar(
            select(func.count(PracticeSession.id)).where(
                PracticeSession.student_id == student_id,
                PracticeSession.status == "COMPLETED",
            )
        ) or 0

        attempt_count = self.db.scalar(
            select(func.count(Attempt.id)).where(
                Attempt.student_id == student_id,
                Attempt.status == "SUBMITTED",
            )
        ) or 0

        avg_score = self.db.scalar(
            select(func.avg(Attempt.score)).where(
                Attempt.student_id == student_id,
                Attempt.status == "SUBMITTED",
            )
        )

        coding_attempted = self.db.scalar(
            select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                CodeSubmission.student_id == student_id
            )
        ) or 0
        coding_solved = self.db.scalar(
            select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                CodeSubmission.student_id == student_id,
                CodeSubmission.status == "ACCEPTED",
            )
        ) or 0

        return {
            "total_questions_attempted": attempted,
            "correct": correct,
            "incorrect": incorrect,
            "unanswered": unanswered,
            "overall_accuracy": accuracy,
            "practice_sessions": int(session_count),
            "practice_accuracy": practice_accuracy,
            "assessment_attempts": int(attempt_count),
            "assessment_avg_score": round(float(avg_score), 2) if avg_score is not None else None,
            "coding_attempted": int(coding_attempted),
            "coding_solved": int(coding_solved),
        }

    # ============================================================ BY TOPIC

    def get_topic_aggregates(self, student_id: int) -> list[dict]:
        """Per-topic aggregates across practice + assessments, with recent/historical split."""
        rows = list(self._practice_answer_rows(student_id)) + list(self._assessment_answer_rows(student_id))

        topics_meta: dict[int, dict] = {}
        for _row_id, _qid, topic_id, _difficulty, _company, is_correct, selected, created_at in rows:
            if topic_id is None:
                continue
            meta = topics_meta.setdefault(topic_id, {"total": 0, "correct": 0, "last": None})
            if selected is not None:
                meta["total"] += 1
                if is_correct:
                    meta["correct"] += 1
            if created_at and (meta["last"] is None or created_at > meta["last"]):
                meta["last"] = created_at

        # Recent = last 20 answered per topic (chronological); older = everything before.
        per_topic_answered: dict[int, list] = {}
        for row in rows:
            topic_id = row[2]
            if topic_id is None or row[6] is None:
                continue
            per_topic_answered.setdefault(topic_id, []).append(row)

        for topic_id, answered in per_topic_answered.items():
            answered.sort(key=lambda r: (r[7] or datetime.min, r[0]))
            meta = topics_meta[topic_id]
            meta["recent"] = answered[-20:]
            meta["older"] = answered[:-20]

        result = []
        topic_names = self._topic_names(list(topics_meta.keys()))
        for topic_id, meta in topics_meta.items():
            total = meta["total"]
            correct = meta["correct"]
            incorrect = total - correct
            accuracy = round(correct / total * 100, 2) if total > 0 else None

            def _acc(rs: list) -> float | None:
                if not rs:
                    return None
                c = sum(1 for r in rs if r[5])
                return round(c / len(rs) * 100, 2)

            recent_accuracy = _acc(meta["recent"])
            historical_accuracy = _acc(meta["older"])

            if accuracy is None:
                trend = "NEW"
            elif historical_accuracy is None:
                trend = "NEW"
            elif recent_accuracy is None:
                trend = "STABLE"
            elif recent_accuracy >= historical_accuracy + 5:
                trend = "IMPROVING"
            elif recent_accuracy <= historical_accuracy - 5:
                trend = "DECLINING"
            else:
                trend = "STABLE"

            result.append({
                "topic_id": topic_id,
                "topic_name": topic_names.get(topic_id, "Unknown"),
                "category": self._topic_category(topic_id),
                "total_attempts": total,
                "correct": correct,
                "incorrect": incorrect,
                "accuracy": accuracy,
                "recent_accuracy": recent_accuracy if historical_accuracy is not None else None,
                "historical_accuracy": historical_accuracy,
                "trend": trend,
                "last_attempted_at": meta["last"],
            })

        result.sort(key=lambda t: (t["accuracy"] if t["accuracy"] is not None else -1))
        return result

    # ============================================================ BY DIFFICULTY

    def get_difficulty_aggregates(self, student_id: int) -> list[dict]:
        rows = list(self._practice_answer_rows(student_id)) + list(self._assessment_answer_rows(student_id))
        stats: dict[str, dict] = {}
        for _rid, _qid, _topic, difficulty, _company, is_correct, selected, _created in rows:
            if difficulty is None or selected is None:
                continue
            s = stats.setdefault(difficulty, {"total": 0, "correct": 0})
            s["total"] += 1
            if is_correct:
                s["correct"] += 1
        out = []
        for difficulty in ("easy", "medium", "hard"):
            s = stats.get(difficulty)
            if not s:
                continue
            acc = round(s["correct"] / s["total"] * 100, 2) if s["total"] else None
            out.append({
                "difficulty": difficulty,
                "total_attempts": s["total"],
                "correct": s["correct"],
                "accuracy": acc,
            })
        return out

    # ============================================================ BY COMPANY

    def get_company_aggregates(self, student_id: int) -> list[dict]:
        rows = list(self._practice_answer_rows(student_id)) + list(self._assessment_answer_rows(student_id))
        stats: dict[int, dict] = {}
        for _rid, _qid, _topic, _difficulty, company_id, is_correct, selected, _created in rows:
            if company_id is None or selected is None:
                continue
            s = stats.setdefault(company_id, {"total": 0, "correct": 0})
            s["total"] += 1
            if is_correct:
                s["correct"] += 1
        names = self._company_names(list(stats.keys()))
        out = []
        for company_id, s in stats.items():
            acc = round(s["correct"] / s["total"] * 100, 2) if s["total"] else None
            out.append({
                "company_id": company_id,
                "company_name": names.get(company_id, "Unknown"),
                "total_attempts": s["total"],
                "correct": s["correct"],
                "accuracy": acc,
            })
        out.sort(key=lambda c: (c["accuracy"] if c["accuracy"] is not None else -1))
        return out

    # ============================================================ TRENDS

    def get_attempt_trend(self, student_id: int, limit: int = 20) -> list[dict]:
        """Chronological (oldest → newest) submitted attempts with scores."""
        stmt = (
            select(Attempt)
            .where(Attempt.student_id == student_id, Attempt.status == "SUBMITTED")
            .order_by(Attempt.submitted_at.asc(), Attempt.id.asc())
        )
        attempts = list(self.db.scalars(stmt).all())[-limit:]
        return [
            {
                "label": f"Attempt {a.id}",
                "score": round(float(a.score), 2) if a.score is not None else None,
                "accuracy": round(float(a.accuracy), 2) if a.accuracy is not None else None,
                "date": a.submitted_at,
            }
            for a in attempts
        ]

    # ============================================================ TOPIC_PERFORMANCE TABLE

    def get_topic_performance_rows(self, student_id: int) -> list[TopicPerformance]:
        stmt = (
            select(TopicPerformance)
            .where(TopicPerformance.student_id == student_id)
            .order_by(TopicPerformance.topic_id)
        )
        return list(self.db.scalars(stmt).all())

    def upsert_topic_performance(
        self, student: StudentProfile, aggregates: list[dict]
    ) -> list[TopicPerformance]:
        """Persist recomputed topic performance rows (derived data, safe to rebuild)."""
        existing = {
            row.topic_id: row for row in self.get_topic_performance_rows(student_id=student.id)
        }
        saved: list[TopicPerformance] = []
        for agg in aggregates:
            row = existing.get(agg["topic_id"])
            if row is None:
                row = TopicPerformance(student_id=student.id, topic_id=agg["topic_id"])
                self.db.add(row)
            row.total_attempts = agg["total_attempts"]
            row.correct_answers = agg["correct"]
            row.incorrect_answers = agg["incorrect"]
            row.accuracy = agg["accuracy"]
            row.trend = agg["trend"]
            row.last_attempted_at = agg["last_attempted_at"]
            saved.append(row)
        self.db.commit()
        for row in saved:
            self.db.refresh(row)
        return saved

    # ============================================================ SNAPSHOTS

    def add_snapshot(
        self,
        student_id: int,
        *,
        assessment_id: int | None,
        overall_score: float | None,
        accuracy: float | None,
        readiness_score: float | None,
    ) -> PerformanceSnapshot:
        snap = PerformanceSnapshot(
            student_id=student_id,
            assessment_id=assessment_id,
            overall_score=overall_score,
            accuracy=accuracy,
            readiness_score=readiness_score,
        )
        self.db.add(snap)
        self.db.commit()
        self.db.refresh(snap)
        return snap

    def list_snapshots(self, student_id: int, limit: int = 50) -> list[PerformanceSnapshot]:
        stmt = (
            select(PerformanceSnapshot)
            .where(PerformanceSnapshot.student_id == student_id)
            .order_by(PerformanceSnapshot.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    # ============================================================ HELPERS

    def _topic_names(self, topic_ids: list[int]) -> dict[int, str]:
        if not topic_ids:
            return {}
        rows = self.db.execute(
            select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids))
        ).all()
        return {tid: name for tid, name in rows}

    def _topic_category(self, topic_id: int) -> str | None:
        return self.db.scalar(select(Topic.category).where(Topic.id == topic_id))

    def _company_names(self, company_ids: list[int]) -> dict[int, str]:
        if not company_ids:
            return {}
        rows = self.db.execute(
            select(Company.id, Company.name).where(Company.id.in_(company_ids))
        ).all()
        return {cid: name for cid, name in rows}

    # ---------- shared write helpers ----------

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()
