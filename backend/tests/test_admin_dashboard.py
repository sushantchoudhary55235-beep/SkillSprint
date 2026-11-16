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


class TestAnalyticsBreakdowns:
    """Phase 15D: Test coverage for analytics breakdown endpoints."""

    def _seed_analytics_data(self, client, db, admin_token):
        """Seed topics, questions, students, and activity for analytics tests."""
        from app.core.security import hash_password
        from app.models.content import Topic
        from app.models.question import Question, QuestionOption
        from app.models.user import User
        from app.models.profile import StudentProfile
        from app.models.practice import PracticeSession, PracticeAnswer
        from app.models.assessment import Assessment, Attempt, Answer
        from app.models.coding import CodingProblem, CodeSubmission
        from datetime import datetime, timedelta, timezone

        # Create topics
        t1 = Topic(name="Percentages", category="quant")
        t2 = Topic(name="Arrays", category="dsa")
        db.add_all([t1, t2])
        db.commit()
        db.refresh(t1)
        db.refresh(t2)

        # Create questions with options (correct answer stored in QuestionOption.is_correct)
        q1 = Question(topic_id=t1.id, question_text="Q1", question_type="MCQ", difficulty="easy", status="APPROVED")
        q2 = Question(topic_id=t1.id, question_text="Q2", question_type="MCQ", difficulty="medium", status="APPROVED")
        q3 = Question(topic_id=t2.id, question_text="Q3", question_type="MCQ", difficulty="hard", status="APPROVED")
        db.add_all([q1, q2, q3])
        db.commit()
        db.refresh(q1)
        db.refresh(q2)
        db.refresh(q3)

        # Add options with correct answers
        opt1 = QuestionOption(question_id=q1.id, option_text="A", option_order=1, is_correct=True)
        opt2 = QuestionOption(question_id=q1.id, option_text="B", option_order=2, is_correct=False)
        opt3 = QuestionOption(question_id=q2.id, option_text="A", option_order=1, is_correct=True)
        opt4 = QuestionOption(question_id=q2.id, option_text="B", option_order=2, is_correct=False)
        opt5 = QuestionOption(question_id=q3.id, option_text="A", option_order=1, is_correct=True)
        opt6 = QuestionOption(question_id=q3.id, option_text="B", option_order=2, is_correct=False)
        db.add_all([opt1, opt2, opt3, opt4, opt5, opt6])
        db.commit()

        # Create students with profiles
        s1 = User(name="Student One", email="s1_analytics@example.com", password_hash=hash_password("pass"), role="student")
        s2 = User(name="Student Two", email="s2_analytics@example.com", password_hash=hash_password("pass"), role="student")
        db.add_all([s1, s2])
        db.commit()
        db.refresh(s1)
        db.refresh(s2)

        sp1 = StudentProfile(user_id=s1.id, student_id="S1ANALYTICS", xp=100, level=2, current_streak=3, readiness_score=50.0)
        sp2 = StudentProfile(user_id=s2.id, student_id="S2ANALYTICS", xp=200, level=3, current_streak=5, readiness_score=75.0)
        db.add_all([sp1, sp2])
        db.commit()

        # Create practice sessions and answers (for TopicPerformance & popular_topics)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)

        # Student 1: 3 practice answers on q1 (t1), 2 on q2 (t1) - recent
        ps1 = PracticeSession(student_id=sp1.id, mode="practice", topic_id=t1.id, question_count=5, status="COMPLETED", created_at=week_ago + timedelta(days=1))
        ps2 = PracticeSession(student_id=sp1.id, mode="practice", topic_id=t1.id, question_count=3, status="COMPLETED", created_at=week_ago + timedelta(days=2))
        db.add_all([ps1, ps2])
        db.commit()
        db.refresh(ps1)
        db.refresh(ps2)

        pa1 = PracticeAnswer(session_id=ps1.id, question_id=q1.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        pa2 = PracticeAnswer(session_id=ps1.id, question_id=q1.id, selected_option_id=0, is_correct=True, time_taken_seconds=15, created_at=week_ago + timedelta(days=1))
        pa3 = PracticeAnswer(session_id=ps1.id, question_id=q1.id, selected_option_id=0, is_correct=False, time_taken_seconds=20, created_at=week_ago + timedelta(days=1))
        pa4 = PracticeAnswer(session_id=ps2.id, question_id=q2.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=2))
        pa5 = PracticeAnswer(session_id=ps2.id, question_id=q2.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=2))
        db.add_all([pa1, pa2, pa3, pa4, pa5])

        # Student 2: 2 practice answers on q3 (t2) - recent
        ps3 = PracticeSession(student_id=sp2.id, mode="practice", topic_id=t2.id, question_count=2, status="COMPLETED", created_at=week_ago + timedelta(days=1))
        db.add(ps3)
        db.commit()
        db.refresh(ps3)

        pa6 = PracticeAnswer(session_id=ps3.id, question_id=q3.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        pa7 = PracticeAnswer(session_id=ps3.id, question_id=q3.id, selected_option_id=0, is_correct=False, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        db.add_all([pa6, pa7])

        # Old answers (should NOT count for popular_topics_week)
        ps_old = PracticeSession(student_id=sp1.id, mode="practice", topic_id=t1.id, question_count=1, status="COMPLETED", created_at=two_weeks_ago)
        db.add(ps_old)
        db.commit()
        db.refresh(ps_old)
        pa_old = PracticeAnswer(session_id=ps_old.id, question_id=q1.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=two_weeks_ago)
        db.add(pa_old)

        # Assessment attempts and answers (for TopicPerformance & popular_topics)
        assess = Assessment(title="Test Assessment", assessment_type="PRACTICE", duration_minutes=30, question_count=2, created_at=week_ago)
        db.add(assess)
        db.commit()
        db.refresh(assess)

        # Link questions to assessment
        assess_question_ids = [q1.id, q2.id]

        att1 = Attempt(student_id=sp1.id, assessment_id=assess.id, status="SUBMITTED", started_at=week_ago + timedelta(days=1), submitted_at=week_ago + timedelta(days=1), score=80.0, accuracy=80.0, time_taken_seconds=300)
        att2 = Attempt(student_id=sp2.id, assessment_id=assess.id, status="SUBMITTED", started_at=week_ago + timedelta(days=1), submitted_at=week_ago + timedelta(days=1), score=50.0, accuracy=50.0, time_taken_seconds=400)
        db.add_all([att1, att2])
        db.commit()
        db.refresh(att1)
        db.refresh(att2)

        ans1 = Answer(attempt_id=att1.id, question_id=q1.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        ans2 = Answer(attempt_id=att1.id, question_id=q2.id, selected_option_id=0, is_correct=False, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        ans3 = Answer(attempt_id=att2.id, question_id=q1.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        ans4 = Answer(attempt_id=att2.id, question_id=q2.id, selected_option_id=0, is_correct=True, time_taken_seconds=10, created_at=week_ago + timedelta(days=1))
        db.add_all([ans1, ans2, ans3, ans4])

        # Coding problems and submissions (for coding_analytics)
        cp1 = CodingProblem(title="Two Sum", difficulty="easy", topic_id=t2.id, input_format="", output_format="", constraints="")
        cp2 = CodingProblem(title="Merge Sort", difficulty="medium", topic_id=t2.id, input_format="", output_format="", constraints="")
        db.add_all([cp1, cp2])
        db.commit()
        db.refresh(cp1)
        db.refresh(cp2)

        # Submissions for sp1 on cp1 (passed 2/3 test cases)
        cs1 = CodeSubmission(student_id=sp1.id, problem_id=cp1.id, language="python", source_code="print(1)", passed_test_cases=2, total_test_cases=3, status="PASSED", created_at=week_ago + timedelta(days=1))
        cs2 = CodeSubmission(student_id=sp1.id, problem_id=cp1.id, language="python", source_code="print(2)", passed_test_cases=0, total_test_cases=3, status="FAILED", created_at=week_ago + timedelta(days=1))
        cs3 = CodeSubmission(student_id=sp2.id, problem_id=cp1.id, language="javascript", source_code="console.log(1)", passed_test_cases=3, total_test_cases=3, status="PASSED", created_at=week_ago + timedelta(days=1))
        cs4 = CodeSubmission(student_id=sp2.id, problem_id=cp2.id, language="python", source_code="print(3)", passed_test_cases=1, total_test_cases=5, status="FAILED", created_at=week_ago + timedelta(days=1))
        db.add_all([cs1, cs2, cs3, cs4])

        # TopicPerformance rows (for question_analytics)
        from app.models.performance import TopicPerformance
        tp1 = TopicPerformance(student_id=sp1.id, topic_id=t1.id, total_attempts=5, correct_answers=4)
        tp2 = TopicPerformance(student_id=sp2.id, topic_id=t1.id, total_attempts=2, correct_answers=1)
        tp3 = TopicPerformance(student_id=sp2.id, topic_id=t2.id, total_attempts=2, correct_answers=1)
        db.add_all([tp1, tp2, tp3])

        db.commit()

        return {
            "topics": [t1, t2],
            "questions": [q1, q2, q3],
            "students": [sp1, sp2],
            "coding_problems": [cp1, cp2],
        }

    def test_analytics_students(self, client, db):
        admin = _admin(client, db)
        self._seed_analytics_data(client, db, admin)

        resp = client.get("/api/admin/analytics/students", headers=_auth(admin))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 2

        # Verify structure of first student
        student = data[0]
        for key in ("student_profile_id", "student_id", "name", "email", "is_active",
                    "accuracy", "questions_attempted", "assessment_avg_score",
                    "problems_solved", "streak_days", "xp", "level", "readiness_score"):
            assert key in student, f"Missing key: {key}"

        # Verify our seeded students are in the list
        student_ids = {s["student_id"] for s in data}
        assert "S1ANALYTICS" in student_ids
        assert "S2ANALYTICS" in student_ids

    def test_analytics_questions(self, client, db):
        admin = _admin(client, db)
        self._seed_analytics_data(client, db, admin)

        resp = client.get("/api/admin/analytics/questions", headers=_auth(admin))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        # Verify structure
        assert "topics" in data
        assert "difficulty_distribution" in data

        topics = data["topics"]
        assert isinstance(topics, list)
        assert len(topics) >= 2

        # Verify topic structure and ordering
        for topic in topics:
            assert "topic_id" in topic
            assert "topic_name" in topic
            assert "total_attempts" in topic
            assert "accuracy" in topic

        # Topics should be ordered by total_attempts descending
        attempts = [t["total_attempts"] for t in topics]
        assert attempts == sorted(attempts, reverse=True)

        # Difficulty distribution
        diff_dist = data["difficulty_distribution"]
        assert isinstance(diff_dist, dict)
        assert "easy" in diff_dist or "medium" in diff_dist or "hard" in diff_dist
        for count in diff_dist.values():
            assert isinstance(count, int)

    def test_analytics_submissions(self, client, db):
        admin = _admin(client, db)
        self._seed_analytics_data(client, db, admin)

        resp = client.get("/api/admin/analytics/submissions", headers=_auth(admin))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        # Verify structure
        assert "problems" in data
        assert "language_distribution" in data

        problems = data["problems"]
        assert isinstance(problems, list)
        assert len(problems) >= 2

        for prob in problems:
            assert "problem_id" in prob
            assert "title" in prob
            assert "difficulty" in prob
            assert "submissions" in prob
            assert "pass_rate" in prob

        # Problems ordered by submissions descending
        subs = [p["submissions"] for p in problems]
        assert subs == sorted(subs, reverse=True)

        # Language distribution
        lang_dist = data["language_distribution"]
        assert isinstance(lang_dist, dict)
        assert "python" in lang_dist
        assert "javascript" in lang_dist
        for count in lang_dist.values():
            assert isinstance(count, int)

        # Verify pass_rate calculation for cp1 (Two Sum): 3 submissions, 5 passed / 9 total = 55.55%
        cp1_data = next(p for p in problems if p["title"] == "Two Sum")
        assert cp1_data["submissions"] == 3
        assert cp1_data["pass_rate"] == round(5 / 9 * 100, 2)

    def test_analytics_popular_topics(self, client, db):
        admin = _admin(client, db)
        self._seed_analytics_data(client, db, admin)

        resp = client.get("/api/admin/analytics/popular-topics?limit=5", headers=_auth(admin))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert isinstance(data, list)
        assert len(data) <= 5

        for topic in data:
            assert "topic_id" in topic
            assert "topic_name" in topic
            assert "attempts" in topic

        # Should be ordered by attempts descending
        attempts = [t["attempts"] for t in data]
        assert attempts == sorted(attempts, reverse=True)

        # t1 (Percentages) should have more attempts than t2 (Arrays)
        # t1: 5 practice + 2 assessment = 7 recent; t2: 2 practice + 0 assessment = 2 recent
        # Old practice (1) should NOT be counted
        topic_names = {t["topic_name"]: t["attempts"] for t in data}
        assert topic_names.get("Percentages", 0) > topic_names.get("Arrays", 0)

    def test_analytics_breakdowns_require_admin(self, client, db):
        student = _register(client, "student_rbac@example.com")
        teacher = _register(client, "teacher_rbac@example.com", "teacher")

        endpoints = [
            "/api/admin/analytics/students",
            "/api/admin/analytics/questions",
            "/api/admin/analytics/submissions",
            "/api/admin/analytics/popular-topics",
        ]

        for endpoint in endpoints:
            # Student should get 403
            resp = client.get(endpoint, headers=_auth(student))
            assert resp.status_code == 403, f"Student should get 403 for {endpoint}, got {resp.status_code}"

            # Teacher should get 403
            resp = client.get(endpoint, headers=_auth(teacher))
            assert resp.status_code == 403, f"Teacher should get 403 for {endpoint}, got {resp.status_code}"
