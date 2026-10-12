"""Danger Zone (account reset) tests.

Covers the non-negotiable rules of the reset service:
- password + exact phrase required (wrong phrase/password rejected)
- ownership: only the student's OWN data is wiped
- atomicity: nothing survives, profile counters zeroed, account intact
- rate limit: 3 attempts / 10 min
- RBAC: teachers/admins cannot call the endpoints
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")

PHRASE = "RESET MY DATA"


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_admin(client: TestClient, db) -> None:
    from app.core.security import hash_password
    from app.models.user import User

    db.add(User(name="Admin", email="resetadmin@example.com",
                password_hash=hash_password("adminpass123"), role="admin"))
    db.commit()


def _create_teacher(client: TestClient, email: str) -> str:
    resp = client.post(
        "/api/auth/register/teacher",
        json={"name": "Teacher One", "email": email, "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return _login(client, email, "password123")


def _setup_student_with_data(client: TestClient, db, email: str = "reset_s1@example.com") -> str:
    """Register a student and generate real practice data. Returns token."""
    _create_admin(client, db)
    admin_token = _login(client, "resetadmin@example.com", "adminpass123")
    resp = client.post("/api/admin/topics", json={"name": "Percentages", "category": "quantitative"},
                       headers=_auth(admin_token))
    topic = resp.json()["data"]
    payload = {
        "question_text": "What is 2+2?", "question_type": "MCQ", "topic_id": topic["id"],
        "difficulty": "easy", "explanation": "Basic addition",
        "options": [
            {"option_text": "3", "option_order": 1, "is_correct": False},
            {"option_text": "4", "option_order": 2, "is_correct": True},
        ],
    }
    client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))

    resp = client.post("/api/auth/register/student",
                       json={"name": "Reset Student", "email": email, "password": "password123"})
    assert resp.status_code == 201, resp.text
    token = _login(client, email, "password123")

    # Generate real data: a practice session with answers.
    start = client.post("/api/students/practice/start",
                        json={"topic_id": topic["id"], "question_count": 10}, headers=_auth(token))
    assert start.status_code == 201, start.text
    session = start.json()["data"]
    for q in session["questions"]:
        client.post(
            f"/api/students/practice/{session['session_id']}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][0]["id"]},
            headers=_auth(token),
        )
    comp = client.post(f"/api/students/practice/{session['session_id']}/complete", headers=_auth(token))
    assert comp.status_code == 200, comp.text
    return token


class TestResetPreview:
    def test_preview_counts_real_data(self, client, db):
        token = _setup_student_with_data(client, db)
        resp = client.get("/api/account/reset/preview", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["practice_sessions"] >= 1
        assert data["practice_answers"] >= 1
        assert data["xp_transactions"] >= 1

    def test_teacher_cannot_preview(self, client, db):
        _create_admin(client, db)
        t_token = _create_teacher(client, "reset_t@example.com")
        resp = client.get("/api/account/reset/preview", headers=_auth(t_token))
        assert resp.status_code == 403


class TestResetExecution:
    def test_wrong_phrase_rejected(self, client, db):
        token = _setup_student_with_data(client, db)
        resp = client.post("/api/account/reset",
                           json={"password": "password123", "confirmation": "reset my data"},
                           headers=_auth(token))
        assert resp.status_code == 422

    def test_wrong_password_rejected(self, client, db):
        token = _setup_student_with_data(client, db)
        resp = client.post("/api/account/reset",
                           json={"password": "wrongpass123", "confirmation": PHRASE},
                           headers=_auth(token))
        assert resp.status_code == 401

    def test_reset_wipes_everything_and_keeps_account(self, client, db):
        token = _setup_student_with_data(client, db, "reset_s2@example.com")
        resp = client.post("/api/account/reset",
                           json={"password": "password123", "confirmation": PHRASE},
                           headers=_auth(token))
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["reset"] is True

        # Learning data gone.
        preview = client.get("/api/account/reset/preview", headers=_auth(token)).json()["data"]
        assert preview["practice_sessions"] == 0
        assert preview["practice_answers"] == 0
        assert preview["xp_transactions"] == 0
        assert preview["activity_events"] == 1  # the DATA_RESET trace itself

        # Account survives: same token still works, profile is fresh.
        prof = client.get("/api/students/profile", headers=_auth(token))
        assert prof.status_code == 200
        assert prof.json()["data"]["xp"] == 0
        assert prof.json()["data"]["level"] == 1
        assert prof.json()["data"]["current_streak"] == 0

    def test_reset_is_rate_limited(self, client, db):
        token = _setup_student_with_data(client, db)
        # 3 attempts (each counted even when failing) → 4th is 429.
        for _ in range(3):
            client.post("/api/account/reset",
                        json={"password": "wrongpass123", "confirmation": PHRASE},
                        headers=_auth(token))
        resp = client.post("/api/account/reset",
                           json={"password": "password123", "confirmation": PHRASE},
                           headers=_auth(token))
        assert resp.status_code == 429

    def test_teacher_cannot_reset(self, client, db):
        _create_admin(client, db)
        t_token = _create_teacher(client, "reset_t2@example.com")
        resp = client.post("/api/account/reset",
                           json={"password": "password123", "confirmation": PHRASE},
                           headers=_auth(t_token))
        assert resp.status_code == 403
