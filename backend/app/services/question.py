"""Question service: business rules for question CRUD and approval workflow.

Phase 4 completion criteria (docs/Phases.md §8):
- Questions can be created.
- Questions can be categorized.
- Topics can be assigned.
- Companies can be assigned.
- Difficulty can be assigned.
- Teachers can submit questions.
- Admin can approve/reject questions.
- Students can retrieve approved questions.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.content import Company, Topic
from app.models.question import Question, QuestionOption
from app.models.user import User, UserRole
from app.repositories.question import QuestionRepository
from app.schemas.question import (
    QuestionCreate,
    QuestionListParams,
    QuestionRead,
    QuestionReadAdmin,
    QuestionStatusUpdate,
    QuestionUpdate,
)


class QuestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = QuestionRepository(db)

    # ---------- public / student read ----------

    def list_approved(self, params: QuestionListParams) -> tuple[list[Question], int]:
        """Return approved questions with pagination metadata."""
        offset = (params.page - 1) * params.limit
        questions = self.repo.list(
            topic_id=params.topic_id,
            company_id=params.company_id,
            difficulty=params.difficulty,
            category=params.category,
            question_type=params.question_type,
            status="approved",
            offset=offset,
            limit=params.limit,
        )
        total = self.repo.count(
            topic_id=params.topic_id,
            company_id=params.company_id,
            difficulty=params.difficulty,
            category=params.category,
            question_type=params.question_type,
            status="approved",
        )
        return questions, total

    def get_approved(self, question_id: int) -> Question:
        q = self.repo.get(question_id, options_loaded=True)
        if q is None or q.status != "approved":
            raise NotFoundError(f"Question {question_id} not found")
        return q

    # ---------- admin full access ----------

    def list_all(self, params: QuestionListParams) -> tuple[list[Question], int]:
        offset = (params.page - 1) * params.limit
        questions = self.repo.list(
            topic_id=params.topic_id,
            company_id=params.company_id,
            difficulty=params.difficulty,
            category=params.category,
            question_type=params.question_type,
            status=params.status,
            offset=offset,
            limit=params.limit,
        )
        total = self.repo.count(
            topic_id=params.topic_id,
            company_id=params.company_id,
            difficulty=params.difficulty,
            category=params.category,
            question_type=params.question_type,
            status=params.status,
        )
        return questions, total

    def get_any(self, question_id: int) -> Question:
        q = self.repo.get(question_id, options_loaded=True)
        if q is None:
            raise NotFoundError(f"Question {question_id} not found")
        return q

    def create(self, data: QuestionCreate, user: User) -> Question:
        """Admin creates an approved question directly."""
        self._validate_foreign_keys(data.topic_id, data.company_id)

        question = Question(
            question_text=data.question_text,
            question_type=data.question_type,
            topic_id=data.topic_id,
            company_id=data.company_id,
            difficulty=data.difficulty,
            explanation=data.explanation,
            source_type="ADMIN",
            created_by=user.id,
            status="approved",
        )
        self.repo.create(question)

        for opt in data.options:
            option = QuestionOption(
                question_id=question.id,
                option_text=opt.option_text,
                option_order=opt.option_order,
                is_correct=opt.is_correct,
            )
            self.repo.create_option(option)

        self.repo.commit()
        self.repo.refresh(question)
        # reload with options
        return self.repo.get(question.id, options_loaded=True)  # type: ignore[return-value]

    def update(self, question_id: int, data: QuestionUpdate) -> Question:
        question = self.repo.get(question_id, options_loaded=True)
        if question is None:
            raise NotFoundError(f"Question {question_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields to update")

        if "topic_id" in update_data or "company_id" in update_data:
            self._validate_foreign_keys(
                update_data.get("topic_id", question.topic_id),
                update_data.get("company_id", question.company_id),
            )

        for field, value in update_data.items():
            setattr(question, field, value)

        self.repo.commit()
        self.repo.refresh(question)
        return question

    def update_status(self, question_id: int, data: QuestionStatusUpdate) -> Question:
        question = self.repo.get(question_id)
        if question is None:
            raise NotFoundError(f"Question {question_id} not found")
        question.status = data.status
        self.repo.commit()
        self.repo.refresh(question)
        return question

    def delete(self, question_id: int) -> None:
        question = self.repo.get(question_id)
        if question is None:
            raise NotFoundError(f"Question {question_id} not found")
        self.db.delete(question)
        self.repo.commit()

    # ---------- teacher submission ----------

    def submit(self, data: QuestionCreate, teacher: User) -> Question:
        """Teacher creates a question that starts in PENDING status."""
        self._validate_foreign_keys(data.topic_id, data.company_id)

        question = Question(
            question_text=data.question_text,
            question_type=data.question_type,
            topic_id=data.topic_id,
            company_id=data.company_id,
            difficulty=data.difficulty,
            explanation=data.explanation,
            source_type="TEACHER",
            created_by=teacher.id,
            status="pending",
        )
        self.repo.create(question)

        for opt in data.options:
            option = QuestionOption(
                question_id=question.id,
                option_text=opt.option_text,
                option_order=opt.option_order,
                is_correct=opt.is_correct,
            )
            self.repo.create_option(option)

        self.repo.commit()
        self.repo.refresh(question)
        return self.repo.get(question.id, options_loaded=True)  # type: ignore[return-value]

    # ---------- helpers ----------

    def _validate_foreign_keys(self, topic_id: int, company_id: int | None) -> None:
        if self.db.get(Topic, topic_id) is None:
            raise NotFoundError(f"Topic {topic_id} not found")
        if company_id is not None and self.db.get(Company, company_id) is None:
            raise NotFoundError(f"Company {company_id} not found")
