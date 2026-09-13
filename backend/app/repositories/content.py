"""Repository layer: all topic/company database access lives here.

Services call repositories; routes call services (docs/Phases.md §6).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Company, Topic


class TopicRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, category: str | None = None, include_inactive: bool = False) -> list[Topic]:
        stmt = select(Topic)
        if not include_inactive:
            stmt = stmt.where(Topic.is_active.is_(True))
        if category:
            stmt = stmt.where(Topic.category == category)
        return list(self.db.scalars(stmt.order_by(Topic.category, Topic.name)).all())

    def get(self, topic_id: int) -> Topic | None:
        return self.db.get(Topic, topic_id)

    def get_by_name(self, name: str) -> Topic | None:
        return self.db.scalar(select(Topic).where(Topic.name == name))

    def create(self, topic: Topic) -> Topic:
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic


class CompanyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, include_inactive: bool = False) -> list[Company]:
        stmt = select(Company)
        if not include_inactive:
            stmt = stmt.where(Company.is_active.is_(True))
        return list(self.db.scalars(stmt.order_by(Company.name)).all())

    def get(self, company_id: int) -> Company | None:
        return self.db.get(Company, company_id)

    def get_by_name(self, name: str) -> Company | None:
        return self.db.scalar(select(Company).where(Company.name == name))

    def create(self, company: Company) -> Company:
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company
