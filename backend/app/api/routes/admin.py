"""Admin endpoints (docs/API_Specification.md §22).

Phase 3 scope: a minimal admin-only sentinel used to verify RBAC wiring.
Phase 4 scope: question CRUD, topic/company management, teacher question approval.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.content import CompanyCreate, CompanyRead, TopicCreate, TopicRead
from app.schemas.question import (
    QuestionCreate,
    QuestionListParams,
    QuestionReadAdmin,
    QuestionStatusUpdate,
    QuestionUpdate,
)
from app.services.content import ContentService
from app.services.question import QuestionService
from app.utils.responses import success_response

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_question_service(db: Session = Depends(get_db)) -> QuestionService:
    return QuestionService(db)


def _get_content_service(db: Session = Depends(get_db)) -> ContentService:
    return ContentService(db)


# ---------------------------------------------------------------- ping
@router.get("/ping")
def admin_ping(user: Annotated[object, Depends(require_admin)]):
    return success_response(data={"admin_id": user.id}, message="Admin access verified")


# ================================================================ QUESTIONS

@router.get("/questions")
def list_questions(
    user: Annotated[object, Depends(require_admin)],
    service: QuestionService = Depends(_get_question_service),
    topic_id: int | None = Query(default=None),
    company_id: int | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    category: str | None = Query(default=None),
    question_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    params = QuestionListParams(
        topic_id=topic_id,
        company_id=company_id,
        difficulty=difficulty,
        category=category,
        question_type=question_type,
        status=status,
        page=page,
        limit=limit,
    )
    questions, total = service.list_all(params)
    return success_response(
        data={
            "questions": [QuestionReadAdmin.model_validate(q) for q in questions],
            "total": total,
            "page": page,
            "limit": limit,
        },
        message="Questions retrieved",
    )


@router.get("/questions/{question_id}")
def get_question(
    question_id: int,
    user: Annotated[object, Depends(require_admin)],
    service: QuestionService = Depends(_get_question_service),
):
    q = service.get_any(question_id)
    return success_response(
        data=QuestionReadAdmin.model_validate(q),
        message="Question retrieved",
    )


@router.post("/questions", status_code=201)
def create_question(
    data: QuestionCreate,
    user: Annotated[object, Depends(require_admin)],
    service: QuestionService = Depends(_get_question_service),
):
    question = service.create(data, user)
    return success_response(
        data=QuestionReadAdmin.model_validate(question),
        message="Question created",
        status_code=201,
    )


@router.patch("/questions/{question_id}")
def update_question(
    question_id: int,
    data: QuestionUpdate,
    user: Annotated[object, Depends(require_admin)],
    service: QuestionService = Depends(_get_question_service),
):
    question = service.update(question_id, data)
    return success_response(
        data=QuestionReadAdmin.model_validate(question),
        message="Question updated",
    )


@router.patch("/questions/{question_id}/status")
def update_question_status(
    question_id: int,
    data: QuestionStatusUpdate,
    user: Annotated[object, Depends(require_admin)],
    service: QuestionService = Depends(_get_question_service),
):
    question = service.update_status(question_id, data)
    return success_response(
        data=QuestionReadAdmin.model_validate(question),
        message=f"Question status updated to {data.status}",
    )


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    user: Annotated[object, Depends(require_admin)],
    service: QuestionService = Depends(_get_question_service),
):
    service.delete(question_id)
    return success_response(message="Question deleted", status_code=200)


# ================================================================ TOPICS

@router.get("/topics")
def list_topics(
    user: Annotated[object, Depends(require_admin)],
    service: ContentService = Depends(_get_content_service),
):
    topics = service.list_topics()
    return success_response(
        data=[TopicRead.model_validate(t) for t in topics],
        message="Topics retrieved",
    )


@router.post("/topics", status_code=201)
def create_topic(
    data: TopicCreate,
    user: Annotated[object, Depends(require_admin)],
    service: ContentService = Depends(_get_content_service),
):
    topic = service.create_topic(name=data.name, category=data.category, description=data.description)
    return success_response(
        data=TopicRead.model_validate(topic),
        message="Topic created",
        status_code=201,
    )


# ================================================================ COMPANIES

@router.get("/companies")
def list_companies(
    user: Annotated[object, Depends(require_admin)],
    service: ContentService = Depends(_get_content_service),
):
    companies = service.list_companies()
    return success_response(
        data=[CompanyRead.model_validate(c) for c in companies],
        message="Companies retrieved",
    )


@router.post("/companies", status_code=201)
def create_company(
    data: CompanyCreate,
    user: Annotated[object, Depends(require_admin)],
    service: ContentService = Depends(_get_content_service),
):
    company = service.create_company(
        name=data.name, description=data.description, website=data.website
    )
    return success_response(
        data=CompanyRead.model_validate(company),
        message="Company created",
        status_code=201,
    )
