"""Phase 6 tests: Assessment & Testing System.

Covers docs/Phases.md §11 completion criteria:
- Assessments can be created.
- Students can start assessments.
- Answers are recorded.
- Submission works.
- Scores are calculated.
- Results are stored.
- Assessment history works.
- Timer enforcement.
- Ownership/isolation.
"""
from datetime import datetime, timedelta, timezone

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


def _create_question(client: TestClient, admin_token: str, topic_id: int, text: str = "Q1", difficulty: str = "easy") -> dict:
    payload = {
        "question_text": text,
        "question_type": "MCQ",
        "topic_id": topic_id,
        "difficulty": difficulty,
        "explanation": "Explanation",
        "options": [
            {"option_text": "A", "option_order": 1, "is_correct": False},
            {"option_text": "B", "option_order": 2, "is_correct": True},
            {"option_text": "C", "option_order": 3, "is_correct": False},
            {"option_text": "D", "option_order": 4, "is_correct": False},
        ],
    }
    resp = client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _create_assessment(client: TestClient, admin_token: str, question_ids: list[int],
                       title: str = "Mock Test 1", duration: int = 30) -> dict:
    resp = client.post(
        "/api/admin/assessments",
        json={"title": title, "assessment_type": "MOCK_TEST", "duration_minutes": duration, "question_ids": question_ids},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _full_setup(client, db, num_questions: int = 5):
    """Setup admin, topics, questions, assessment. Returns (student_token, admin_token, assessment)."""
    _create_admin(client, db)
    admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
    topic = _create_topic(client, admin_token)
    questions = [_create_question(client, admin_token, topic["id"], f"Question {i}") for i in range(num_questions)]
    assessment = _create_assessment(client, admin_token, [q["id"] for q in questions])
    _register_student(client)
    student_token = _login(client, "s1@example.com")
    return student_token, admin_token, assessment, questions


# ============================================================ ADMIN ASSESSMENT CRUD

class TestAdminAssessmentCRUD:
    def test_admin_creates_assessment(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        assert assessment["title"] == "Mock Test 1"
        assert assessment["question_count"] == 5
        assert assessment["is_active"] is True

    def test_admin_lists_assessments(self, client, db):
        student_token, admin_token, _, _ = _full_setup(client, db)
        resp = client.get("/api/admin/assessments", headers=_auth(admin_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1

    def test_admin_gets_assessment_detail(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        resp = client.get(f"/api/admin/assessments/{assessment['id']}", headers=_auth(admin_token))
        assert resp.status_code == 200
        assert len(resp.json()["data"]["question_ids"]) == 5

    def test_admin_updates_assessment(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        resp = client.patch(
            f"/api/admin/assessments/{assessment['id']}",
            json={"title": "Updated Title", "duration_minutes": 45},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated Title"

    def test_non_admin_cannot_create_assessment(self, client, db):
        student_token, admin_token, _, questions = _full_setup(client, db)
        resp = client.post(
            "/api/admin/assessments",
            json={"title": "X", "question_ids": [q["id"] for q in questions]},
            headers=_auth(student_token),
        )
        assert resp.status_code == 403

    def test_invalid_question_rejected(self, client, db):
        _create_admin(client, db)
        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        resp = client.post(
            "/api/admin/assessments",
            json={"title": "Bad", "question_ids": [99999]},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 404


# ============================================================ STUDENT LIST

class TestStudentAssessmentList:
    def test_students_see_active_assessments(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        resp = client.get("/api/assessments", headers=_auth(student_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1

    def test_inactive_assessments_hidden(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        # Deactivate
        client.patch(f"/api/admin/assessments/{assessment['id']}", json={"is_active": False}, headers=_auth(admin_token))
        resp = client.get("/api/assessments", headers=_auth(student_token))
        assert resp.json()["data"]["total"] == 0

    def test_unauthenticated_can_list(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        resp = client.get("/api/assessments")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1


# ============================================================ ATTEMPT START

class TestAttemptStart:
    def test_student_starts_assessment(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["attempt_id"] > 0
        assert data["assessment_id"] == assessment["id"]
        assert data["duration_minutes"] == 30
        assert len(data["questions"]) == 5
        # Questions should NOT include is_correct
        for q in data["questions"]:
            assert "is_correct" not in q["options"][0]

    def test_cannot_start_inactive_assessment(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        client.patch(f"/api/admin/assessments/{assessment['id']}", json={"is_active": False}, headers=_auth(admin_token))
        resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        assert resp.status_code == 404

    def test_double_start_rejected(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        assert resp.status_code == 409


# ============================================================ ANSWER SUBMISSION

class TestAnswerSubmission:
    def test_valid_answer_accepted(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        q = start_resp.json()["data"]["questions"][0]

        resp = client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"], "time_taken_seconds": 10},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_correct"] is True
        assert data["correct_option_id"] == q["options"][1]["id"]

    def test_invalid_question_rejected(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]

        resp = client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": 99999, "selected_option_id": 1},
            headers=_auth(student_token),
        )
        assert resp.status_code == 422

    def test_question_outside_assessment_rejected(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        # Create a question NOT in the assessment
        topic = _create_topic(client, admin_token, "Extra Topic", "verbal")
        extra_q = _create_question(client, admin_token, topic["id"], "Extra Q")

        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]

        resp = client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": extra_q["id"], "selected_option_id": extra_q["options"][1]["id"]},
            headers=_auth(student_token),
        )
        assert resp.status_code == 422

    def test_answer_recorded_in_db(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        q = start_resp.json()["data"]["questions"][0]

        client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"], "time_taken_seconds": 5},
            headers=_auth(student_token),
        )

        from app.models.assessment import Answer
        answer = db.query(Answer).filter_by(attempt_id=attempt_id, question_id=q["id"]).first()
        assert answer is not None
        assert answer.is_correct is True
        assert answer.time_taken_seconds == 5

    def test_answer_update_overwrites(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        q = start_resp.json()["data"]["questions"][0]

        # First answer: wrong
        client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][0]["id"]},
            headers=_auth(student_token),
        )
        # Second answer: correct (update)
        resp = client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
            headers=_auth(student_token),
        )
        assert resp.json()["data"]["is_correct"] is True


# ============================================================ TIMER

class TestTimer:
    def test_expired_attempt_rejects_answers(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        q = start_resp.json()["data"]["questions"][0]

        # Simulate time passing beyond duration
        from app.models.assessment import Attempt
        attempt = db.get(Attempt, attempt_id)
        attempt.started_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.commit()

        resp = client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
            headers=_auth(student_token),
        )
        assert resp.status_code == 409


# ============================================================ SUBMISSION & SCORING

class TestSubmission:
    def test_submit_calculates_score_correctly(self, client, db):
        student_token, admin_token, assessment, questions = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        qs = start_resp.json()["data"]["questions"]

        # Answer 3 correct, 2 wrong
        for i, q in enumerate(qs):
            if i < 3:
                opt = q["options"][1]  # correct
            else:
                opt = q["options"][0]  # wrong
            client.post(
                f"/api/attempts/{attempt_id}/answer",
                json={"question_id": q["id"], "selected_option_id": opt["id"], "time_taken_seconds": 10},
                headers=_auth(student_token),
            )

        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["correct"] == 3
        assert data["incorrect"] == 2
        assert data["score"] == 60.0  # 3/5 * 100
        assert data["accuracy"] == 60.0
        assert data["total_questions"] == 5

    def test_unattempted_counted(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        qs = start_resp.json()["data"]["questions"]

        # Answer only 1 question
        client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": qs[0]["id"], "selected_option_id": qs[0]["options"][1]["id"]},
            headers=_auth(student_token),
        )

        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        data = resp.json()["data"]
        assert data["correct"] == 1
        assert data["unattempted"] == 4

    def test_duplicate_submission_rejected(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        assert resp.status_code == 409

    def test_submit_expired_attempt_rejected(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]

        from app.models.assessment import Attempt
        attempt = db.get(Attempt, attempt_id)
        attempt.started_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.commit()

        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        assert resp.status_code == 409

    def test_topic_performance_calculated(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db, num_questions=3)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        qs = start_resp.json()["data"]["questions"]

        # Answer all correctly
        for q in qs:
            client.post(
                f"/api/attempts/{attempt_id}/answer",
                json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
                headers=_auth(student_token),
            )

        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        tp = resp.json()["data"]["topic_performance"]
        assert len(tp) > 0
        assert tp[0]["accuracy"] == 100.0


# ============================================================ RESULT

class TestResult:
    def test_get_result_after_submission(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db, num_questions=3)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        qs = start_resp.json()["data"]["questions"]

        for q in qs:
            client.post(
                f"/api/attempts/{attempt_id}/answer",
                json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
                headers=_auth(student_token),
            )
        client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))

        resp = client.get(f"/api/attempts/{attempt_id}/result", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "SUBMITTED"
        assert data["score"] == 100.0
        assert data["assessment_title"] == "Mock Test 1"
        assert data["submitted_at"] is not None

    def test_get_result_during_attempt(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]

        resp = client.get(f"/api/attempts/{attempt_id}/result", headers=_auth(student_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "IN_PROGRESS"


# ============================================================ HISTORY

class TestAttemptHistory:
    def test_history_shows_attempts(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))

        resp = client.get("/api/students/me/attempts", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["assessment_title"] == "Mock Test 1"
        assert data[0]["status"] == "SUBMITTED"


# ============================================================ OWNERSHIP / SECURITY

class TestOwnership:
    def test_student_cannot_answer_others_attempt(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        q = start_resp.json()["data"]["questions"][0]

        # Student 2
        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        resp = client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1]["id"]},
            headers=_auth(s2_token),
        )
        assert resp.status_code == 403

    def test_student_cannot_submit_others_attempt(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]

        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(s2_token))
        assert resp.status_code == 403

    def test_student_cannot_see_others_result(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]

        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")

        resp = client.get(f"/api/attempts/{attempt_id}/result", headers=_auth(s2_token))
        assert resp.status_code == 403

    def test_student_only_sees_own_history(self, client, db):
        student_token, admin_token, assessment, _ = _full_setup(client, db)
        start_resp = client.post(f"/api/assessments/{assessment['id']}/start", headers=_auth(student_token))
        attempt_id = start_resp.json()["data"]["attempt_id"]
        client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))

        _register_student(client, "s2@example.com")
        s2_token = _login(client, "s2@example.com")
        resp = client.get("/api/students/me/attempts", headers=_auth(s2_token))
        assert len(resp.json()["data"]) == 0


# ============================================================ END-TO-END

class TestEndToEnd:
    def test_full_assessment_flow(self, client, db):
        """Complete end-to-end: create → start → answer → submit → result."""
        # 1. Setup
        _create_admin(client, db)
        admin_token = _login(client, "admin@skillsprint.com", "adminpass123")
        topic = _create_topic(client, admin_token, "Percentages", "quantitative")
        questions = []
        for i in range(3):
            q = _create_question(client, admin_token, topic["id"], f"E2E Q{i+1}")
            questions.append(q)

        # 2. Admin creates assessment
        assessment_resp = client.post(
            "/api/admin/assessments",
            json={"title": "E2E Test", "assessment_type": "MOCK_TEST", "duration_minutes": 30,
                  "question_ids": [q["id"] for q in questions]},
            headers=_auth(admin_token),
        )
        assessment_id = assessment_resp.json()["data"]["id"]

        # 3. Student registers and logs in
        _register_student(client, "e2e@example.com")
        student_token = _login(client, "e2e@example.com")

        # 4. Student sees assessment
        list_resp = client.get("/api/assessments", headers=_auth(student_token))
        assert list_resp.json()["data"]["total"] == 1

        # 5. Student starts assessment
        start_resp = client.post(f"/api/assessments/{assessment_id}/start", headers=_auth(student_token))
        assert start_resp.status_code == 201
        attempt_id = start_resp.json()["data"]["attempt_id"]
        qs = start_resp.json()["data"]["questions"]

        # 6. Student answers questions (2 correct, 1 wrong)
        for i, q in enumerate(qs):
            opt = q["options"][1] if i < 2 else q["options"][0]
            client.post(
                f"/api/attempts/{attempt_id}/answer",
                json={"question_id": q["id"], "selected_option_id": opt["id"], "time_taken_seconds": 15},
                headers=_auth(student_token),
            )

        # 7. Student submits
        submit_resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(student_token))
        assert submit_resp.status_code == 200
        result = submit_resp.json()["data"]
        assert result["correct"] == 2
        assert result["incorrect"] == 1
        assert result["score"] == round(2 / 3 * 100, 2)
        assert len(result["topic_performance"]) == 1
        assert result["topic_performance"][0]["topic_name"] == "Percentages"

        # 8. Student views result
        result_resp = client.get(f"/api/attempts/{attempt_id}/result", headers=_auth(student_token))
        assert result_resp.json()["data"]["status"] == "SUBMITTED"

        # 9. Student views history
        history_resp = client.get("/api/students/me/attempts", headers=_auth(student_token))
        assert len(history_resp.json()["data"]) == 1

        # 10. Verify DB records
        from app.models.assessment import Attempt
        attempt = db.get(Attempt, attempt_id)
        assert attempt.status == "SUBMITTED"
        assert float(attempt.score) == result["score"]
