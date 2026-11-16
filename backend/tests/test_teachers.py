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


class TestRoleBootstrapDEMO:
    """Demo bootstrap: teacher + seeded students share the EmailStr-accepted
    demo domain. A fresh development DB boots all three roles, the teacher
    sees exactly its associated students, and every non-teacher route stays
    blocked.
    """

    @pytest.fixture(autouse=True)
    def _demo_teachers(self, client, db):
        from app.core.security import hash_password
        from app.models.content import TeacherStudent
        from app.models.profile import TeacherProfile
        from app.models.user import User

        teacher = User(
            name="Demo Teacher",
            email="demo.teacher@demo.skillsprint.dev",
            password_hash=hash_password("Demo#Pass123"),
            role="teacher",
        )
        db.add(teacher)
        db.flush()
        tprof = TeacherProfile(department="Demo Department")
        teacher.teacher_profile = tprof
        db.commit()
        self.demo_teacher = teacher
        self.demo_profile = tprof

        for i, name in enumerate(["Demo Aarav", "Demo Meera", "Demo Rohan"], start=1):
            user = User(
                name=name,
                email=f"demo.{name.split()[-1].lower()}@demo.skillsprint.dev",
                password_hash=hash_password("Demo#Pass123"),
                role="student",
            )
            db.add(user)
            db.flush()
            from app.models.profile import StudentProfile as SP
            sp = SP(
                student_id=f"SSDEMO{i:04d}",
                readiness_score=0,
                xp=0,
                level=1,
                current_streak=0,
                longest_streak=0,
            )
            user.student_profile = sp
            db.flush()

        t = self.demo_teacher
        for i in range(1, 4):
            sp = db.query(SP).filter_by(student_id=f"SSDEMO{i:04d}").first()
            if db.query(TeacherStudent).filter_by(teacher_id=t.id, student_id=sp.id).first() is None:
                db.add(TeacherStudent(teacher_id=t.id, student_id=sp.id, status="ACTIVE"))
        db.commit()

    def test_demo_teacher_login(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "demo.teacher@demo.skillsprint.dev", "password": "Demo#Pass123"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["user"]["role"] == "teacher"

    def test_demo_teacher_sees_only_associated_students(self, client):
        token = client.post(
            "/api/auth/login",
            json={"email": "demo.teacher@demo.skillsprint.dev", "password": "Demo#Pass123"},
        ).json()["data"]["access_token"]
        resp = client.get("/api/teachers/dashboard",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_students"] == 3

    def test_demo_student_login_with_documented_password(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "demo.aarav@demo.skillsprint.dev", "password": "Demo#Pass123"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["user"]["role"] == "student"

    def test_demo_student_profile_accessible_to_student_only(self, client, db):
        token = client.post(
            "/api/auth/login",
            json={"email": "demo.teacher@demo.skillsprint.dev", "password": "Demo#Pass123"},
        ).json()["data"]["access_token"]
        resp = client.get("/api/students/profile",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_demo_student_login_blocked_for_teacher(self, client):
        token = client.post(
            "/api/auth/login",
            json={"email": "demo.teacher@demo.skillsprint.dev", "password": "Demo#Pass123"},
        ).json()["data"]["access_token"]
        resp = client.get("/api/students/profile",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_demo_teacher_has_no_admin_access(self, client):
        token = client.post(
            "/api/auth/login",
            json={"email": "demo.teacher@demo.skillsprint.dev", "password": "Demo#Pass123"},
        ).json()["data"]["access_token"]
        resp = client.get("/api/admin/ping",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_demo_student_login_blocked_for_teacher_with_student_route(self, client):
        token = client.post(
            "/api/auth/login",
            json={"email": "demo.teacher@demo.skillsprint.dev", "password": "Demo#Pass123"},
        ).json()["data"]["access_token"]
        resp = client.get("/api/students/dashboard",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
