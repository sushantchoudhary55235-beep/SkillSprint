"""Root pytest configuration.

- Expose the app package on sys.path.
- Provide shared fixtures: an in-memory SQLite database per test and a
  TestClient with the database dependency overridden.
"""
import os
import sys
from pathlib import Path

# Drop bcrypt cost to its minimum for test speed BEFORE app.core.security is
# imported anywhere (registration/login hashing dominates the suite otherwise).
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.models  # noqa: E402,F401  -- register all models
from app.db.base import Base  # noqa: E402

TEST_DB_URL = "sqlite://"  # in-memory


@pytest.fixture()
def db_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(db_engine) -> Session:
    factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the process-wide AI rate limiter between tests.

    User ids restart at 1 in every fresh test database, so limiter state must
    not leak across tests.
    """
    from app.core.rate_limit import ai_limiter

    ai_limiter._hits.clear()
    yield
    ai_limiter._hits.clear()
    # Danger Zone reset limiter shares the same per-test reset need: user ids
    # restart at 1 in every fresh DB, so attempt history must not leak.
    from app.services import student_reset

    student_reset._reset_attempts.clear()


@pytest.fixture()
def client(db):
    """FastAPI TestClient with the database dependency overridden."""
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
