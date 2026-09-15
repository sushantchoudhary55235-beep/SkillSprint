"""Repository layer for questions and question options."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.question import Question, QuestionOption


class QuestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- reads ----------

    def get(self, question_id: int, *, options_loaded: bool = False) -> Question | None:
        stmt = select(Question)
        if options_loaded:
            stmt = stmt.options(joinedload(Question.options))
        return self.db.get(Question, question_id)

    def list(
        self,
        *,
        topic_id: int | None = None,
        company_id: int | None = None,
        difficulty: str | None = None,
        category: str | None = None,
        question_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Question]:
        stmt = select(Question).options(joinedload(Question.options))

        if topic_id is not None:
            stmt = stmt.where(Question.topic_id == topic_id)
        if company_id is not None:
            stmt = stmt.where(Question.company_id == company_id)
        if difficulty is not None:
            stmt = stmt.where(Question.difficulty == difficulty)
        if question_type is not None:
            stmt = stmt.where(Question.question_type == question_type)
        if status is not None:
            stmt = stmt.where(Question.status == status)

        # Category filtering requires a JOIN on topics table.
        if category is not None:
            from app.models.content import Topic

            stmt = stmt.join(Topic, Question.topic_id == Topic.id).where(
                Topic.category == category
            )

        stmt = stmt.order_by(Question.id.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).unique().all())

    def count(
        self,
        *,
        topic_id: int | None = None,
        company_id: int | None = None,
        difficulty: str | None = None,
        category: str | None = None,
        question_type: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count(Question.id))

        if topic_id is not None:
            stmt = stmt.where(Question.topic_id == topic_id)
        if company_id is not None:
            stmt = stmt.where(Question.company_id == company_id)
        if difficulty is not None:
            stmt = stmt.where(Question.difficulty == difficulty)
        if question_type is not None:
            stmt = stmt.where(Question.question_type == question_type)
        if status is not None:
            stmt = stmt.where(Question.status == status)
        if category is not None:
            from app.models.content import Topic

            stmt = stmt.join(Topic, Question.topic_id == Topic.id).where(
                Topic.category == category
            )

        return self.db.scalar(stmt) or 0

    # ---------- writes ----------

    def create(self, question: Question) -> Question:
        self.db.add(question)
        self.db.flush()  # get PK without committing
        return question

    def create_option(self, option: QuestionOption) -> QuestionOption:
        self.db.add(option)
        self.db.flush()
        return option

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)
