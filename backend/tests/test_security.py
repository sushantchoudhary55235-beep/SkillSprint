"""Phase 15 tests: authentication, authorization, validation envelopes,
secret leakage, and CORS behaviour (master prompt Phase 15 §2, §3, §5, §7).
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


def _register(client: TestClient, email: str, role: str = "student") -> str:
    client.post(
        f"/api/auth/register/{role}",
        json={"name": email.split("@")[0], "email": email, "password": "password123"},
    )
    return _login(client, email, "password123")


def _admin(client: TestClient, db, email: str = "sec_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    db.add(User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin"))
    db.commit()
    return _login(client, email, "adminpass123")


class TestAuthentication:
    def test_missing_token_returns_401(self, client, db):
        for path in ("/api/students/profile", "/api/admin/users", "/api/gamification/me"):
            resp = client.get(path)
            assert resp.status_code == 401, path
            body = resp.json()
            assert body["success"] is False
            assert body["error_code"] == "UNAUTHORIZED"

    def test_garbage_token_returns_401(self, client, db):
        resp = client.get("/api/students/profile", headers=_auth("not-a-jwt"))
        assert resp.status_code == 401

    def test_signed_token_with_non_numeric_sub_returns_401(self, client, db):
        """A validly-signed token whose sub is not a numeric user id must be
        rejected with 401, never crash with a 500."""
        from app.core.security import create_access_token

        token = create_access_token("not-a-number")
        resp = client.get("/api/auth/me", headers=_auth(token))
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "UNAUTHORIZED"

    def test_token_without_exp_claim_rejected(self, client, db):
        """Tokens without an exp claim must not be accepted — they would
        otherwise remain valid forever."""
        from datetime import datetime, timezone

        from app.core.config import settings
        from jose import jwt

        token = jwt.encode(
            {"sub": "1", "iat": datetime.now(timezone.utc)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        resp = client.get("/api/auth/me", headers=_auth(token))
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "UNAUTHORIZED"

    def test_expired_token_rejected(self, client, db, monkeypatch):
        from app.core.config import settings
        from app.core.security import create_access_token

        monkeypatch.setattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", -5, raising=False)
        token = create_access_token("999")
        resp = client.get("/api/students/profile", headers=_auth(token))
        assert resp.status_code == 401
        assert "expired" in resp.json()["message"].lower() or resp.json()["error_code"] == "UNAUTHORIZED"

    def test_tampered_token_rejected(self, client, db):
        token = _register(client, "sec_tamper@example.com")[:-3] + "abc"
        resp = client.get("/api/students/profile", headers=_auth(token))
        assert resp.status_code == 401

    def test_deactivated_account_rejected(self, client, db):
        admin = _admin(client, db)
        token = _register(client, "sec_deact@example.com")

        users = client.get(
            "/api/admin/users?search=sec_deact@", headers=_auth(admin)
        ).json()["data"]["users"]
        uid = users[0]["id"]
        client.patch(f"/api/admin/users/{uid}/status?is_active=false", headers=_auth(admin))

        resp = client.get("/api/students/profile", headers=_auth(token))
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "UNAUTHORIZED"

    def test_reactivated_account_accepted(self, client, db):
        admin = _admin(client, db)
        token = _register(client, "sec_react@example.com")
        users = client.get(
            "/api/admin/users?search=sec_react@", headers=_auth(admin)
        ).json()["data"]["users"]
        uid = users[0]["id"]
        client.patch(f"/api/admin/users/{uid}/status?is_active=false", headers=_auth(admin))
        client.patch(f"/api/admin/users/{uid}/status?is_active=true", headers=_auth(admin))
        assert client.get("/api/students/profile", headers=_auth(token)).status_code == 200


class TestAuthorization:
    def test_student_cannot_access_teacher_routes(self, client, db):
        token = _register(client, "sec_stud@example.com")
        resp = client.get("/api/teachers/dashboard", headers=_auth(token))
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "FORBIDDEN"

    def test_student_cannot_access_admin_routes(self, client, db):
        token = _register(client, "sec_stud2@example.com")
        assert client.get("/api/admin/users", headers=_auth(token)).status_code == 403
        assert client.get("/api/admin/analytics", headers=_auth(token)).status_code == 403

    def test_teacher_cannot_access_admin_routes(self, client, db):
        token = _register(client, "sec_teach@example.com", role="teacher")
        assert client.get("/api/admin/users", headers=_auth(token)).status_code == 403
        assert client.post(
            "/api/admin/topics", headers=_auth(token), json={"name": "X", "category": "y"}
        ).status_code == 403

    def test_teacher_cannot_access_student_gamification(self, client, db):
        token = _register(client, "sec_teach2@example.com", role="teacher")
        assert client.get("/api/gamification/me", headers=_auth(token)).status_code == 403

    def test_admin_ping_rbac(self, client, db):
        admin = _admin(client, db)
        resp = client.get("/api/admin/ping", headers=_auth(admin))
        assert resp.status_code == 200


class TestValidationErrors:
    def test_empty_login_returns_422_envelope(self, client, db):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error_code"] == "VALIDATION_ERROR"
        # No stack trace leaked
        assert "traceback" not in str(body).lower()

    def test_wrong_type_returns_422(self, client, db):
        resp = client.post(
            "/api/students/practice/start",
            headers=_auth(_register(client, "sec_types@example.com")),
            json={"topic_id": "not-an-int"},
        )
        assert resp.status_code == 422

    def test_unknown_route_returns_envelope_404(self, client, db):
        resp = client.get("/api/does-not-exist")
        assert resp.status_code == 404
        assert resp.json()["success"] is False

    def test_no_raw_500_on_malformed_json(self, client, db):
        resp = client.post(
            "/api/auth/login",
            content="{bad json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        assert resp.json()["success"] is False


class TestSecretProtection:
    def test_gemini_key_never_in_responses(self, client, db, monkeypatch):
        from app.core.config import settings
        from app.services import ai as ai_mod

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "super-secret-key-123", raising=False)

        def _fake_generate(self, prompt: str) -> str:
            return "ok"

        monkeypatch.setattr(ai_mod.AIService, "_generate", _fake_generate)

        token = _register(client, "sec_leak@example.com")
        resp = client.post(
            "/api/ai/explain", headers=_auth(token), json={"question_text": "x"}
        )
        assert resp.status_code == 200
        assert "super-secret-key-123" not in resp.text

    def test_gemini_missing_key_clear_error(self, client, db, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "", raising=False)
        token = _register(client, "sec_nokey@example.com")
        resp = client.post(
            "/api/ai/explain", headers=_auth(token), json={"question_text": "x"}
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["error_code"] == "SERVICE_UNAVAILABLE"
        assert "not configured" in body["message"].lower()


class TestCors:
    def test_cors_origin_allowed(self, client):
        resp = client.options(
            "/api/topics",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert resp.status_code in (200, 400)
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_unknown_origin_not_allowed(self, client):
        resp = client.options(
            "/api/topics",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
        )
        assert resp.headers.get("access-control-allow-origin") is None
