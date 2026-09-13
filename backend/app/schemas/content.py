"""Pydantic schemas for content entities (topics, companies)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TopicBase(BaseModel):
    name: str
    category: str
    description: str | None = None


class TopicCreate(TopicBase):
    pass


class TopicRead(TopicBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class CompanyBase(BaseModel):
    name: str
    description: str | None = None
    website: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
