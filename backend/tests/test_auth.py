"""Phase 3 tests: authentication and RBAC (docs/Phases.md §7 completion criteria).

Covers:
- All three roles can authenticate
- Invalid credentials rejected
- Protected APIs reject unauthenticated requests
- Students/teachers cannot access admin APIs (backend-enforced RBAC)
- Student IDs are unique
- Passwords never stored as plain text
- Token tampering / malformed auth headers rejected
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.profile import StudentProfile
from app.models.user import User

pytestmark = pytest.mark.usefixtures("db")


def _register_student(client: TestClient, email: str = "rahul@example.com", password: str = "password123") -> dict:
    resp = client.post(
        "/api/auth/register/student",
        json={"name": "Rahul Sharma", "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register_teacher(client: TestClient, email: str = "teacher@example.com") -> dict:
    resp = client.post(
        "/api/auth/register/teacher",
        json={"name": "Professor Sharma", "email": email, "password": "password123", "department": "CSE"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register_admin(client: TestClient, db, email: str = "admin@skillsprint.com") -> User:
    """Admins are platform-managed: seeded directly (no public registration)."""
    from app.core.security import hash_password

    user = User(name="Platform Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, email: str, password: str = "password123") -> tuple[int, dict]:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return resp.status_code, resp.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- registration
def test_student_registration_generates_unique_student_id(client: TestClient) -> None:
    body = _register_student(client)
    data = body["data"]
    assert body["success"] is True
    assert data["student_id"].startswith("SS")
    assert data["role"] == "student"


def test_student_ids_are_unique_across_registrations(client: TestClient) -> None:
    first = _register_student(client, email="a@example.com")["data"]["student_id"]
    second = _register_student(client, email="b@example.com")["data"]["student_id"]
    assert first != second


def test_duplicate_email_registration_conflicts(client: TestClient) -> None:
    _register_student(client)
    resp = client.post(
        "/api/auth/register/student",
        json={"name": "Other Rahul", "email": "rahul@example.com", "password": "password123"},
    )
    assert resp.status_code == 409
    assert resp.json()["success"] is False


def test_short_password_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register/student",
        json={"name": "Weak PW", "email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_password_never_stored_plain_text(client: TestClient, db) -> None:
    _register_student(client)
    user = db.scalar(select(User).where(User.email == "rahul@example.com"))
    assert user is not None
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")  # bcrypt


def test_teacher_registration_with_duplicate_employee_id_conflicts(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register/teacher",
        json={"name": "T1", "email": "t1@example.com", "password": "password123", "employee_id": "EMP-1"},
    )
    assert resp.status_code == 201
    resp = client.post(
        "/api/auth/register/teacher",
        json={"name": "T2", "email": "t2@example.com", "password": "password123", "employee_id": "EMP-1"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------- login
def test_student_login_returns_token(client: TestClient) -> None:
    _register_student(client)
    status, body = _login(client, "rahul@example.com")
    assert status == 200
    assert body["success"] is True
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["user"]["role"] == "student"


def test_wrong_password_rejected(client: TestClient) -> None:
    _register_student(client)
    status, body = _login(client, "rahul@example.com", "wrongpassword")
    assert status == 401
    assert body["success"] is False


def test_unknown_email_rejected(client: TestClient) -> None:
    status, body = _login(client, "ghost@example.com")
    assert status == 401
    assert body["success"] is False


def test_all_roles_can_authenticate(client: TestClient, db) -> None:
    _register_student(client)
    _register_teacher(client)
    _register_admin(client, db)
    for email, password, expected_role in (
        ("rahul@example.com", "password123", "student"),
        ("teacher@example.com", "password123", "teacher"),
        ("admin@skillsprint.com", "adminpass123", "admin"),
    ):
        status, body = _login(client, email, password)
        assert status == 200
        assert body["data"]["user"]["role"] == expected_role


# -------------------------------------------------------------------- /me
def test_me_returns_profile_identifiers(client: TestClient) -> None:
    student_id = _register_student(client)["data"]["student_id"]
    _, body = _login(client, "rahul@example.com")
    token = body["data"]["access_token"]

    resp = client.get("/api/auth/me", headers=_auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["role"] == "student"
    assert data["student_id"] == student_id


def test_me_requires_authentication(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_tampered_token_rejected(client: TestClient) -> None:
    _register_student(client)
    _, body = _login(client, "rahul@example.com")
    token = body["data"]["access_token"]

    resp = client.get("/api/auth/me", headers=_auth_header(token[:-3] + "abc"))
    assert resp.status_code == 401


def test_malformed_authorization_header_rejected(client: TestClient) -> None:
    resp = client.get("/api/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401


def test_logout_requires_authentication(client: TestClient) -> None:
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401
    _register_student(client)
    _, body = _login(client, "rahul@example.com")
    resp = client.post("/api/auth/logout", headers=_auth_header(body["data"]["access_token"]))
    assert resp.status_code == 200


# ---------------------------------------------------------------- RBAC guards
def test_student_profile_accessible_to_student_only(client: TestClient, db) -> None:
    _register_student(client)
    _register_teacher(client)
    _register_admin(client, db)

    _, student = _login(client, "rahul@example.com")
    _, teacher = _login(client, "teacher@example.com")
    _, admin = _login(client, "admin@skillsprint.com", "adminpass123")

    ok = client.get("/api/students/profile", headers=_auth_header(student["data"]["access_token"]))
    assert ok.status_code == 200
    assert ok.json()["data"]["xp"] == 0

    for token in (teacher["data"]["access_token"], admin["data"]["access_token"]):
        denied = client.get("/api/students/profile", headers=_auth_header(token))
        assert denied.status_code == 403


def test_admin_api_rejects_students_and_teachers(client: TestClient, db) -> None:
    _register_student(client)
    _register_teacher(client)
    _register_admin(client, db)

    _, student = _login(client, "rahul@example.com")
    _, teacher = _login(client, "teacher@example.com")
    _, admin = _login(client, "admin@skillsprint.com", "adminpass123")

    ok = client.get("/api/admin/ping", headers=_auth_header(admin["data"]["access_token"]))
    assert ok.status_code == 200

    for token in (student["data"]["access_token"], teacher["data"]["access_token"]):
        denied = client.get("/api/admin/ping", headers=_auth_header(token))
        assert denied.status_code == 403


def test_protected_apis_reject_unauthenticated_requests(client: TestClient) -> None:
    for path in ("/api/students/profile", "/api/admin/ping", "/api/auth/me"):
        resp = client.get(path)
        assert resp.status_code == 401, path


def test_student_id_persisted_on_profile(client: TestClient, db) -> None:
    student_id = _register_student(client)["data"]["student_id"]
    profile = db.scalar(select(StudentProfile))
    assert profile is not None
    assert profile.student_id == student_id
    assert profile.xp == 0
    assert profile.level == 1
