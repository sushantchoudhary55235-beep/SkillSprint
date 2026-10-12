"""Phase 15C tests: AI question generation & evaluation.

Covers: valid generation shape, invalid-JSON retry then 503, structural
validation (4 options, distinct, correct answer among options), the
no-persistence rule, deterministic evaluation, XP/streak/readiness updates,
rate limiting (10/min → 429), and RBAC.
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")

VALID_JSON = (
    '{"question": "What is 20% of 500?", '
    '"options": ["80", "100", "120", "150"], '
    '"correct_answer": "100", '
    '"explanation": "20% of 500 = 100"}'
)


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


@pytest.fixture()
def ai_ok(monkeypatch):
    """Healthy Gemini returning a structurally valid question JSON."""
    from app.core.config import settings
    from app.services import ai as ai_mod

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(ai_mod.AIService, "_generate", lambda self, prompt: VALID_JSON)
    return ai_mod


def _gen_payload(topic_id=None, company="TCS", topic_name="Quantitative Aptitude", difficulty="medium"):
    payload = {"company": company, "difficulty": difficulty}
    if topic_id is not None:
        payload["topic_id"] = topic_id
    if topic_name is not None:
        payload["topic_name"] = topic_name
    return payload


class TestGeneration:
    def test_generate_returns_valid_question(self, client, db, ai_ok):
        token = _register(client, "aiq1@example.com")
        resp = client.post("/api/ai/questions/generate", headers=_auth(token),
                           json=_gen_payload(company="TCS", topic_name="Quantitative Aptitude"))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["question"] == "What is 20% of 500?"
        assert len(data["options"]) == 4
        # Security hardening: the answer key NEVER reaches the client.
        assert "correct_answer" not in data
        assert "explanation" not in data
        assert data["ticket"]
        assert data["company"] == "TCS"
        assert data["persisted"] is False

    def test_generated_question_not_saved_to_db(self, client, db, ai_ok):
        token = _register(client, "aiq2@example.com")
        client.post("/api/ai/questions/generate", headers=_auth(token), json=_gen_payload())
        from sqlalchemy import func, select

        from app.models.question import Question

        assert db.scalar(select(func.count(Question.id))) == 0

    def test_invalid_json_retried_then_503(self, client, db, monkeypatch):
        from app.core.config import settings
        from app.services import ai as ai_mod

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key", raising=False)
        calls = {"n": 0}

        def _garbage(self, prompt):
            calls["n"] += 1
            return "Sorry, I cannot help with that."

        monkeypatch.setattr(ai_mod.AIService, "_generate", _garbage)
        token = _register(client, "aiq3@example.com")
        resp = client.post("/api/ai/questions/generate", headers=_auth(token), json=_gen_payload())
        assert resp.status_code == 503
        assert calls["n"] == 2  # one retry

    def test_duplicate_options_rejected(self, client, db, monkeypatch):
        from app.core.config import settings
        from app.services import ai as ai_mod

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key", raising=False)
        dup = ('{"question": "Q?", "options": ["a", "a", "b", "c"], '
               '"correct_answer": "a", "explanation": "e"}')
        monkeypatch.setattr(ai_mod.AIService, "_generate", lambda self, prompt: dup)
        token = _register(client, "aiq4@example.com")
        assert client.post("/api/ai/questions/generate", headers=_auth(token),
                           json=_gen_payload()).status_code == 503

    def test_correct_answer_must_be_an_option(self, client, db, monkeypatch):
        from app.core.config import settings
        from app.services import ai as ai_mod

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key", raising=False)
        bad = ('{"question": "Q?", "options": ["a", "b", "c", "d"], '
               '"correct_answer": "z", "explanation": "e"}')
        monkeypatch.setattr(ai_mod.AIService, "_generate", lambda self, prompt: bad)
        token = _register(client, "aiq5@example.com")
        assert client.post("/api/ai/questions/generate", headers=_auth(token),
                           json=_gen_payload()).status_code == 503

    def test_markdown_fenced_json_accepted(self, client, db, monkeypatch):
        from app.core.config import settings
        from app.services import ai as ai_mod

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key", raising=False)
        fenced = f"```json\n{VALID_JSON}\n```"
        monkeypatch.setattr(ai_mod.AIService, "_generate", lambda self, prompt: fenced)
        token = _register(client, "aiq6@example.com")
        resp = client.post("/api/ai/questions/generate", headers=_auth(token), json=_gen_payload())
        assert resp.status_code == 200

    def test_missing_key_returns_503(self, client, db, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "", raising=False)
        token = _register(client, "aiq7@example.com")
        resp = client.post("/api/ai/questions/generate", headers=_auth(token), json=_gen_payload())
        assert resp.status_code == 503

    def test_unknown_topic_404(self, client, db, ai_ok):
        token = _register(client, "aiq8@example.com")
        resp = client.post("/api/ai/questions/generate", headers=_auth(token),
                           json=_gen_payload(topic_id=9999, topic_name=None))
        assert resp.status_code == 404

    def test_requires_auth(self, client, db, ai_ok):
        assert client.post("/api/ai/questions/generate", json=_gen_payload()).status_code == 401

    def test_teacher_forbidden(self, client, db, ai_ok):
        client.post("/api/auth/register/teacher",
                    json={"name": "Te", "email": "aiq_t@example.com", "password": "password123"})
        token = _login(client, "aiq_t@example.com")
        assert client.post("/api/ai/questions/generate", headers=_auth(token),
                           json=_gen_payload()).status_code == 403

    def test_invalid_difficulty_422(self, client, db, ai_ok):
        token = _register(client, "aiq9@example.com")
        resp = client.post("/api/ai/questions/generate", headers=_auth(token),
                           json=_gen_payload(difficulty="impossible"))
        assert resp.status_code in (422, 503)


class TestEvaluation:
    def _generate(self, client, token):
        resp = client.post(
            "/api/ai/questions/generate",
            headers=_auth(token),
            json={"company": "TCS", "topic_name": "Percentages", "difficulty": "easy"},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()["data"]

    def _evaluate(self, client, token, student_answer="100", ticket=None):
        """Generate a fresh question and answer it (or reuse a ticket)."""
        data = self._generate(client, token)
        return client.post(
            "/api/ai/questions/evaluate",
            headers=_auth(token),
            json={
                "ticket": ticket or data["ticket"],
                "student_answer": student_answer,
                "time_taken_seconds": 10,
            },
        )

    def test_correct_answer_updates_xp_streak_readiness(self, client, db, ai_ok):
        token = _register(client, "aiq10@example.com")
        profile_before = client.get("/api/students/profile", headers=_auth(token)).json()["data"]
        assert profile_before["xp"] == 0

        resp = self._evaluate(client, token, student_answer="100")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["is_correct"] is True
        assert data["xp_earned"] == 5
        assert data["xp_total"] == 5
        assert data["current_streak"] == 1
        assert data["readiness_score"] > 0

    def test_wrong_answer_gives_hint_no_xp(self, client, db, ai_ok):
        token = _register(client, "aiq11@example.com")
        resp = self._evaluate(client, token, student_answer="120")
        data = resp.json()["data"]
        assert data["is_correct"] is False
        assert data["xp_earned"] == 0
        assert data["hint"] is not None  # AI mocked → returns text
        assert data["correct_answer"] == "100"  # revealed AFTER answering

    def test_client_cannot_self_grade(self, client, db, ai_ok):
        """THE critical security property: a client-supplied correct_answer
        (or any fabricated payload) must not influence grading."""
        token = _register(client, "aiq_farm@example.com")
        resp = client.post(
            "/api/ai/questions/evaluate",
            headers=_auth(token),
            json={
                "ticket": "totally-fake-ticket-value",
                "question": "What is 2+2?",
                "options": ["4"],
                "student_answer": "4",
                "correct_answer": "4",  # attacker-chosen key — must be ignored
                "difficulty": "easy",
            },
        )
        assert resp.status_code == 422
        profile = client.get("/api/students/profile", headers=_auth(token)).json()["data"]
        assert profile["xp"] == 0  # no XP from the fabricated payload

    def test_ticket_single_use_replay_rejected(self, client, db, ai_ok):
        token = _register(client, "aiq_replay@example.com")
        data = self._generate(client, token)
        first = client.post(
            "/api/ai/questions/evaluate",
            headers=_auth(token),
            json={"ticket": data["ticket"], "student_answer": "100"},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/ai/questions/evaluate",
            headers=_auth(token),
            json={"ticket": data["ticket"], "student_answer": "100"},
        )
        assert second.status_code == 422

    def test_ticket_owned_by_another_student_rejected(self, client, db, ai_ok):
        t1 = _register(client, "aiq_own1@example.com")
        data = self._generate(client, t1)
        t2 = _register(client, "aiq_own2@example.com")
        resp = client.post(
            "/api/ai/questions/evaluate",
            headers=_auth(t2),
            json={"ticket": data["ticket"], "student_answer": "100"},
        )
        assert resp.status_code == 422

    def test_evaluation_records_answer_not_question(self, client, db, ai_ok):
        token = _register(client, "aiq12@example.com")
        self._evaluate(client, token)
        from sqlalchemy import func, select

        from app.models.question import Question

        assert db.scalar(select(func.count(Question.id))) == 0  # question never stored

    def test_empty_answer_422(self, client, db, ai_ok):
        token = _register(client, "aiq13@example.com")
        data = self._generate(client, token)
        resp = client.post(
            "/api/ai/questions/evaluate",
            headers=_auth(token),
            json={"ticket": data["ticket"], "student_answer": ""},
        )
        assert resp.status_code == 422

    def test_evaluate_is_rate_limited(self, client, db, ai_ok):
        """evaluate writes rows + awards XP → it must be throttled too."""
        import app.api.routes.ai as ai_routes
        from app.core.rate_limit import SlidingWindowLimiter

        old_limiter = ai_routes.ai_limiter
        # Each round = 1 generate + 1 evaluate = 2 hits. Budget 4 → two full
        # rounds pass; the third round's generate trips the limiter.
        ai_routes.ai_limiter = SlidingWindowLimiter(max_requests=4, window_seconds=60)
        try:
            token = _register(client, "aiq_rl_eval@example.com")
            for _ in range(2):
                resp = self._evaluate(client, token, student_answer="100")
                assert resp.status_code == 200
            resp = client.post(
                "/api/ai/questions/generate",
                headers=_auth(token),
                json={"company": "TCS", "topic_name": "Percentages", "difficulty": "easy"},
            )
            assert resp.status_code == 429
            # And evaluate is equally blocked (same shared budget).
            data = resp.json()
            assert data["error_code"] == "RATE_LIMITED"
        finally:
            ai_routes.ai_limiter = old_limiter


class TestAIRateLimit:
    def test_rate_limit_429_after_10(self, client, db, ai_ok):
        from app.core.rate_limit import SlidingWindowLimiter

        token = _register(client, "aiq_rl@example.com")
        # Fresh limiter for this test (10/min).
        from app.services import ai as ai_mod

        import app.api.routes.ai as ai_routes

        limiter = SlidingWindowLimiter(max_requests=10, window_seconds=60)
        original = ai_routes._enforce_ai_rate_limit.__wrapped__ if hasattr(
            ai_routes._enforce_ai_rate_limit, "__wrapped__") else None

        # Patch the module-level limiter used by the routes.
        monkey = ai_ok
        old_limiter = ai_routes.ai_limiter
        ai_routes.ai_limiter = limiter
        try:
            for _ in range(10):
                resp = client.post("/api/ai/hint", headers=_auth(token),
                                   json={"question_text": "x"})
                assert resp.status_code == 200
            resp = client.post("/api/ai/hint", headers=_auth(token),
                               json={"question_text": "x"})
            assert resp.status_code == 429
            body = resp.json()
            assert body["error_code"] == "RATE_LIMITED"
            assert "10" in body["message"]
            assert resp.headers.get("Retry-After") is not None
        finally:
            ai_routes.ai_limiter = old_limiter

    def test_per_user_isolation(self, client, db, ai_ok):
        import app.api.routes.ai as ai_routes
        from app.core.rate_limit import SlidingWindowLimiter

        old_limiter = ai_routes.ai_limiter
        ai_routes.ai_limiter = SlidingWindowLimiter(max_requests=1, window_seconds=60)
        try:
            t1 = _register(client, "aiq_rl1@example.com")
            t2 = _register(client, "aiq_rl2@example.com")
            assert client.post("/api/ai/hint", headers=_auth(t1),
                               json={"question_text": "x"}).status_code == 200
            # user1 blocked, user2 unaffected
            assert client.post("/api/ai/hint", headers=_auth(t1),
                               json={"question_text": "x"}).status_code == 429
            assert client.post("/api/ai/hint", headers=_auth(t2),
                               json={"question_text": "x"}).status_code == 200
        finally:
            ai_routes.ai_limiter = old_limiter
