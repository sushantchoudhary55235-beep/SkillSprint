"""Repository layer for practice sessions and answers."""
import random
from datetime import datetime, timezone

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.practice import PracticeAnswer, PracticeSession
from app.models.question import Question, QuestionOption


class PracticeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- questions ----------

    def get_random_questions(
        self,
        *,
        topic_id: int | None = None,
        company_id: int | None = None,
        difficulty: str | None = None,
        count: int = 10,
    ) -> list[Question]:
        """Fetch approved questions matching filters, randomly sampled."""
        stmt = (
            select(Question)
            .where(Question.status == "approved")
            .options(joinedload(Question.options))
        )
        if topic_id is not None:
            stmt = stmt.where(Question.topic_id == topic_id)
        if company_id is not None:
            stmt = stmt.where(Question.company_id == company_id)
        if difficulty is not None:
            stmt = stmt.where(Question.difficulty == difficulty)

        all_q = list(self.db.scalars(stmt).unique().all())
        if len(all_q) <= count:
            return all_q
        return random.sample(all_q, count)

    # ---------- sessions ----------

    def create_session(self, session: PracticeSession) -> PracticeSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_session(self, session_id: int) -> PracticeSession | None:
        stmt = (
            select(PracticeSession)
            .where(PracticeSession.id == session_id)
            .options(joinedload(PracticeSession.answers))
        )
        return self.db.scalars(stmt).unique().first()

    def list_sessions(
        self,
        student_id: int,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PracticeSession], int]:
        base = select(PracticeSession).where(PracticeSession.student_id == student_id)
        total = self.db.scalar(select(func.count(PracticeSession.id)).where(PracticeSession.student_id == student_id)) or 0
        stmt = base.order_by(PracticeSession.id.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all()), total

    # ---------- answers ----------

    def create_answer(self, answer: PracticeAnswer) -> PracticeAnswer:
        self.db.add(answer)
        self.db.flush()
        return answer

    # ---------- progress ----------

    def get_topic_progress(self, student_id: int) -> list[dict]:
        """Aggregate practice answers per topic for a student."""
        from app.models.content import Topic

        stmt = (
            select(
                PracticeAnswer.question_id,
                PracticeAnswer.is_correct,
                Question.topic_id,
            )
            .join(Question, PracticeAnswer.question_id == Question.id)
            .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
            .where(PracticeSession.student_id == student_id)
        )
        rows = self.db.execute(stmt).all()

        # aggregate by topic
        topic_stats: dict[int, dict] = {}
        for question_id, is_correct, topic_id in rows:
            if topic_id is None:
                continue
            if topic_id not in topic_stats:
                topic_stats[topic_id] = {"total": 0, "correct": 0}
            topic_stats[topic_id]["total"] += 1
            if is_correct:
                topic_stats[topic_id]["correct"] += 1

        result = []
        for topic_id, stats in topic_stats.items():
            topic = self.db.get(Topic, topic_id)
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            result.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic.name if topic else "Unknown",
                    "total_attempts": stats["total"],
                    "correct_answers": stats["correct"],
                    "accuracy": round(accuracy, 2),
                    "trend": "stable",  # simple default; Phase 7 will refine
                }
            )
        return result

    def get_overall_stats(self, student_id: int) -> dict:
        """Overall practice statistics for a student."""
        stmt = (
            select(
                func.count(PracticeAnswer.id).label("total"),
                func.sum(func.cast(PracticeAnswer.is_correct, Integer)).label("correct"),
            )
            .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
            .where(PracticeSession.student_id == student_id)
        )
        row = self.db.execute(stmt).one()
        total = row.total or 0
        correct = int(row.correct or 0)
        return {
            "total_questions_attempted": total,
            "total_correct": correct,
            "total_incorrect": total - correct,
            "overall_accuracy": round((correct / total * 100) if total > 0 else 0, 2),
        }

    def get_session_count(self, student_id: int) -> int:
        return self.db.scalar(
            select(func.count(PracticeSession.id)).where(PracticeSession.student_id == student_id)
        ) or 0

    # ---------- daily quiz ----------

    def get_daily_quiz_session(self, student_id: int) -> PracticeSession | None:
        """Check if student already has a daily quiz session for today."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return self.db.scalar(
            select(PracticeSession).where(
                PracticeSession.student_id == student_id,
                PracticeSession.mode == "DAILY_QUIZ",
                PracticeSession.created_at >= today_start,
            )
        )

    # ---------- commit ----------

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)
