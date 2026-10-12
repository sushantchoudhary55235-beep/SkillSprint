"""Phase 8 tests: Personalization Engine.

The CRITICAL requirement: two students with different performance histories
must receive different recommendations (docs/Phases.md §12).
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


# ---- helpers (mirrors test_performance.py) ----

def _login(client: TestClient, email: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> str:
    resp = client.post(
        "/api/auth/register/student",
        json={"name": email.split("@")[0], "email": email, "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return _login(client, email)


def _create_admin(client: TestClient, db, email: str = "rec_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    return _login(client, email, "adminpass123")


def _topic(client: TestClient, admin_token: str, name: str, category: str = "quantitative") -> dict:
    resp = client.post("/api/admin/topics", json={"name": name, "category": category}, headers=_auth(admin_token))
    assert resp.status_code == 201
    return resp.json()["data"]


def _question(client: TestClient, admin_token: str, topic_id: int, difficulty: str = "easy") -> dict:
    payload = {
        "question_text": f"Q topic={topic_id} diff={difficulty}",
        "question_type": "MCQ",
        "topic_id": topic_id,
        "difficulty": difficulty,
        "options": [
            {"option_text": "a", "option_order": 1, "is_correct": False},
            {"option_text": "b", "option_order": 2, "is_correct": True},
            {"option_text": "c", "option_order": 3, "is_correct": False},
            {"option_text": "d", "option_order": 4, "is_correct": False},
        ],
    }
    resp = client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))
    assert resp.status_code == 201
    return resp.json()["data"]


def _practice(client: TestClient, token: str, topic_id: int, questions: list[dict], outcomes: list[bool]) -> None:
    resp = client.post(
        "/api/students/practice/start",
        json={"topic_id": topic_id, "question_count": len(questions)},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    sid = resp.json()["data"]["session_id"]
    for q, ok in zip(questions, outcomes):
        client.post(
            f"/api/students/practice/{sid}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1 if ok else 0]["id"]},
            headers=_auth(token),
        )
    resp = client.post(f"/api/students/practice/{sid}/complete", headers=_auth(token))
    assert resp.status_code == 200


def _recs(client: TestClient, token: str) -> list[dict]:
    resp = client.get("/api/recommendations/me", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["recommendations"]


# ============================================================ CORE RULES

class TestRecommendationGeneration:
    def test_new_student_gets_no_recommendations(self, client, db):
        """No performance data → no fabricated recommendations."""
        token = _register(client, "empty@example.com")
        assert _recs(client, token) == []

    def test_weak_topic_recommends_practice_low_difficulty(self, client, db):
        token = _register(client, "weak@example.com")
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Time & Work")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        _practice(client, token, t["id"], qs, [False, False, False, True])  # 25%

        recs = _recs(client, token)
        assert len(recs) >= 1
        r = recs[0]
        assert r["topic_id"] == t["id"]
        assert r["recommendation_type"] == "PRACTICE_TOPIC"
        assert r["priority"] in ("HIGH", "MEDIUM")
        assert r["recommended_difficulty"] in ("easy", "medium")
        assert "25%" in r["reason"]
        assert r["status"] == "ACTIVE"

    def test_moderate_topic_recommends_medium_practice(self, client, db):
        token = _register(client, "moderate@example.com")
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Percentages")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        _practice(client, token, t["id"], qs, [True, True, True, False])  # 75%

        recs = _recs(client, token)
        assert len(recs) == 1
        assert recs[0]["recommended_difficulty"] == "medium"
        assert "80%" in recs[0]["reason"]

    def test_strong_topic_recommends_assessment(self, client, db):
        token = _register(client, "strong@example.com")
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Ratio")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        _practice(client, token, t["id"], qs, [True, True, True, True])  # 100%

        recs = _recs(client, token)
        assert len(recs) == 1
        assert recs[0]["recommendation_type"] == "TAKE_TOPIC_TEST"
        assert "mastered" in recs[0]["reason"]

    def test_minimum_sample_size_required(self, client, db):
        """1-2 attempts are too few to base a recommendation on."""
        token = _register(client, "small@example.com")
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Probability")
        qs = [_question(client, admin, t["id"]) for _ in range(2)]
        _practice(client, token, t["id"], qs, [False, False])

        assert _recs(client, token) == []


class TestDifferentiatedRecommendations:
    def test_two_weak_students_get_different_recommendations(self, client, db):
        """THE critical test: Student A weak in Percentages, Student B weak in
        Logical Reasoning → their top recommendations must differ."""
        admin = _create_admin(client, db)
        t_pct = _topic(client, admin, "Percentages")
        t_lr = _topic(client, admin, "Logical Reasoning", "logical")

        pct_qs = [_question(client, admin, t_pct["id"]) for _ in range(4)]
        lr_qs = [_question(client, admin, t_lr["id"]) for _ in range(4)]

        # Student A: fails Percentages, aces Logical Reasoning
        a = _register(client, "studentA@example.com")
        _practice(client, a, t_pct["id"], pct_qs, [False] * 4)
        _practice(client, a, t_lr["id"], lr_qs, [True] * 4)

        # Student B: the opposite
        b = _register(client, "studentB@example.com")
        _practice(client, b, t_pct["id"], pct_qs, [True] * 4)
        _practice(client, b, t_lr["id"], lr_qs, [False] * 4)

        recs_a = _recs(client, a)
        recs_b = _recs(client, b)

        assert len(recs_a) >= 1
        assert len(recs_b) >= 1
        # Weakest topic first for each student
        assert recs_a[0]["topic_id"] == t_pct["id"]
        assert recs_b[0]["topic_id"] == t_lr["id"]
        # And the full lists are not identical
        assert recs_a != recs_b

    def test_recommendations_update_after_new_performance(self, client, db):
        """After practicing a weak topic up to mastery, recommendation changes."""
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Profit & Loss")
        qs = [_question(client, admin, t["id"]) for _ in range(8)]

        token = _register(client, "improver@example.com")
        _practice(client, token, t["id"], qs[:4], [False, False, False, False])  # weak
        first = _recs(client, token)
        assert first[0]["recommended_difficulty"] in ("easy", "medium")

        # Student improves: aces 4 more
        _practice(client, token, t["id"], qs[4:], [True] * 4)  # now 50% overall
        resp = client.post("/api/recommendations/generate", headers=_auth(token))
        assert resp.status_code == 200

        recs = _recs(client, token)
        if recs:  # 50% is still weak → same type but reason reflects new accuracy
            assert "50%" in recs[0]["reason"]

    def test_completed_recommendation_no_longer_active(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Averages")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        token = _register(client, "completer@example.com")
        _practice(client, token, t["id"], qs, [False] * 4)

        recs = _recs(client, token)
        rec_id = recs[0]["id"]
        resp = client.post(f"/api/recommendations/{rec_id}/complete", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["completed"] is True

        # Completed rec disappears from active list; regenerating produces new one
        active = _recs(client, token)
        assert all(r["id"] != rec_id for r in active)


# ============================================================ SECURITY

class TestRecommendationSecurity:
    def test_student_cannot_complete_others_recommendation(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Puzzles")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        owner = _register(client, "owner@example.com")
        _practice(client, owner, t["id"], qs, [False] * 4)
        rec_id = _recs(client, owner)[0]["id"]

        other = _register(client, "other@example.com")
        resp = client.post(f"/api/recommendations/{rec_id}/complete", headers=_auth(other))
        assert resp.status_code == 404

        # Owner's recommendation is untouched
        assert _recs(client, owner)[0]["id"] == rec_id

    def test_teacher_cannot_access_recommendations(self, client, db):
        resp = client.post(
            "/api/auth/register/teacher",
            json={"name": "Teacher One", "email": "rec_teacher@example.com", "password": "password123",
                  "department": "CSE"},
        )
        assert resp.status_code == 201
        token = _login(client, "rec_teacher@example.com")
        resp = client.get("/api/recommendations/me", headers=_auth(token))
        assert resp.status_code == 403

    def test_unauthenticated_access_denied(self, client, db):
        resp = client.get("/api/recommendations/me")
        assert resp.status_code == 401
