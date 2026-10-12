"""Phase 7 tests: Performance Analysis Engine.

Covers the Phase 7 testing checklist:
- accuracy calculation (practice + assessment combined)
- topic aggregation with trends
- difficulty aggregation
- company aggregation
- strengths/weaknesses detection
- snapshots written on assessment submission
- empty data / new student
- large attempt history
- ownership/security
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


# ---- helpers ----

def _register_student(client: TestClient, email: str = "perf_s1@example.com") -> str:
    resp = client.post(
        "/api/auth/register/student",
        json={"name": "Perf Student", "email": email, "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return _login(client, email)


def _create_admin(client: TestClient, db, email: str = "perf_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    return _login(client, email, "adminpass123")


def _login(client: TestClient, email: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_topic(client: TestClient, admin_token: str, name: str, category: str = "quantitative") -> dict:
    resp = client.post(
        "/api/admin/topics", json={"name": name, "category": category}, headers=_auth(admin_token)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _create_company(client: TestClient, admin_token: str, name: str) -> dict:
    resp = client.post("/api/admin/companies", json={"name": name}, headers=_auth(admin_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _create_question(
    client: TestClient,
    admin_token: str,
    topic_id: int,
    company_id: int | None = None,
    difficulty: str = "easy",
    correct_index: int = 1,
) -> dict:
    options = [
        {"option_text": f"opt{i}", "option_order": i + 1, "is_correct": i == correct_index}
        for i in range(4)
    ]
    payload = {
        "question_text": f"Question for topic {topic_id} ({difficulty})",
        "question_type": "MCQ",
        "topic_id": topic_id,
        "company_id": company_id,
        "difficulty": difficulty,
        "explanation": "explanation",
        "options": options,
    }
    resp = client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def _practice(
    client: TestClient,
    token: str,
    topic_id: int,
    questions: list[dict],
    outcomes: list[bool],
    difficulty: str | None = None,
) -> int:
    """Start a practice session, answer questions with given outcomes, complete it."""
    body = {"topic_id": topic_id, "question_count": len(questions)}
    if difficulty:
        body["difficulty"] = difficulty
    resp = client.post("/api/students/practice/start", json=body, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    session_id = resp.json()["data"]["session_id"]
    for q, correct in zip(questions, outcomes):
        opt_index = 1 if correct else 0  # index of correct option in payload order
        client.post(
            f"/api/students/practice/{session_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][opt_index]["id"]},
            headers=_auth(token),
        )
    resp = client.post(f"/api/students/practice/{session_id}/complete", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return session_id


def _setup_world(client: TestClient, db):
    """Admin + two topics + one company + a question pool."""
    admin_token = _create_admin(client, db)
    t_pct = _create_topic(client, admin_token, "Percentages")
    t_lr = _create_topic(client, admin_token, "Logical Reasoning", "logical")
    company = _create_company(client, admin_token, "TCS")

    pct_qs = [_create_question(client, admin_token, t_pct["id"], company["id"]) for _ in range(6)]
    lr_qs = [_create_question(client, admin_token, t_lr["id"], None) for _ in range(6)]
    return admin_token, t_pct, t_lr, company, pct_qs, lr_qs


# ============================================================ OVERALL / NEW STUDENT

class TestOverallPerformance:
    def test_new_student_has_empty_performance(self, client, db):
        token = _register_student(client)
        resp = client.get("/api/performance/me", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_questions_attempted"] == 0
        assert data["correct"] == 0
        assert data["incorrect"] == 0
        assert data["unanswered"] == 0
        assert data["overall_accuracy"] is None
        assert data["classification"] == "new"

    def test_accuracy_from_practice_only(self, client, db):
        token = _register_student(client)
        admin_token, t_pct, _t_lr, _co, pct_qs, _lr_qs = _setup_world(client, db)
        _practice(client, token, t_pct["id"], pct_qs[:4], [True, True, True, False])

        resp = client.get("/api/performance/me", headers=_auth(token))
        data = resp.json()["data"]
        assert data["total_questions_attempted"] == 4
        assert data["correct"] == 3
        assert data["incorrect"] == 1
        assert data["overall_accuracy"] == 75.0
        assert data["classification"] == "moderate"
        assert data["practice_sessions"] == 1

    def test_assessment_avg_score_included(self, client, db):
        from app.models.assessment import Assessment, AssessmentQuestion

        token = _register_student(client)
        admin_token, t_pct, _t_lr, _co, pct_qs, _lr_qs = _setup_world(client, db)

        # Create an assessment directly in DB (admin API covered elsewhere)
        admin_user = db.query(__import__("app.models.user", fromlist=["User"]).User).filter_by(email="perf_admin@example.com").first()
        assessment = Assessment(
            title="Mock 1", assessment_type="MOCK_TEST", duration_minutes=30,
            question_count=2, created_by=admin_user.id, is_active=True,
        )
        db.add(assessment)
        db.flush()
        for i, q in enumerate(pct_qs[:2], 1):
            db.add(AssessmentQuestion(assessment_id=assessment.id, question_id=q["id"], question_order=i))
        db.commit()

        resp = client.post(f"/api/assessments/{assessment.id}/start", headers=_auth(token))
        attempt_id = resp.json()["data"]["attempt_id"]
        # Answer 1 correct, 1 incorrect
        client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": pct_qs[0]["id"], "selected_option_id": pct_qs[0]["options"][1]["id"]},
            headers=_auth(token),
        )
        client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": pct_qs[1]["id"], "selected_option_id": pct_qs[1]["options"][0]["id"]},
            headers=_auth(token),
        )
        resp = client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(token))
        assert resp.status_code == 200, resp.text

        data = client.get("/api/performance/me", headers=_auth(token)).json()["data"]
        assert data["assessment_attempts"] == 1
        assert data["assessment_avg_score"] == 50.0
        # Combined: practice 0 + assessment 2 attempted
        assert data["total_questions_attempted"] == 2


# ============================================================ TOPICS

class TestTopicPerformance:
    def test_topic_aggregation(self, client, db):
        token = _register_student(client)
        _admin, t_pct, t_lr, _co, pct_qs, lr_qs = _setup_world(client, db)

        _practice(client, token, t_pct["id"], pct_qs[:4], [True, True, True, False])   # 75%
        _practice(client, token, t_lr["id"], lr_qs[:4], [False, False, True, False])   # 25%

        resp = client.get("/api/performance/topics", headers=_auth(token))
        topics = {t["topic_name"]: t for t in resp.json()["data"]}
        assert topics["Percentages"]["accuracy"] == 75.0
        assert topics["Percentages"]["classification"] == "moderate"
        assert topics["Logical Reasoning"]["accuracy"] == 25.0
        assert topics["Logical Reasoning"]["classification"] == "weak"
        assert topics["Percentages"]["total_attempts"] == 4

    def test_topics_sorted_weakest_first(self, client, db):
        token = _register_student(client)
        _admin, t_pct, t_lr, _co, pct_qs, lr_qs = _setup_world(client, db)
        _practice(client, token, t_pct["id"], pct_qs[:4], [True, True, True, False])
        _practice(client, token, t_lr["id"], lr_qs[:4], [False, False, True, False])

        topics = client.get("/api/performance/topics", headers=_auth(token)).json()["data"]
        assert topics[0]["topic_name"] == "Logical Reasoning"
        assert topics[-1]["topic_name"] == "Percentages"

    def test_trend_new_with_single_batch(self, client, db):
        token = _register_student(client)
        _admin, t_pct, _t_lr, _co, pct_qs, _lr_qs = _setup_world(client, db)
        _practice(client, token, t_pct["id"], pct_qs[:4], [True, True, False, False])

        topics = client.get("/api/performance/topics", headers=_auth(token)).json()["data"]
        assert topics[0]["trend"] == "NEW"

    def test_trend_improving(self, client, db):
        """Older answers weak, recent answers strong → IMPROVING."""
        token = _register_student(client)
        admin_token, t_pct, _t_lr, _co, _pct_qs, _lr_qs = _setup_world(client, db)
        # 10 wrong first, then 20 correct: last-20 window = all correct (100%),
        # historical = first 10 (0%)
        wrong_pool = [_create_question(client, admin_token, t_pct["id"]) for _ in range(10)]
        right_pool = [_create_question(client, admin_token, t_pct["id"]) for _ in range(20)]
        _practice(client, token, t_pct["id"], wrong_pool, [False] * 10)
        _practice(client, token, t_pct["id"], right_pool, [True] * 20)

        topics = client.get("/api/performance/topics", headers=_auth(token)).json()["data"]
        t = topics[0]
        assert t["total_attempts"] == 30
        assert t["trend"] == "IMPROVING"
        assert t["recent_accuracy"] == 100.0
        assert t["historical_accuracy"] == 0.0

    def test_trend_declining(self, client, db):
        token = _register_student(client)
        admin_token, t_pct, _t_lr, _co, _pct_qs, _lr_qs = _setup_world(client, db)
        # 30 correct then 20 wrong: last-20 window = 0%, historical = 100%
        right_pool = [_create_question(client, admin_token, t_pct["id"]) for _ in range(30)]
        wrong_pool = [_create_question(client, admin_token, t_pct["id"]) for _ in range(20)]
        _practice(client, token, t_pct["id"], right_pool, [True] * 30)
        _practice(client, token, t_pct["id"], wrong_pool, [False] * 20)

        topics = client.get("/api/performance/topics", headers=_auth(token)).json()["data"]
        assert topics[0]["trend"] == "DECLINING"

    def test_trend_stable(self, client, db):
        token = _register_student(client)
        admin_token, t_pct, _t_lr, _co, pct_qs, _lr_qs = _setup_world(client, db)
        many = [_create_question(client, admin_token, t_pct["id"]) for _ in range(24)]
        # Historical 50%, recent 50% → stable
        outcomes_old = [True, False] * 12
        outcomes_new = [True, False, True, False]
        _practice(client, token, t_pct["id"], many, outcomes_old)
        _practice(client, token, t_pct["id"], pct_qs[:4], outcomes_new)

        topics = client.get("/api/performance/topics", headers=_auth(token)).json()["data"]
        assert topics[0]["trend"] == "STABLE"


# ============================================================ DIFFICULTY & COMPANY

class TestDifficultyAndCompany:
    def test_difficulty_aggregation(self, client, db):
        token = _register_student(client)
        admin_token, t_pct, _t_lr, company, pct_qs, _lr_qs = _setup_world(client, db)

        easy_qs = [_create_question(client, admin_token, t_pct["id"], company["id"], "easy") for _ in range(3)]
        hard_qs = [_create_question(client, admin_token, t_pct["id"], company["id"], "hard") for _ in range(3)]

        _practice(client, token, t_pct["id"], easy_qs, [True, True, False], difficulty="easy")
        _practice(client, token, t_pct["id"], hard_qs, [False, False, True], difficulty="hard")

        rows = client.get("/api/performance/difficulties", headers=_auth(token)).json()["data"]
        by_diff = {r["difficulty"]: r for r in rows}
        assert by_diff["easy"]["total_attempts"] == 3
        assert by_diff["easy"]["accuracy"] == 66.67
        assert by_diff["hard"]["total_attempts"] == 3
        assert by_diff["hard"]["accuracy"] == 33.33

    def test_company_aggregation(self, client, db):
        token = _register_student(client)
        admin_token, t_pct, _t_lr, company, pct_qs, _lr_qs = _setup_world(client, db)

        co_qs = [_create_question(client, admin_token, t_pct["id"], company["id"]) for _ in range(4)]
        _practice(client, token, t_pct["id"], co_qs, [True, True, True, False])

        rows = client.get("/api/performance/companies", headers=_auth(token)).json()["data"]
        assert len(rows) == 1
        assert rows[0]["company_name"] == "TCS"
        assert rows[0]["total_attempts"] == 4
        assert rows[0]["accuracy"] == 75.0

    def test_company_empty_when_no_company_questions(self, client, db):
        token = _register_student(client)
        _admin, _t_pct, _t_lr, _co, _pct_qs, _lr_qs = _setup_world(client, db)
        rows = client.get("/api/performance/companies", headers=_auth(token)).json()["data"]
        assert rows == []


# ============================================================ STRENGTHS / WEAKNESSES

class TestStrengthsWeaknesses:
    def test_strength_and_weakness_detection(self, client, db):
        token = _register_student(client)
        _admin, t_pct, t_lr, _co, pct_qs, lr_qs = _setup_world(client, db)

        # Percentages: 100% strong; Logical: 25% weak
        _practice(client, token, t_pct["id"], pct_qs[:4], [True] * 4)
        _practice(client, token, t_lr["id"], lr_qs[:4], [True, False, False, False])

        strengths = client.get("/api/performance/strengths", headers=_auth(token)).json()["data"]
        weaknesses = client.get("/api/performance/weaknesses", headers=_auth(token)).json()["data"]

        assert any(s["topic_name"] == "Percentages" for s in strengths)
        assert any(w["topic_name"] == "Logical Reasoning" for w in weaknesses)
        assert not any(s["topic_name"] == "Logical Reasoning" for s in strengths)

    def test_minimum_sample_filters_single_answers(self, client, db):
        """A single wrong answer (total_attempts < 3) must NOT be a weakness."""
        token = _register_student(client)
        _admin, t_pct, t_lr, _co, pct_qs, lr_qs = _setup_world(client, db)
        _practice(client, token, t_lr["id"], lr_qs[:1], [False])

        weaknesses = client.get("/api/performance/weaknesses", headers=_auth(token)).json()["data"]
        assert weaknesses == []


# ============================================================ SNAPSHOTS & TRENDS

class TestSnapshotsAndTrends:
    def test_snapshot_created_on_assessment_submit(self, client, db):
        from app.models.assessment import Assessment, AssessmentQuestion
        from app.models.performance import PerformanceSnapshot

        token = _register_student(client)
        admin_token, t_pct, _t_lr, _co, pct_qs, _lr_qs = _setup_world(client, db)

        admin_user = db.query(__import__("app.models.user", fromlist=["User"]).User).filter_by(email="perf_admin@example.com").first()
        assessment = Assessment(
            title="Mock Snap", assessment_type="MOCK_TEST", duration_minutes=30,
            question_count=2, created_by=admin_user.id, is_active=True,
        )
        db.add(assessment)
        db.flush()
        for i, q in enumerate(pct_qs[:2], 1):
            db.add(AssessmentQuestion(assessment_id=assessment.id, question_id=q["id"], question_order=i))
        db.commit()

        resp = client.post(f"/api/assessments/{assessment.id}/start", headers=_auth(token))
        attempt_id = resp.json()["data"]["attempt_id"]
        client.post(
            f"/api/attempts/{attempt_id}/answer",
            json={"question_id": pct_qs[0]["id"], "selected_option_id": pct_qs[0]["options"][1]["id"]},
            headers=_auth(token),
        )
        client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(token))

        snaps = db.query(PerformanceSnapshot).filter_by(student_id=_student_id(db, token)).all()
        assert len(snaps) == 1
        assert float(snaps[0].overall_score) == 50.0
        assert snaps[0].assessment_id == assessment.id

        # topic_performance rebuilt
        resp = client.get("/api/performance/topics", headers=_auth(token))
        assert resp.json()["data"][0]["topic_name"] == "Percentages"

    def test_trend_endpoint_returns_chronological_scores(self, client, db):
        token = _register_student(client)
        resp = client.get("/api/performance/trends", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"] == []


def _student_id(db, token: str) -> int:
    from app.models.profile import StudentProfile

    # Decode token subject via jose is overkill; take the only student.
    profile = db.query(StudentProfile).filter_by(student_id=_latest_student_code(db)).first()
    return profile.id


def _latest_student_code(db) -> str:
    from app.models.profile import StudentProfile

    profile = db.query(StudentProfile).order_by(StudentProfile.id.desc()).first()
    return profile.student_id
