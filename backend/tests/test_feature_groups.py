"""Feature group tests: coaching (dashboard/daily plan/skill gap/trends/revision),
adaptive difficulty, bookmarks, interview prep, and readiness breakdown.

All values must derive from real backend data — the core assertion strategy is
to create known performance patterns and verify the deterministic outputs.
"""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


def _login(client: TestClient, email: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> str:
    client.post(
        "/api/auth/register/student",
        json={"name": email.split("@")[0], "email": email, "password": "password123"},
    )
    return _login(client, email)


def _admin(client: TestClient, db, email: str = "fg_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    db.add(User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin"))
    db.commit()
    return _login(client, email, "adminpass123")


def _topic(client: TestClient, admin: str, name: str, category: str = "quantitative") -> dict:
    resp = client.post("/api/admin/topics", json={"name": name, "category": category}, headers=_auth(admin))
    assert resp.status_code == 201
    return resp.json()["data"]


def _questions(client: TestClient, admin: str, topic_id: int, n: int = 5) -> list[dict]:
    out = []
    for i in range(n):
        payload = {
            "question_text": f"Q{topic_id}-{i}",
            "question_type": "MCQ",
            "topic_id": topic_id,
            "difficulty": "easy",
            "options": [
                {"option_text": "a", "option_order": 1, "is_correct": False},
                {"option_text": "b", "option_order": 2, "is_correct": True},
                {"option_text": "c", "option_order": 3, "is_correct": False},
                {"option_text": "d", "option_order": 4, "is_correct": False},
            ],
        }
        resp = client.post("/api/admin/questions", json=payload, headers=_auth(admin))
        assert resp.status_code == 201
        out.append(resp.json()["data"])
    return out


