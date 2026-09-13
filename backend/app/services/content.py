"""Content service: business rules for topics and companies."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.content import Company, Topic
from app.repositories.content import CompanyRepository, TopicRepository


class ContentService:
    def __init__(self, db: Session) -> None:
        self.topics = TopicRepository(db)
        self.companies = CompanyRepository(db)

    # ----- Topics -----

    def list_topics(self, category: str | None = None) -> list[Topic]:
        return self.topics.list(category=category)

    def create_topic(self, name: str, category: str, description: str | None = None) -> Topic:
        if self.topics.get_by_name(name):
            raise ConflictError(f"Topic '{name}' already exists")
        return self.topics.create(
            Topic(name=name, category=category, description=description)
        )

    def get_topic(self, topic_id: int) -> Topic:
        topic = self.topics.get(topic_id)
        if topic is None:
            raise NotFoundError(f"Topic {topic_id} not found")
        return topic

    # ----- Companies -----

    def list_companies(self) -> list[Company]:
        return self.companies.list()

    def create_company(
        self, name: str, description: str | None = None, website: str | None = None
    ) -> Company:
        if self.companies.get_by_name(name):
            raise ConflictError(f"Company '{name}' already exists")
        return self.companies.create(Company(name=name, description=description, website=website))

    def get_company(self, company_id: int) -> Company:
        company = self.companies.get(company_id)
        if company is None:
            raise NotFoundError(f"Company {company_id} not found")
        return company
