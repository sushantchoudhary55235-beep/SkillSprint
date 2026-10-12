"""Phase 13 tests: Admin Dashboard.

Covers: user management (list/search/activate/deactivate), topic & company
edit/deactivate, platform analytics, gamification config, and RBAC isolation
(students/teachers rejected everywhere).
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin(client: TestClient, db, email: str = "p13_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    db.add(User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin"))
    db.commit()
    return _login(client, email, "adminpass123")


def _register(client: TestClient, email: str, endpoint: str = "student") -> str:
    client.post(f"/api/auth/register/{endpoint}",
                json={"name": email.split("@")[0], "email": email, "password": "password123"})
    return _login(client, email, "password123")


class TestUserManagement:
    def test_list_users_with_filters(self, client, db):
        admin = _admin(client, db)
        _register(client, "u1@example.com")
        _register(client, "u2@example.com")
        _register(client, "t1@example.com", "teacher")

        resp = client.get("/api/admin/users", headers=_auth(admin))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 4

        # Filter by role
        resp = client.get("/api/admin/users?role=teacher", headers=_auth(admin))
        roles = {u["role"] for u in resp.json()["data"]["users"]}
        assert roles == {"teacher"}

        # Search
        resp = client.get("/api/admin/users?search=u1@", headers=_auth(admin))
        users = resp.json()["data"]["users"]
        assert len(users) == 1 and users[0]["email"] == "u1@example.com"

    def test_deactivate_user_revokes_access(self, client, db):
        admin = _admin(client, db)
        s = _register(client, "deact@example.com")

        # Find the STUDENT's user id (not the admin's) via the users list.
        users = client.get("/api/admin/users?search=deact@", headers=_auth(admin)).json()["data"]["users"]
        student_uid = users[0]["id"]

        resp = client.patch(f"/api/admin/users/{student_uid}/status?is_active=false", headers=_auth(admin))
        assert resp.status_code == 200
        # Deactivated user's token no longer works (get_current_user rejects inactive)
        resp = client.get("/api/students/profile", headers=_auth(s))
        assert resp.status_code == 401

    def test_cannot_deactivate_last_admin(self, client, db):
        admin = _admin(client, db)
        admin_id = client.get("/api/auth/me", headers=_auth(admin)).json()["data"]["id"]
        resp = client.patch(f"/api/admin/users/{admin_id}/status?is_active=false", headers=_auth(admin))
        assert resp.status_code == 422

    def test_users_endpoint_requires_admin(self, client, db):
        s = _register(client, "noadmin@example.com")
        assert client.get("/api/admin/users", headers=_auth(s)).status_code == 403


class TestTopicCompanyManagement:
    def test_update_topic(self, client, db):
        admin = _admin(client, db)
        tid = client.post("/api/admin/topics", headers=_auth(admin),
                          json={"name": "Old Name", "category": "quant"}).json()["data"]["id"]

        resp = client.patch(f"/api/admin/topics/{tid}", headers=_auth(admin),
                            json={"name": "New Name", "description": "d"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    def test_deactivate_topic_hides_from_students(self, client, db):
        admin = _admin(client, db)
        tid = client.post("/api/admin/topics", headers=_auth(admin),
                          json={"name": "HideMe", "category": "quant"}).json()["data"]["id"]

        client.patch(f"/api/admin/topics/{tid}", headers=_auth(admin), json={"is_active": False})

        s = _register(client, "topic_hider@example.com")
        # /api/topics uses the standard {success, message, data} envelope
        topics = client.get("/api/topics", headers=_auth(s)).json()["data"]
        assert all(t["id"] != tid for t in topics)

    def test_duplicate_topic_name_409(self, client, db):
        admin = _admin(client, db)
        client.post("/api/admin/topics", headers=_auth(admin),
                    json={"name": "Unique Topic", "category": "quant"})
        tid = client.post("/api/admin/topics", headers=_auth(admin),
                          json={"name": "Other", "category": "quant"}).json()["data"]["id"]
        resp = client.patch(f"/api/admin/topics/{tid}", headers=_auth(admin),
                            json={"name": "Unique Topic"})
        assert resp.status_code == 409

    def test_update_company(self, client, db):
        admin = _admin(client, db)
        cid = client.post("/api/admin/companies", headers=_auth(admin),
                          json={"name": "Acme"}).json()["data"]["id"]
        resp = client.patch(f"/api/admin/companies/{cid}", headers=_auth(admin),
                            json={"name": "Acme Corp", "is_active": False})
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False


class TestAnalyticsAndConfig:
    def test_platform_analytics(self, client, db):
        admin = _admin(client, db)
        resp = client.get("/api/admin/analytics", headers=_auth(admin))
        assert resp.status_code == 200
        data = resp.json()["data"]
        for key in ("total_students", "total_teachers", "total_questions",
                    "total_assessments", "total_attempts", "active_students_7d"):
            assert key in data

    def test_gamification_config(self, client, db):
        admin = _admin(client, db)
        resp = client.get("/api/admin/gamification/config", headers=_auth(admin))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "xp_rules" in data and "level_thresholds" in data and "badges" in data

    def test_analytics_requires_admin(self, client, db):
        s = _register(client, "analy@example.com")
        assert client.get("/api/admin/analytics", headers=_auth(s)).status_code == 403
