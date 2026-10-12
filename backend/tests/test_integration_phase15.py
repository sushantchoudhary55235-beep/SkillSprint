"""Phase 15 tests: pagination on list endpoints and concurrent-user safety.

- Pagination: coding problems & submissions, users, questions (?page=&limit=).
- 100+ rows stay fast (no full-table fetch in one response).
- Concurrency: parallel logins + practice submissions against the real
  TestClient/DB session machinery; all must succeed without 500s. Each worker
  gets its own DB session (mirroring production request-scoped sessions);
  they share one file-backed SQLite database.
"""
import concurrent.futures
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


def _login(client: TestClient, email: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> str:
    client.post(
        "/api/auth/register/student",
        json={"name": email.split("@")[0], "email": email, "password": "password123"},
    )
    return _login(client, email)


def _admin(client: TestClient, db, email: str = "pag_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    db.add(User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin"))
    db.commit()
    return _login(client, email, "adminpass123")


@pytest.fixture()
def shared_file_db(db_engine):
    """A file-backed SQLite DB shared by all concurrent worker sessions.

    The default test fixture uses a single in-memory session (one connection);
    real concurrency needs per-request sessions like production.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    import app.models  # noqa: F401 — register all models
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(bind=engine)

    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(path)


# ============================================================ PAGINATION

class TestPagination:
    def test_admin_users_paginated(self, client, db):
        admin = _admin(client, db)
        for i in range(25):
            client.post("/api/auth/register/student",
                        json={"name": f"PagU{i}", "email": f"pagu{i}@example.com",
                              "password": "password123"})

        resp = client.get("/api/admin/users?page=1&limit=10", headers=_auth(admin))
        data = resp.json()["data"]
        assert data["total"] >= 25
        assert len(data["users"]) == 10
        assert data["page"] == 1 and data["limit"] == 10

        resp2 = client.get("/api/admin/users?page=2&limit=10", headers=_auth(admin))
        ids_page1 = {u["id"] for u in data["users"]}
        ids_page2 = {u["id"] for u in resp2.json()["data"]["users"]}
        assert ids_page1.isdisjoint(ids_page2)

    def test_questions_paginated(self, client, db):
        admin = _admin(client, db)
        admin_token = _login(client, "pag_admin@example.com", "adminpass123")
        topic = client.post("/api/admin/topics", headers=_auth(admin_token),
                            json={"name": "PagTopic", "category": "quant"}).json()["data"]
        payload = {
            "question_text": "Q?", "question_type": "MCQ", "topic_id": topic["id"],
            "difficulty": "easy", "explanation": "e",
            "options": [
                {"option_text": "1", "option_order": 1, "is_correct": True},
                {"option_text": "2", "option_order": 2, "is_correct": False},
            ],
        }
        for _ in range(7):
            client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))

        resp = client.get("/api/questions?page=1&limit=3")
        data = resp.json()["data"]
        assert data["total"] == 7
        assert len(data["questions"]) == 3

    def test_coding_problems_paginated(self, client, db):
        from app.models.coding import CodingProblem

        for i in range(12):
            db.add(CodingProblem(title=f"Problem {i}", description="d",
                                 difficulty="EASY", input_format="i",
                                 output_format="o", constraints="c"))
        db.commit()
        token = _register(client, "pag_code@example.com")

        resp = client.get("/api/coding/problems?page=1&limit=5", headers=_auth(token))
        data = resp.json()["data"]
        assert data["total"] == 12
        assert len(data["problems"]) == 5

    def test_submissions_paginated(self, client, db):
        from app.models.coding import CodingProblem, CodeSubmission, TestCase
        from app.models.profile import StudentProfile
        from app.models.user import User

        token = _register(client, "pag_subs@example.com")
        db.add(CodingProblem(title="Subs", description="d", difficulty="EASY",
                             input_format="i", output_format="o", constraints="c"))
        db.flush()
        problem = db.query(CodingProblem).filter_by(title="Subs").first()
        db.add(TestCase(problem_id=problem.id, input_data="1 2", expected_output="3"))
        user = db.query(User).filter_by(email="pag_subs@example.com").first()
        profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
        for _ in range(6):
            db.add(CodeSubmission(student_id=profile.id, problem_id=problem.id,
                                  language="python", source_code="print(3)",
                                  status="WRONG_ANSWER", total_test_cases=1,
                                  passed_test_cases=0))
        db.commit()

        resp = client.get("/api/coding/submissions/me?page=1&limit=4", headers=_auth(token))
        data = resp.json()["data"]
        assert data["total"] == 6
        assert len(data["submissions"]) == 4

    def test_large_dataset_no_timeout(self, client, db):
        """100+ rows: paginated endpoints must respond promptly and correctly."""
        import time

        from app.models.coding import CodingProblem

        for i in range(120):
            db.add(CodingProblem(title=f"Bulk {i}", description="d", difficulty="EASY",
                                 input_format="i", output_format="o", constraints="c"))
        db.commit()
        token = _register(client, "pag_bulk@example.com")

        started = time.monotonic()
        resp = client.get("/api/coding/problems?page=3&limit=20", headers=_auth(token))
        elapsed = time.monotonic() - started
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 120
        assert len(data["problems"]) == 20
        assert elapsed < 5.0, f"paginated list took {elapsed:.2f}s"


# ============================================================ CONCURRENCY

def _get_app():
    from app.main import app

    return app


class TestConcurrency:
    def test_parallel_logins(self, shared_file_db):
        from fastapi.testclient import TestClient as TC

        setup = TestClient(_get_app())
        for i in range(12):
            setup.post("/api/auth/register/student",
                       json={"name": f"ConcL{i}", "email": f"concl{i}@example.com",
                             "password": "password123"})

        def _do_login(i: int):
            c = TC(_get_app())
            resp = c.post("/api/auth/login",
                          json={"email": f"concl{i}@example.com", "password": "password123"})
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(_do_login, range(12)))
        assert all(code == 200 for code in results), results

    def test_parallel_quiz_submissions(self, shared_file_db):
        """10 concurrent students answering practice questions; no 500s."""
        from fastapi.testclient import TestClient as TC

        from app.models.content import Topic
        from app.models.question import Question, QuestionOption

        setup = TestClient(_get_app())
        topic = Topic(name="ConcTopic", category="quant")
        s = shared_file_db()
        s.add(topic)
        s.flush()
        for i in range(5):
            q = Question(question_text=f"Q{i}?", question_type="MCQ",
                         topic_id=topic.id, difficulty="easy", status="approved")
            s.add(q)
            s.flush()
            s.add(QuestionOption(question_id=q.id, option_text=f"{i}",
                                 option_order=1, is_correct=True))
            s.add(QuestionOption(question_id=q.id, option_text="0",
                                 option_order=2, is_correct=False))
        s.commit()
        topic_id = topic.id
        s.close()

        tokens = []
        for i in range(10):
            setup.post("/api/auth/register/student",
                       json={"name": f"ConcS{i}", "email": f"concs{i}@example.com",
                             "password": "password123"})
            tokens.append(_login(setup, f"concs{i}@example.com"))

        def _do_quiz(token: str):
            c = TC(_get_app())
            h = _auth(token)
            start = c.post("/api/students/practice/start", headers=h,
                           json={"topic_id": topic_id, "question_count": 3})
            if start.status_code != 201:
                return start.status_code
            session_id = start.json()["data"]["session_id"]
            for q in start.json()["data"]["questions"]:
                ans = c.post(f"/api/students/practice/{session_id}/answer", headers=h,
                             json={"question_id": q["id"],
                                   "selected_option_id": q["options"][0]["id"]})
                if ans.status_code != 200:
                    return ans.status_code
            done = c.post(f"/api/students/practice/{session_id}/complete", headers=h)
            return done.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(_do_quiz, tokens))
        assert all(code in (200, 201) for code in results), results

    def test_concurrent_same_student_answers_serialized(self, shared_file_db):
        """Same student firing parallel answers: server must not crash (no 5xx)."""
        from fastapi.testclient import TestClient as TC

        from app.models.content import Topic
        from app.models.question import Question, QuestionOption

        setup = TestClient(_get_app())
        topic = Topic(name="ConcTopic2", category="quant")
        s = shared_file_db()
        s.add(topic)
        s.flush()
        q = Question(question_text="Q?", question_type="MCQ", topic_id=topic.id,
                     difficulty="easy", status="approved")
        s.add(q)
        s.flush()
        s.add(QuestionOption(question_id=q.id, option_text="a", option_order=1, is_correct=True))
        s.add(QuestionOption(question_id=q.id, option_text="b", option_order=2, is_correct=False))
        s.commit()
        topic_id = topic.id
        s.close()

        setup.post("/api/auth/register/student",
                   json={"name": "ConcOne", "email": "concone@example.com",
                         "password": "password123"})
        token = _login(setup, "concone@example.com")

        h = _auth(token)
        start = setup.post("/api/students/practice/start", headers=h,
                           json={"topic_id": topic_id, "question_count": 1})
        session_id = start.json()["data"]["session_id"]
        qid = start.json()["data"]["questions"][0]["id"]
        oid = start.json()["data"]["questions"][0]["options"][0]["id"]

        def _answer(_: int):
            c = TC(_get_app())
            return c.post(f"/api/students/practice/{session_id}/answer", headers=h,
                          json={"question_id": qid, "selected_option_id": oid}).status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(_answer, range(4)))
        # at most one accepted; others conflict — but never a 5xx
        assert all(code in (200, 400, 409, 422) for code in results), results

    def test_parallel_ai_generation_no_crash(self, shared_file_db):
        """Concurrent AI generation under the rate limiter: only 200/429/503."""
        from app.core.config import settings
        from app.services import ai as ai_mod

        monkey_key = "test-key"
        settings_orig = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = monkey_key
        old_gen = ai_mod.AIService._generate
        ai_mod.AIService._generate = lambda self, prompt: VALID_AI_JSON
        import app.api.routes.ai as ai_routes
        from app.core.rate_limit import SlidingWindowLimiter

        old_limiter = ai_routes.ai_limiter
        ai_routes.ai_limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60)
        try:
            setup = TestClient(_get_app())
            token = _register(setup, "ai_conc@example.com")

            def _gen(_: int):
                c = TC(_get_app())
                return c.post("/api/ai/questions/generate", headers=_auth(token),
                              json={"company": "TCS", "topic_name": "Percentages",
                                    "difficulty": "easy"}).status_code

            from fastapi.testclient import TestClient as TC

            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(_gen, range(6)))
            assert all(code in (200, 429) for code in results), results
        finally:
            ai_routes.ai_limiter = old_limiter
            ai_mod.AIService._generate = old_gen
            settings.GEMINI_API_KEY = settings_orig


VALID_AI_JSON = (
    '{"question": "What is 25% of 200?", '
    '"options": ["25", "50", "75", "100"], '
    '"correct_answer": "50", '
    '"explanation": "25% of 200 = 50"}'
)
