"""Content service: business rules for topics and companies."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
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

    def update_topic(
        self,
        topic_id: int,
        *,
        name: str | None = None,
        category: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> Topic:
        topic = self.get_topic(topic_id)
        if name is not None and name != topic.name:
            existing = self.topics.get_by_name(name)
            if existing is not None:
                raise ConflictError(f"Topic '{name}' already exists")
            topic.name = name
        if category is not None:
            if not category.strip():
                raise ValidationError("category cannot be empty")
            topic.category = category
        if description is not None:
            topic.description = description
        if is_active is not None:
            topic.is_active = is_active
        return self.topics.save(topic)

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

    def update_company(
        self,
        company_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        website: str | None = None,
        is_active: bool | None = None,
    ) -> Company:
        company = self.get_company(company_id)
        if name is not None and name != company.name:
            existing = self.companies.get_by_name(name)
            if existing is not None:
                raise ConflictError(f"Company '{name}' already exists")
            company.name = name
        if description is not None:
            company.description = description
        if website is not None:
            company.website = website
        if is_active is not None:
            company.is_active = is_active
        return self.companies.save(company)
