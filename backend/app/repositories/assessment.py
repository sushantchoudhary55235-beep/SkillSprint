"""Repository layer for assessments, attempts, and answers."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.assessment import Answer, Assessment, AssessmentQuestion, Attempt
from app.models.question import Question, QuestionOption
from app.models.content import Topic


class AssessmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- assessments ----------

    def get_assessment(self, assessment_id: int) -> Assessment | None:
        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(joinedload(Assessment.assessment_questions))
        )
        return self.db.scalars(stmt).unique().first()

    def list_active_assessments(self, offset: int = 0, limit: int = 20) -> tuple[list[Assessment], int]:
        base = select(Assessment).where(Assessment.is_active.is_(True))
        total = self.db.scalar(
            select(func.count(Assessment.id)).where(Assessment.is_active.is_(True))
        ) or 0
        stmt = base.order_by(Assessment.id.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all()), total

    def list_all_assessments(self, offset: int = 0, limit: int = 20) -> tuple[list[Assessment], int]:
        base = select(Assessment)
        total = self.db.scalar(select(func.count(Assessment.id))) or 0
        stmt = base.order_by(Assessment.id.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all()), total

    def create_assessment(self, assessment: Assessment) -> Assessment:
        self.db.add(assessment)
        self.db.flush()
        return assessment

    def add_assessment_question(self, aq: AssessmentQuestion) -> AssessmentQuestion:
        self.db.add(aq)
        self.db.flush()
        return aq

    def get_assessment_question_ids(self, assessment_id: int) -> list[int]:
        stmt = (
            select(AssessmentQuestion.question_id)
            .where(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.question_order)
        )
        return list(self.db.scalars(stmt).all())

    # ---------- attempts ----------

    def create_attempt(self, attempt: Attempt) -> Attempt:
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def get_attempt(self, attempt_id: int) -> Attempt | None:
        stmt = (
            select(Attempt)
            .where(Attempt.id == attempt_id)
            .options(joinedload(Attempt.answers))
        )
        return self.db.scalars(stmt).unique().first()

    def get_active_attempt(self, student_id: int, assessment_id: int) -> Attempt | None:
        """Check if student already has an in-progress attempt for this assessment."""
        return self.db.scalar(
            select(Attempt).where(
                Attempt.student_id == student_id,
                Attempt.assessment_id == assessment_id,
                Attempt.status == "IN_PROGRESS",
            )
        )

    def list_student_attempts(
        self, student_id: int, offset: int = 0, limit: int = 20
    ) -> tuple[list[dict], int]:
        """List attempts with assessment titles."""
        total = self.db.scalar(
            select(func.count(Attempt.id)).where(Attempt.student_id == student_id)
        ) or 0

        stmt = (
            select(Attempt, Assessment.title)
            .join(Assessment, Attempt.assessment_id == Assessment.id)
            .where(Attempt.student_id == student_id)
            .order_by(Attempt.id.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "attempt": attempt,
                "assessment_title": title,
            }
            for attempt, title in rows
        ], total

    # ---------- answers ----------

    def create_answer(self, answer: Answer) -> Answer:
        self.db.add(answer)
        self.db.flush()
        return answer

    def get_existing_answer(self, attempt_id: int, question_id: int) -> Answer | None:
        return self.db.scalar(
            select(Answer).where(
                Answer.attempt_id == attempt_id,
                Answer.question_id == question_id,
            )
        )

    # ---------- commit ----------

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)
