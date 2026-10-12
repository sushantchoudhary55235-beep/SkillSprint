"""Phase 12 tests: Teacher Dashboard API.

Covers: student association by public Student ID, association validation,
dashboard aggregates, per-student performance view, access isolation
(unassociated students → 403), and soft removal.
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


def _register_teacher(client: TestClient, email: str) -> str:
    client.post("/api/auth/register/teacher",
                json={"name": "T" + email.split("@")[0], "email": email, "password": "password123"})
    return _login(client, email, "password123")


def _register_student(client: TestClient, email: str) -> str:
    client.post("/api/auth/register/student",
                json={"name": email.split("@")[0], "email": email, "password": "password123"})
    return _login(client, email, "password123")


def _student_code(client: TestClient, token: str) -> str:
    return client.get("/api/students/profile", headers=_auth(token)).json()["data"]["student_id"]


def _associate(client: TestClient, teacher_token: str, student_code: str) -> None:
    resp = client.post("/api/teachers/students",
                       json={"student_id": student_code}, headers=_auth(teacher_token))
    assert resp.status_code == 201, resp.text


class TestStudentAssociation:
    def test_add_student_by_id(self, client, db):
        t = _register_teacher(client, "t_assoc@example.com")
        s = _register_student(client, "s_assoc@example.com")
        code = _student_code(client, s)

        resp = client.post("/api/teachers/students", json={"student_id": code}, headers=_auth(t))
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "ACTIVE"

    def test_add_unknown_student_404(self, client, db):
        t = _register_teacher(client, "t_unknown@example.com")
        resp = client.post("/api/teachers/students",
                           json={"student_id": "SS000000000"}, headers=_auth(t))
        assert resp.status_code == 404

    def test_add_duplicate_409(self, client, db):
        t = _register_teacher(client, "t_dup@example.com")
        s = _register_student(client, "s_dup@example.com")
        _associate(client, t, _student_code(client, s))
        resp = client.post("/api/teachers/students",
                           json={"student_id": _student_code(client, s)}, headers=_auth(t))
        assert resp.status_code == 409

    def test_students_endpoint_requires_teacher(self, client, db):
        s = _register_student(client, "s_role@example.com")
        resp = client.get("/api/teachers/students", headers=_auth(s))
        assert resp.status_code == 403


class TestDashboardAndDetail:
    def test_dashboard_aggregates(self, client, db):
        t = _register_teacher(client, "t_dash@example.com")
        s1 = _register_student(client, "s_dash1@example.com")
        s2 = _register_student(client, "s_dash2@example.com")
        _associate(client, t, _student_code(client, s1))
        _associate(client, t, _student_code(client, s2))

        data = client.get("/api/teachers/dashboard", headers=_auth(t)).json()["data"]
        assert data["total_students"] == 2
        assert len(data["students"]) == 2

    def test_student_detail_for_associated(self, client, db):
        t = _register_teacher(client, "t_detail@example.com")
        s = _register_student(client, "s_detail@example.com")
        _associate(client, t, _student_code(client, s))

        listing = client.get("/api/teachers/students", headers=_auth(t)).json()["data"]
        spid = listing[0]["student_profile_id"]
        data = client.get(f"/api/teachers/students/{spid}", headers=_auth(t)).json()["data"]
        assert data["overall"] is not None
        assert "weak_topics" in data and "strong_topics" in data

    def test_unassociated_student_detail_403(self, client, db):
        t = _register_teacher(client, "t_iso@example.com")
        s = _register_student(client, "s_iso@example.com")

        # Any profile id — teacher has zero associations, so access must fail.
        resp = client.get("/api/teachers/students/1", headers=_auth(t))
        assert resp.status_code in (403, 404)

        _ = s  # student exists but is NOT associated

    def test_student_cannot_access_teacher_dashboard(self, client, db):
        s = _register_student(client, "s_nodash@example.com")
        resp = client.get("/api/teachers/dashboard", headers=_auth(s))
        assert resp.status_code == 403


class TestRemoval:
    def test_remove_student(self, client, db):
        t = _register_teacher(client, "t_rm@example.com")
        s = _register_student(client, "s_rm@example.com")
        _associate(client, t, _student_code(client, s))

        listing = client.get("/api/teachers/students", headers=_auth(t)).json()["data"]
        spid = listing[0]["student_profile_id"]

        resp = client.delete(f"/api/teachers/students/{spid}", headers=_auth(t))
        assert resp.status_code == 200

        # Removed → detail access revoked
        assert client.get(f"/api/teachers/students/{spid}", headers=_auth(t)).status_code in (403, 404)
        # and dashboard no longer counts them
        data = client.get("/api/teachers/dashboard", headers=_auth(t)).json()["data"]
        assert data["total_students"] == 0
