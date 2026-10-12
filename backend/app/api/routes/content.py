"""Content endpoints (docs/API_Specification.md §10, §11, §13).

Phase 2 scope: read-only topic/company endpoints.
Phase 4 scope: public question listing for students (approved questions only).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.content import CompanyRead, TopicRead
from app.schemas.question import QuestionListParams, QuestionRead
from app.services.content import ContentService
from app.services.question import QuestionService
from app.utils.responses import success_response

router = APIRouter(tags=["content"])


def _get_content_service(db: Session = Depends(get_db)) -> ContentService:
    return ContentService(db)


def _get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(db)


# ---------------------------------------------------------------- topics
@router.get("/topics")
def list_topics(
    category: str | None = Query(default=None),
    service: ContentService = Depends(_get_content_service),
):
    """Standard {success, message, data} envelope (contract fix)."""
    return success_response(
        data=[TopicRead.model_validate(t) for t in service.list_topics(category=category)],
        message="Topics retrieved",
    )


@router.get("/topics/{topic_id}")
def get_topic(topic_id: int, service: ContentService = Depends(_get_content_service)):
    return success_response(
        data=TopicRead.model_validate(service.get_topic(topic_id)),
        message="Topic retrieved",
    )


# --------------------------------------------------------------- companies
@router.get("/companies")
def list_companies(service: ContentService = Depends(_get_content_service)):
    return success_response(
        data=[CompanyRead.model_validate(c) for c in service.list_companies()],
        message="Companies retrieved",
    )


@router.get("/companies/{company_id}")
def get_company(company_id: int, service: ContentService = Depends(_get_content_service)):
    return success_response(
        data=CompanyRead.model_validate(service.get_company(company_id)),
        message="Company retrieved",
    )


# ---------------------------------------------------------------- questions
@router.get("/questions")
def list_questions(
    service: QuestionService = Depends(_get_question_service),
    topic_id: int | None = Query(default=None),
    company_id: int | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    category: str | None = Query(default=None),
    question_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Public endpoint: students retrieve approved questions."""
    params = QuestionListParams(
        topic_id=topic_id,
        company_id=company_id,
        difficulty=difficulty,
        category=category,
        question_type=question_type,
        page=page,
        limit=limit,
    )
    questions, total = service.list_approved(params)
    return success_response(
        data={
            "questions": [QuestionRead.model_validate(q) for q in questions],
            "total": total,
            "page": page,
            "limit": limit,
        },
        message="Questions retrieved",
    )


@router.get("/questions/{question_id}")
def get_question(
    question_id: int,
    service: QuestionService = Depends(_get_question_service),
):
    """Public endpoint: students retrieve a single approved question."""
    q = service.get_approved(question_id)
    return success_response(
        data=QuestionRead.model_validate(q),
        message="Question retrieved",
    )
