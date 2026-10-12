"""Phase 5 tests: Student Learning System.

Covers docs/Phases.md §9 completion criteria:
- Student dashboard works.
- Topics come from backend.
- Companies come from backend.
- Topic-wise and company-wise practice works.
- Difficulty filtering works.
- Questions fetched from real content.
- Answer evaluation is server-side.
- Attempts/answers recorded.
- Basic progress metrics work.
- Practice history works.
- Daily quiz foundation works.
- Student data isolation enforced.
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


# ---- helpers ----

def _register_student(client: TestClient, email: str = "s1@example.com") -> dict:
    resp = client.post(
        "/api/auth/register/student",
        json={"name": "Student One", "email": email, "password": "password123"},
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
    resp = client.post("/api/admin/topics", json={"name": name, "category": category}, headers=_auth(admin_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _create_company(client: TestClient, admin_token: str, name: str = "TCS") -> dict:
    resp = client.post("/api/admin/companies", json={"name": name}, headers=_auth(admin_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _create_question(client: TestClient, admin_token: str, topic_id: int, company_id: int | None = None,
                     difficulty: str = "easy", text: str = "What is 2+2?") -> dict:
    payload = {
        "question_text": text,
        "question_type": "MCQ",
        "topic_id": topic_id,
        "company_id": company_id,
        "difficulty": difficulty,
        "explanation": "Basic addition",
        "options": [
            {"option_text": "3", "option_order": 1, "is_correct": False},
            {"option_text": "4", "option_order": 2, "is_correct": True},
            {"option_text": "5", "option_order": 3, "is_correct": False},
            {"option_text": "6", "option_order": 4, "is_correct": False},
        ],
    }
    resp = client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _full_setup(client, db):
    """Set up admin, topic, company, 3 questions. Returns (student_token, admin_token, topic, company)."""
    _create_admin(client, db)
    admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
    topic = _create_topic(client, admin_token)
    company = _create_company(client, admin_token)
    _create_question(client, admin_token, topic["id"], company["id"], "easy", "Q1: What is 2+2?")
    _create_question(client, admin_token, topic["id"], company["id"], "easy", "Q2: What is 3+3?")
    _create_question(client, admin_token, topic["id"], company["id"], "medium", "Q3: What is 5x5?")

    _register_student(client)
    student_token = _login(client, "s1@example.com")
    return student_token, admin_token, topic, company


# ============================================================ DASHBOARD

class TestDashboard:
    def test_authenticated_student_can_access_dashboard(self, client, db):
        student_token, *_ = _full_setup(client, db)
        resp = client.get("/api/students/dashboard", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["student_id"].startswith("SS")
        assert data["name"] == "Student One"
        assert data["xp"] == 0
        assert data["total_questions_attempted"] == 0
        assert data["recent_sessions"] == []

    def test_unauthenticated_cannot_access_dashboard(self, client, db):
        resp = client.get("/api/students/dashboard")
        assert resp.status_code == 401

    def test_teacher_cannot_access_student_dashboard(self, client, db):
        from tests.test_content_api import _register_teacher
        _register_teacher(client)
        t_token = _login(client, "t@example.com")
        resp = client.get("/api/students/dashboard", headers=_auth(t_token))
        assert resp.status_code == 403

    def test_dashboard_shows_practice_progress(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        # Start and complete a session
        resp = client.post("/api/students/practice/start", json={"topic_id": topic["id"], "question_count": 3}, headers=_auth(student_token))
        session_id = resp.json()["data"]["session_id"]
        questions = resp.json()["data"]["questions"]
        # Answer all correctly
        for q in questions:
            correct_opt = next(o for o in q["options"] if o["id"])  # just pick first
            client.post(f"/api/students/practice/{session_id}/answer",
                       json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"], "time_taken_seconds": 10},
                       headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))

        # Check dashboard
        resp = client.get("/api/students/dashboard", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_questions_attempted"] == 3
        assert data["total_correct"] == 3
        assert data["overall_accuracy"] == 100.0
        assert len(data["recent_sessions"]) == 1


# ============================================================ TOPIC PRACTICE

class TestTopicPractice:
    def test_start_topic_practice_returns_questions(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 2},
            headers=_auth(student_token),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["session_id"] > 0
        assert data["mode"] == "TOPIC"
        assert len(data["questions"]) == 2
        # Questions should have options but NOT is_correct
        for q in data["questions"]:
            assert "is_correct" not in q["options"][0]

    def test_no_questions_returns_404(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        # Create a topic with no questions
        new_topic = _create_topic(client, admin_token, "Empty Topic", "verbal")
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": new_topic["id"], "question_count": 5},
            headers=_auth(student_token),
        )
        assert resp.status_code == 404

    def test_difficulty_filtering_works(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "difficulty": "hard", "question_count": 10},
            headers=_auth(student_token),
        )
        assert resp.status_code == 404  # no hard questions exist


# ============================================================ COMPANY PRACTICE

class TestCompanyPractice:
    def test_start_company_practice(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"company_id": company["id"], "question_count": 3},
            headers=_auth(student_token),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["mode"] == "COMPANY"
        assert len(data["questions"]) == 3

    def test_company_with_no_questions_returns_404(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        new_company = _create_company(client, admin_token, "EmptyCo")
        resp = client.post(
            "/api/students/practice/start",
            json={"company_id": new_company["id"], "question_count": 5},
            headers=_auth(student_token),
        )
        assert resp.status_code == 404


# ============================================================ ANSWER EVALUATION

class TestAnswerEvaluation:
    def test_correct_answer_evaluated_correctly(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]
        correct_opt = q["options"][1]  # option_order=2 is correct (is_correct=True)

        resp = client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": correct_opt["id"], "time_taken_seconds": 15},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_correct"] is True
        assert "explanation" in data

    def test_incorrect_answer_evaluated_correctly(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]
        wrong_opt = q["options"][0]  # option_order=1 is incorrect

        resp = client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": wrong_opt["id"], "time_taken_seconds": 10},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_correct"] is False

    def test_unanswered_question(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]

        resp = client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": None},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_correct"] is False

    def test_invalid_option_rejected(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]

        resp = client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": 99999},
            headers=_auth(student_token),
        )
        assert resp.status_code == 422

    def test_answer_recorded_in_session(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]

        client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"], "time_taken_seconds": 5},
            headers=_auth(student_token),
        )

        # Check DB directly
        from app.models.practice import PracticeAnswer
        answer = db.query(PracticeAnswer).filter_by(session_id=session_id).first()
        assert answer is not None
        assert answer.is_correct is True
        assert answer.time_taken_seconds == 5


# ============================================================ SESSION COMPLETION

class TestSessionCompletion:
    def test_complete_session_calculates_score(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 3},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        questions = resp.json()["data"]["questions"]

        # Answer 2 correct, 1 wrong
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": questions[0]["id"], "selected_option_id": questions[0]["options"][1]["id"], "time_taken_seconds": 10},
                    headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": questions[1]["id"], "selected_option_id": questions[1]["options"][1]["id"], "time_taken_seconds": 10},
                    headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": questions[2]["id"], "selected_option_id": questions[2]["options"][0]["id"], "time_taken_seconds": 10},
                    headers=_auth(student_token))

        resp = client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["correct"] == 2
        assert data["incorrect"] == 1
        assert data["score"] == 67  # 2/3 * 100 rounded
        assert data["accuracy"] == 66.67
        assert data["xp_earned"] > 0  # 2*5 + 25 = 35

    def test_xp_awarded_correctly(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"], "time_taken_seconds": 5},
                    headers=_auth(student_token))

        resp = client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))
        xp = resp.json()["data"]["xp_earned"]
        assert xp == 30  # 1*5 + 25 = 30

    def test_double_complete_rejected(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
                    headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))
        resp = client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))
        assert resp.status_code == 409

    def test_student_level_increases_with_xp(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        # Create many questions for more XP
        for i in range(30):
            _create_question(client, admin_token, topic["id"], company["id"], "easy", f"Q{i}")
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 25},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        questions = resp.json()["data"]["questions"]
        for q in questions:
            client.post(f"/api/students/practice/{session_id}/answer",
                       json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"], "time_taken_seconds": 5},
                       headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))

        # XP = 25*5 + 25 = 150 → level 2
        resp = client.get("/api/students/profile", headers=_auth(student_token))
        assert resp.json()["data"]["xp"] == 150
        assert resp.json()["data"]["level"] >= 2


# ============================================================ PRACTICE HISTORY

class TestPracticeHistory:
    def test_history_shows_sessions(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        # Create 3 sessions
        for _ in range(3):
            resp = client.post(
                "/api/students/practice/start",
                json={"topic_id": topic["id"], "question_count": 1},
                headers=_auth(student_token),
            )
            sid = resp.json()["data"]["session_id"]
            q = resp.json()["data"]["questions"][0]
            client.post(f"/api/students/practice/{sid}/answer",
                       json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
                       headers=_auth(student_token))
            client.post(f"/api/students/practice/{sid}/complete", headers=_auth(student_token))

        resp = client.get("/api/students/practice/history", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3
        assert len(data["sessions"]) == 3
        for s in data["sessions"]:
            assert s["status"] == "COMPLETED"
            assert s["correct_count"] == 1

    def test_history_pagination(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        for _ in range(5):
            resp = client.post(
                "/api/students/practice/start",
                json={"topic_id": topic["id"], "question_count": 1},
                headers=_auth(student_token),
            )
            sid = resp.json()["data"]["session_id"]
            client.post(f"/api/students/practice/{sid}/complete", headers=_auth(student_token))

        resp = client.get("/api/students/practice/history?page=1&limit=2", headers=_auth(student_token))
        data = resp.json()["data"]
        assert len(data["sessions"]) == 2
        assert data["total"] == 5


# ============================================================ PROGRESS

class TestProgress:
    def test_progress_tracks_correctness(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 3},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        questions = resp.json()["data"]["questions"]
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": questions[0]["id"], "selected_option_id": questions[0]["options"][1]["id"], "time_taken_seconds": 10},
                    headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/answer",
                    json={"question_id": questions[1]["id"], "selected_option_id": questions[1]["options"][0]["id"], "time_taken_seconds": 10},
                    headers=_auth(student_token))
        client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))

        resp = client.get("/api/students/progress", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_questions_attempted"] == 2
        assert data["total_correct"] == 1
        assert data["overall_accuracy"] == 50.0


# ============================================================ DAILY QUIZ

class TestDailyQuiz:
    def test_start_daily_quiz(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["mode"] == "DAILY_QUIZ"
        assert len(data["questions"]) == 3  # 3 questions available, picks all

    def test_daily_quiz_resume(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp1 = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        session_id_1 = resp1.json()["data"]["session_id"]
        resp2 = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        session_id_2 = resp2.json()["data"]["session_id"]
        assert session_id_1 == session_id_2  # same session resumed

    def test_daily_quiz_not_resumed_after_completion(self, client, db):
        """Audit fix H1: a COMPLETED daily quiz must not be handed back as a
        new session — the next start after completion creates a fresh one."""
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp1 = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        assert resp1.status_code == 201
        session_id = resp1.json()["data"]["session_id"]
        questions = resp1.json()["data"]["questions"]

        # Answer every question (correctness irrelevant here) and complete.
        for q in questions:
            ans = client.post(
                f"/api/students/practice/{session_id}/answer",
                json={"question_id": q["id"], "selected_option_id": q["options"][0]["id"]},
                headers=_auth(student_token),
            )
            assert ans.status_code == 200, ans.text
        comp = client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(student_token))
        assert comp.status_code == 200, comp.text

        resp2 = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        assert resp2.status_code == 201, resp2.text
        assert resp2.json()["data"]["session_id"] != session_id
        assert len(resp2.json()["data"]["questions"]) == len(questions)

    def test_daily_quiz_resume_before_any_answer(self, client, db):
        """Resuming before answering anything must still return a playable
        question set (same size), not an empty list."""
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp1 = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        assert resp1.status_code == 201
        session_id = resp1.json()["data"]["session_id"]
        count = len(resp1.json()["data"]["questions"])
        assert count > 0

        resp2 = client.post("/api/students/quiz/daily/start", headers=_auth(student_token))
        assert resp2.status_code == 201
        assert resp2.json()["data"]["session_id"] == session_id
        assert len(resp2.json()["data"]["questions"]) == count


# ============================================================ OWNERSHIP / ISOLATION

class TestOwnership:
    def test_student_cannot_answer_other_students_session(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)

        # Student 1 creates session
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]
        q = resp.json()["data"]["questions"][0]

        # Student 2 registers
        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        # Student 2 tries to answer Student 1's session
        resp = client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
            headers=_auth(s2_token),
        )
        assert resp.status_code == 422  # validation error (session ownership)

    def test_student_cannot_complete_other_students_session(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        session_id = resp.json()["data"]["session_id"]

        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        resp = client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(s2_token))
        assert resp.status_code == 422

    def test_student_only_sees_own_history(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        # Student 1 creates session
        resp = client.post(
            "/api/students/practice/start",
            json={"topic_id": topic["id"], "question_count": 1},
            headers=_auth(student_token),
        )
        sid = resp.json()["data"]["session_id"]
        client.post(f"/api/students/practice/{sid}/complete", headers=_auth(student_token))

        # Student 2 registers (no sessions)
        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        resp = client.get("/api/students/practice/history", headers=_auth(s2_token))
        assert resp.json()["data"]["total"] == 0

    def test_student_only_sees_own_progress(self, client, db):
        student_token, admin_token, topic, company = _full_setup(client, db)
        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        resp = client.get("/api/students/progress", headers=_auth(s2_token))
        data = resp.json()["data"]
        assert data["total_questions_attempted"] == 0
