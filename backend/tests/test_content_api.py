"""Phase 4 tests: question CRUD, teacher submission, admin approval, public retrieval.

Covers docs/Phases.md §8 completion criteria:
- Questions can be created, categorized, topics/companies/difficulty assigned.
- Teachers can submit questions (PENDING).
- Admin can approve/reject questions.
- Students can retrieve approved questions.
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


# ---- helpers ----

def _register_student(client: TestClient, email: str = "s@example.com") -> dict:
    resp = client.post(
        "/api/auth/register/student",
        json={"name": "Student One", "email": email, "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _register_teacher(client: TestClient, email: str = "t@example.com") -> dict:
    resp = client.post(
        "/api/auth/register/teacher",
        json={"name": "Teacher One", "email": email, "password": "password123", "department": "CSE"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_admin(client: TestClient, db, email: str = "admin@skillsprint.com"):
    from app.core.security import hash_password
    from app.models.user import User

    user = User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, email: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_topic(client: TestClient, admin_token: str, name: str = "Percentages", category: str = "quantitative") -> dict:
    resp = client.post(
        "/api/admin/topics",
        json={"name": name, "category": category},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _create_company(client: TestClient, admin_token: str, name: str = "TCS") -> dict:
    resp = client.post(
        "/api/admin/companies",
        json={"name": name},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _question_payload(topic_id: int, company_id: int | None = None) -> dict:
    return {
        "question_text": "What is 20% of 500?",
        "question_type": "MCQ",
        "topic_id": topic_id,
        "company_id": company_id,
        "difficulty": "easy",
        "explanation": "20% of 500 = 100",
        "options": [
            {"option_text": "80", "option_order": 1, "is_correct": False},
            {"option_text": "100", "option_order": 2, "is_correct": True},
            {"option_text": "120", "option_order": 3, "is_correct": False},
            {"option_text": "150", "option_order": 4, "is_correct": False},
        ],
    }


# =============================================================== ADMIN TOPICS
class TestAdminTopics:
    def test_admin_can_create_topic(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, token)
        assert topic["name"] == "Percentages"
        assert topic["category"] == "quantitative"

    def test_non_admin_cannot_create_topic(self, client, db):
        _register_student(client)
        token = _login(client, "s@example.com")
        resp = client.post(
            "/api/admin/topics",
            json={"name": "Foo", "category": "bar"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_admin_can_list_topics(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        _create_topic(client, token, "Probability", "quantitative")
        _create_topic(client, token, "Puzzles", "logical")
        resp = client.get("/api/admin/topics", headers=_auth(token))
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_duplicate_topic_conflicts(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        _create_topic(client, token)
        resp = client.post(
            "/api/admin/topics",
            json={"name": "Percentages", "category": "quantitative"},
            headers=_auth(token),
        )
        assert resp.status_code == 409


# ============================================================= ADMIN COMPANIES
class TestAdminCompanies:
    def test_admin_can_create_company(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        company = _create_company(client, token)
        assert company["name"] == "TCS"

    def test_non_admin_cannot_create_company(self, client, db):
        _register_student(client)
        token = _login(client, "s@example.com")
        resp = client.post(
            "/api/admin/companies",
            json={"name": "Infosys"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_admin_can_list_companies(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        _create_company(client, token, "TCS")
        _create_company(client, token, "Infosys")
        resp = client.get("/api/admin/companies", headers=_auth(token))
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


# ============================================================= ADMIN QUESTIONS
class TestAdminQuestions:
    def _setup(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, token)
        company = _create_company(client, token)
        return token, topic, company

    def test_admin_creates_approved_question(self, client, db):
        token, topic, company = self._setup(client, db)
        payload = _question_payload(topic["id"], company["id"])
        resp = client.post("/api/admin/questions", json=payload, headers=_auth(token))
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "approved"
        assert data["topic_id"] == topic["id"]
        assert data["difficulty"] == "easy"
        assert len(data["options"]) == 4

    def test_admin_lists_questions(self, client, db):
        token, topic, company = self._setup(client, db)
        client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        resp = client.get("/api/admin/questions", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 2

    def test_admin_gets_single_question(self, client, db):
        token, topic, company = self._setup(client, db)
        create_resp = client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        q_id = create_resp.json()["data"]["id"]
        resp = client.get(f"/api/admin/questions/{q_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == q_id

    def test_admin_updates_question(self, client, db):
        token, topic, company = self._setup(client, db)
        create_resp = client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        q_id = create_resp.json()["data"]["id"]
        resp = client.patch(
            f"/api/admin/questions/{q_id}",
            json={"difficulty": "hard", "explanation": "Updated explanation"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["difficulty"] == "hard"
        assert resp.json()["data"]["explanation"] == "Updated explanation"

    def test_admin_updates_question_status(self, client, db):
        token, topic, company = self._setup(client, db)
        create_resp = client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        q_id = create_resp.json()["data"]["id"]
        resp = client.patch(
            f"/api/admin/questions/{q_id}/status",
            json={"status": "archived"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "archived"

    def test_admin_deletes_question(self, client, db):
        token, topic, company = self._setup(client, db)
        create_resp = client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        q_id = create_resp.json()["data"]["id"]
        resp = client.delete(f"/api/admin/questions/{q_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # confirm gone
        resp = client.get(f"/api/admin/questions/{q_id}", headers=_auth(token))
        assert resp.status_code == 404

    def test_non_admin_cannot_create_question(self, client, db):
        admin = _create_admin(client, db)
        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, admin_token)

        _register_student(client)
        student_token = _login(client, "s@example.com")
        resp = client.post(
            "/api/admin/questions",
            json=_question_payload(topic["id"]),
            headers=_auth(student_token),
        )
        assert resp.status_code == 403

    def test_invalid_topic_rejected(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        resp = client.post(
            "/api/admin/questions",
            json=_question_payload(topic_id=9999),
            headers=_auth(token),
        )
        assert resp.status_code == 404

    def test_pagination_works(self, client, db):
        token, topic, company = self._setup(client, db)
        for _ in range(5):
            client.post("/api/admin/questions", json=_question_payload(topic["id"]), headers=_auth(token))
        resp = client.get("/api/admin/questions?limit=2&page=1", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["questions"]) == 2
        assert data["total"] == 5

    def test_filter_by_difficulty(self, client, db):
        token, topic, company = self._setup(client, db)
        easy = _question_payload(topic["id"])
        client.post("/api/admin/questions", json=easy, headers=_auth(token))
        hard = _question_payload(topic["id"])
        hard["difficulty"] = "hard"
        client.post("/api/admin/questions", json=hard, headers=_auth(token))
        resp = client.get("/api/admin/questions?difficulty=hard", headers=_auth(token))
        assert resp.json()["data"]["total"] == 1
        assert resp.json()["data"]["questions"][0]["difficulty"] == "hard"


# ========================================================== TEACHER QUESTIONS
class TestTeacherQuestions:
    def _setup(self, client, db):
        admin = _create_admin(client, db)
        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, admin_token)
        company = _create_company(client, admin_token)

        _register_teacher(client)
        teacher_token = _login(client, "t@example.com")
        return teacher_token, topic, company

    def test_teacher_submits_question_pending(self, client, db):
        teacher_token, topic, company = self._setup(client, db)
        payload = _question_payload(topic["id"], company["id"])
        resp = client.post("/api/teachers/questions", json=payload, headers=_auth(teacher_token))
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "pending"
        assert data["source_type"] == "TEACHER"
        assert data["created_by"] is not None

    def test_student_cannot_submit_question(self, client, db):
        admin = _create_admin(client, db)
        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, admin_token)

        _register_student(client)
        student_token = _login(client, "s@example.com")
        resp = client.post(
            "/api/teachers/questions",
            json=_question_payload(topic["id"]),
            headers=_auth(student_token),
        )
        assert resp.status_code == 403

    def test_admin_can_approve_teacher_question(self, client, db):
        teacher_token, topic, company = self._setup(client, db)
        resp = client.post(
            "/api/teachers/questions",
            json=_question_payload(topic["id"]),
            headers=_auth(teacher_token),
        )
        q_id = resp.json()["data"]["id"]

        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        resp = client.patch(
            f"/api/admin/questions/{q_id}/status",
            json={"status": "approved"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"

    def test_admin_can_reject_teacher_question(self, client, db):
        teacher_token, topic, company = self._setup(client, db)
        resp = client.post(
            "/api/teachers/questions",
            json=_question_payload(topic["id"]),
            headers=_auth(teacher_token),
        )
        q_id = resp.json()["data"]["id"]

        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        resp = client.patch(
            f"/api/admin/questions/{q_id}/status",
            json={"status": "rejected"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "rejected"


# ====================================================== PUBLIC QUESTION READ
class TestPublicQuestions:
    def _setup(self, client, db):
        admin = _create_admin(client, db)
        token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, token)
        company = _create_company(client, token)
        # Create an approved question
        resp = client.post(
            "/api/admin/questions",
            json=_question_payload(topic["id"], company["id"]),
            headers=_auth(token),
        )
        approved_id = resp.json()["data"]["id"]
        # Create a pending question (teacher-submitted)
        _register_teacher(client, "teacher2@example.com")
        t_token = _login(client, "teacher2@example.com")
        client.post(
            "/api/teachers/questions",
            json=_question_payload(topic["id"]),
            headers=_auth(t_token),
        )
        return approved_id, topic, company

    def test_students_list_approved_questions(self, client, db):
        approved_id, topic, company = self._setup(client, db)
        _register_student(client)
        s_token = _login(client, "s@example.com")
        resp = client.get("/api/questions", headers=_auth(s_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1  # only approved
        assert data["questions"][0]["id"] == approved_id

    def test_students_get_single_approved_question(self, client, db):
        approved_id, topic, company = self._setup(client, db)
        _register_student(client)
        s_token = _login(client, "s@example.com")
        resp = client.get(f"/api/questions/{approved_id}", headers=_auth(s_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == approved_id
        # options should NOT include is_correct
        for opt in resp.json()["data"]["options"]:
            assert "is_correct" not in opt

    def test_students_cannot_see_pending_question(self, client, db):
        _, topic, company = self._setup(client, db)
        _register_student(client)
        s_token = _login(client, "s@example.com")
        resp = client.get("/api/questions", headers=_auth(s_token))
        assert resp.json()["data"]["total"] == 1  # pending excluded

    def test_filter_by_topic(self, client, db):
        admin = _create_admin(client, db)
        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        t1 = _create_topic(client, admin_token, "Probability", "quantitative")
        t2 = _create_topic(client, admin_token, "Puzzles", "logical")
        client.post("/api/admin/questions", json=_question_payload(t1["id"]), headers=_auth(admin_token))
        client.post("/api/admin/questions", json=_question_payload(t2["id"]), headers=_auth(admin_token))

        _register_student(client)
        s_token = _login(client, "s@example.com")
        resp = client.get(f"/api/questions?topic_id={t1['id']}", headers=_auth(s_token))
        assert resp.json()["data"]["total"] == 1

    def test_unauthenticated_can_list_approved(self, client, db):
        approved_id, topic, company = self._setup(client, db)
        resp = client.get("/api/questions")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1
