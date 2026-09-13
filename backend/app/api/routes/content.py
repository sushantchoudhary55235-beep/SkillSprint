"""Content endpoints (docs/API_Specification.md §10, §13).

Read-only in Phase 2; admin write endpoints arrive in Phase 13.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.content import CompanyRead, TopicRead
from app.services.content import ContentService

router = APIRouter(tags=["content"])


def get_content_service(db: Session = Depends(get_db)) -> ContentService:
    return ContentService(db)


@router.get("/topics", response_model=list[TopicRead])
def list_topics(
    category: str | None = Query(default=None),
    service: ContentService = Depends(get_content_service),
):
    return service.list_topics(category=category)


@router.get("/topics/{topic_id}", response_model=TopicRead)
def get_topic(topic_id: int, service: ContentService = Depends(get_content_service)):
    return service.get_topic(topic_id)


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(service: ContentService = Depends(get_content_service)):
    return service.list_companies()


@router.get("/companies/{company_id}", response_model=CompanyRead)
def get_company(company_id: int, service: ContentService = Depends(get_content_service)):
    return service.get_company(company_id)