def _practice(client: TestClient, token: str, topic_id: int, questions: list[dict], outcomes: list[bool]) -> dict:
    resp = client.post(
        "/api/students/practice/start",
        json={"topic_id": topic_id, "question_count": len(questions)},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    sid = resp.json()["data"]["session_id"]
    for q, ok in zip(questions, outcomes):
        client.post(
            f"/api/students/practice/{sid}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1 if ok else 0]["id"]},
            headers=_auth(token),
        )
    resp = client.post(f"/api/students/practice/{sid}/complete", headers=_auth(token))
    assert resp.status_code == 200
    return resp.json()["data"]


def _coding_problem(client: TestClient, admin: str, topic_id: int, title: str = "Sum Two") -> int:
    """Insert a coding problem directly (admin CRUD for problems may not exist)."""
    from app.models.coding import CodingProblem, TestCase as TC

    from app.db.session import SessionLocal  # not used; we use the test db fixture

    return 0  # replaced below


# ============================================================ COACHING DASHBOARD

class TestCoachingDashboard:
    def test_dashboard_requires_student(self, client, db):
        assert client.get("/api/coaching/dashboard").status_code == 401

    def test_new_student_empty_state(self, client, db):
        token = _register(client, "fg_new@example.com")
        resp = client.get("/api/coaching/dashboard", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_accuracy"] is None
        assert data["readiness"]["data_completeness"] <= 0.5
        assert data["todays_plan"]["items"], "plan always has at least the XP item"

    def test_dashboard_reflects_real_activity(self, client, db):
        admin = _admin(client, db)
        t1 = _topic(client, admin, "FG Weak Topic")
        t2 = _topic(client, admin, "FG Strong Topic")
        qs1 = _questions(client, admin, t1["id"])
        qs2 = _questions(client, admin, t2["id"])
        token = _register(client, "fg_active@example.com")

        _practice(client, token, t1["id"], qs1, [False] * 5)   # weak
        _practice(client, token, t2["id"], qs2, [True] * 5)    # strong

        resp = client.get("/api/coaching/dashboard", headers=_auth(token))
        data = resp.json()["data"]

        assert data["current_accuracy"] == 50.0
        assert data["xp_today"] > 0
        assert data["weakest_aptitude_topic"]["topic_id"] == t1["id"]
        assert data["weakest_aptitude_topic"]["accuracy"] == 0.0
        assert data["readiness"]["score"] > 0
        assert data["todays_plan"]["xp_earned_today"] == data["xp_today"]

    def test_two_students_get_different_plans(self, client, db):
        admin = _admin(client, db)
        ta = _topic(client, admin, "FG Plan Topic A")
        tb = _topic(client, admin, "FG Plan Topic B")
        qa = _questions(client, admin, ta["id"])
        qb = _questions(client, admin, tb["id"])

        a = _register(client, "fg_plan_a@example.com")
        b = _register(client, "fg_plan_b@example.com")
        _practice(client, a, ta["id"], qa, [False] * 5)
        _practice(client, b, tb["id"], qb, [False] * 5)

        plan_a = client.get("/api/coaching/daily-plan", headers=_auth(a)).json()["data"]
        plan_b = client.get("/api/coaching/daily-plan", headers=_auth(b)).json()["data"]
        assert plan_a["focus_topic"] == ta["name"]
        assert plan_b["focus_topic"] == tb["name"]


# ============================================================ SKILL GAP

class TestSkillGap:
    def test_priorities_follow_accuracy(self, client, db):
        admin = _admin(client, db)
        t1 = _topic(client, admin, "FG Gap Weak")
        t2 = _topic(client, admin, "FG Gap Strong")
        q1 = _questions(client, admin, t1["id"])
        q2 = _questions(client, admin, t2["id"])
        token = _register(client, "fg_gap@example.com")
        _practice(client, token, t1["id"], q1, [False] * 5)
        _practice(client, token, t2["id"], q2, [True] * 5)

        resp = client.get("/api/coaching/skill-gap", headers=_auth(token))
        data = resp.json()["data"]
        by_id = {s["topic_id"]: s for s in data["skills"]}

        weak = by_id[t1["id"]]
        strong = by_id[t2["id"]]
        assert weak["priority"] == "HIGH"
        assert weak["level"] == "weak"
        assert strong["level"] == "strong"
        assert strong["priority_score"] < weak["priority_score"]
        assert data["skills"][0]["topic_id"] == t1["id"]  # sorted by urgency
        assert "formula" in data  # transparency requirement

    def test_insufficient_data_flagged(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Gap Tiny")
        qs = _questions(client, admin, t["id"], n=2)
        token = _register(client, "fg_gap2@example.com")
        _practice(client, token, t["id"], qs, [False] * 2)

        data = client.get("/api/coaching/skill-gap", headers=_auth(token)).json()["data"]
        assert data["skills"][0]["priority"] == "INSUFFICIENT_DATA"


# ============================================================ ADAPTIVE DIFFICULTY

class TestAdaptiveDifficulty:
    def test_low_accuracy_recommends_easy(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Adapt Low")
        qs = _questions(client, admin, t["id"], n=6)
        token = _register(client, "fg_adapt1@example.com")
        _practice(client, token, t["id"], qs, [True, False, False, False, True, False])

        data = client.get("/api/adaptive/difficulty", headers=_auth(token)).json()["data"]
        assert data["suggested_difficulty"] == "easy"
        assert data["window_accuracy"] < 60
        assert data["algorithm"]["window"] == 10

    def test_high_accuracy_recommends_hard(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Adapt High")
        qs = _questions(client, admin, t["id"], n=6)
        token = _register(client, "fg_adapt2@example.com")
        _practice(client, token, t["id"], qs, [True] * 6)

        data = client.get("/api/adaptive/difficulty", headers=_auth(token)).json()["data"]
        assert data["suggested_difficulty"] == "hard"
        assert data["window_accuracy"] >= 80

    def test_no_data_defaults_easy(self, client, db):
        token = _register(client, "fg_adapt3@example.com")
        data = client.get("/api/adaptive/difficulty", headers=_auth(token)).json()["data"]
        assert data["suggested_difficulty"] == "easy"
        assert data["window_accuracy"] is None


# ============================================================ TRENDS

class TestProgressTrends:
    def test_7_day_window_has_data_after_practice(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Trend Topic")
        qs = _questions(client, admin, t["id"])
        token = _register(client, "fg_trend@example.com")
        _practice(client, token, t["id"], qs, [True] * 5)

        data = client.get("/api/coaching/trends?days=7", headers=_auth(token)).json()["data"]
        assert data["has_data"] is True
        assert data["totals"]["attempted"] == 5
        assert len(data["series"]) == 7
        # accuracy present on days with attempts
        assert any(p["accuracy"] is not None for p in data["series"])

    def test_empty_state_without_data(self, client, db):
        token = _register(client, "fg_trend2@example.com")
        data = client.get("/api/coaching/trends?days=7", headers=_auth(token)).json()["data"]
        assert data["has_data"] is False
        assert data["totals"]["attempted"] == 0

    def test_days_param_validated(self, client, db):
        token = _register(client, "fg_trend3@example.com")
        assert client.get("/api/coaching/trends?days=45", headers=_auth(token)).status_code == 422
        assert client.get("/api/coaching/trends?days=30", headers=_auth(token)).status_code == 200


# ============================================================ REVISION

class TestRevision:
    def test_revision_targets_wrong_answer_topics(self, client, db):
        admin = _admin(client, db)
        t1 = _topic(client, admin, "FG Rev Wrong")
        t2 = _topic(client, admin, "FG Rev Right")
        q1 = _questions(client, admin, t1["id"])
        q2 = _questions(client, admin, t2["id"])
        token = _register(client, "fg_rev@example.com")
        _practice(client, token, t1["id"], q1, [False] * 5)
        _practice(client, token, t2["id"], q2, [True] * 5)

        data = client.get("/api/coaching/revision", headers=_auth(token)).json()["data"]
        assert data["total"] >= 1
        assert data["topics"][0]["topic_id"] == t1["id"]
        assert data["topics"][0]["wrong_count"] == 5

    def test_quick_revision_starts_session(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Rev Session")
        _questions(client, admin, t["id"], n=6)
        token = _register(client, "fg_rev2@example.com")
        qs = _questions(client, admin, t["id"], n=5)
        # five q's registered above create 10 total; practice wrong to build feed
        _practice(client, token, t["id"], qs, [False] * 5)

        resp = client.post("/api/coaching/revision/practice?count=5", headers=_auth(token))
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["session"]["question_count"] == 5
        assert data["topic_id"] == t["id"]

    def test_revision_empty_state(self, client, db):
        token = _register(client, "fg_rev3@example.com")
        data = client.get("/api/coaching/revision", headers=_auth(token)).json()["data"]
        assert data["total"] == 0


# ============================================================ BOOKMARKS

class TestBookmarks:
    def _question(self, client, admin):
        t = _topic(client, admin, "FG Bookmark Topic")
        return _questions(client, admin, t["id"], n=1)[0]

    def test_bookmark_question_roundtrip(self, client, db):
        admin = _admin(client, db)
        q = self._question(client, admin)
        token = _register(client, "fg_bm1@example.com")

        resp = client.post(
            "/api/bookmarks",
            json={"bookmark_type": "QUESTION", "question_id": q["id"]},
            headers=_auth(token),
        )
        assert resp.status_code == 201, resp.text
        bm_id = resp.json()["data"]["id"]

        items = client.get("/api/bookmarks", headers=_auth(token)).json()["data"]
        assert len(items) == 1
        assert items[0]["question_text"] == q["question_text"]
        assert items[0]["correct_answer"] is not None  # review includes answer key

        # duplicate save is idempotent
        resp = client.post(
            "/api/bookmarks",
            json={"bookmark_type": "QUESTION", "question_id": q["id"]},
            headers=_auth(token),
        )
        items = client.get("/api/bookmarks", headers=_auth(token)).json()["data"]
        assert len(items) == 1

        # remove
        resp = client.delete(f"/api/bookmarks/{bm_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert client.get("/api/bookmarks", headers=_auth(token)).json()["data"] == []

    def test_cannot_remove_others_bookmark(self, client, db):
        admin = _admin(client, db)
        q = self._question(client, admin)
        owner = _register(client, "fg_bm2@example.com")
        other = _register(client, "fg_bm3@example.com")
        bm = client.post(
            "/api/bookmarks", json={"bookmark_type": "QUESTION", "question_id": q["id"]},
            headers=_auth(owner),
        ).json()["data"]["id"]
        assert client.delete(f"/api/bookmarks/{bm}", headers=_auth(other)).status_code == 404
        # owner's bookmark intact
        assert len(client.get("/api/bookmarks", headers=_auth(owner)).json()["data"]) == 1

    def test_concept_bookmark_requires_note(self, client, db):
        token = _register(client, "fg_bm4@example.com")
        resp = client.post("/api/bookmarks", json={"bookmark_type": "CONCEPT"}, headers=_auth(token))
        assert resp.status_code == 422


# ============================================================ INTERVIEW PREP

class TestInterviewPrep:
    def test_config_lists_categories(self, client, db):
        token = _register(client, "fg_iv1@example.com")
        data = client.get("/api/interview/config", headers=_auth(token)).json()["data"]
        ids = {c["id"] for c in data["categories"]}
        assert {"TECHNICAL", "HR", "BEHAVIORAL", "SQL", "PYTHON", "DSA", "PROJECT"} <= ids

    def test_questions_do_not_leak_expected_concepts(self, client, db):
        token = _register(client, "fg_iv2@example.com")
        resp = client.get(
            "/api/interview/questions?category=SQL&difficulty=easy", headers=_auth(token)
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["questions"]
        assert all(q["expected_concepts"] is None for q in data["questions"])

    def test_evaluate_returns_deterministic_feedback(self, client, db):
        token = _register(client, "fg_iv3@example.com")
        resp = client.post(
            "/api/interview/evaluate",
            json={"category": "SQL", "question_id": 1,
                  "answer": "An inner join returns only matching rows; a left join keeps all rows "
                            "from the left table with null for non-matches."},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        fb = data["deterministic_feedback"]
        assert fb["source"] == "deterministic"
        assert fb["quality"] in ("good", "partial", "weak")
        assert data["expected_concepts"]
        assert "not a verdict" in data["disclaimer"] or "subjective" in data["disclaimer"]
        # AI feedback only present if configured; when absent the key is None
        assert data["ai_feedback"] is None or data["ai_feedback"]["source"] == "ai"

    def test_evaluate_rejects_empty_answer(self, client, db):
        token = _register(client, "fg_iv4@example.com")
        resp = client.post(
            "/api/interview/evaluate",
            json={"category": "SQL", "question_id": 1, "answer": "   "},
            headers=_auth(token),
        )
        assert resp.status_code == 422

    def test_invalid_category_rejected(self, client, db):
        token = _register(client, "fg_iv5@example.com")
        resp = client.get(
            "/api/interview/questions?category=COOKING&difficulty=easy", headers=_auth(token)
        )
        assert resp.status_code == 422


# ============================================================ READINESS BREAKDOWN

class TestReadinessBreakdown:
    def test_components_present_and_weighted(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Ready Topic")
        qs = _questions(client, admin, t["id"])
        token = _register(client, "fg_ready@example.com")
        _practice(client, token, t["id"], qs, [True] * 5)

        data = client.get("/api/performance/readiness", headers=_auth(token)).json()["data"]
        assert set(data["components"]) == {"aptitude", "coding", "consistency", "coverage", "assessment"}
        assert abs(sum(data["weights"].values()) - 1.0) < 1e-9
        assert 0 <= data["score"] <= 100
        assert data["aptitude"]["attempted"] == 5
        assert data["coverage"]["topics_attempted"] >= 1

    def test_profile_readiness_synced_after_practice(self, client, db):
        admin = _admin(client, db)
        t = _topic(client, admin, "FG Ready Sync")
        qs = _questions(client, admin, t["id"])
        token = _register(client, "fg_ready2@example.com")
        _practice(client, token, t["id"], qs, [True] * 5)

        profile = client.get("/api/students/profile", headers=_auth(token)).json()["data"]
        readiness = client.get("/api/performance/readiness", headers=_auth(token)).json()["data"]
        assert abs(profile["readiness_score"] - readiness["score"]) < 0.01


# ============================================================ COMPANY PROFILE

class TestCompanyProfile:
    def test_general_profile_label_when_thin(self, client, db):
        admin = _admin(client, db)
        from app.models.content import Company

        company = db.query(Company).filter_by(name="DemoCorp").first()
        if company is None:
            company = __import__("app.models.content", fromlist=["Company"]).Company(
                name="FG Corp", description="test"
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        token = _register(client, "fg_co@example.com")
        resp = client.get(f"/api/coaching/companies/{company.id}/profile", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_general_profile"] is True
        assert "not represent actual hiring" in data["profile_note"]

    def test_unknown_company_404(self, client, db):
        token = _register(client, "fg_co2@example.com")
        resp = client.get("/api/coaching/companies/99999/profile", headers=_auth(token))
        assert resp.status_code == 404
