"""Phase 10 tests: Gamification Engine.

Covers: XP ledger + duplicate protection, level curve, streaks, missions,
badges, leaderboards, and the critical security rule — clients cannot POST XP.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("db")


# ---- helpers ----

def _login(client: TestClient, email: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> str:
    client.post("/api/auth/register/student",
                json={"name": email.split("@")[0], "email": email, "password": "password123"})
    return _login(client, email)


def _create_admin(client: TestClient, db, email: str = "gam_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    return _login(client, email, "adminpass123")


def _topic(client: TestClient, admin_token: str, name: str = "Gam Topic") -> dict:
    resp = client.post("/api/admin/topics", json={"name": name, "category": "quantitative"}, headers=_auth(admin_token))
    assert resp.status_code == 201
    return resp.json()["data"]


def _question(client: TestClient, admin_token: str, topic_id: int) -> dict:
    payload = {
        "question_text": f"Q{topic_id}-{datetime.now().timestamp()}",
        "question_type": "MCQ",
        "topic_id": topic_id,
        "difficulty": "easy",
        "options": [
            {"option_text": "a", "option_order": 1, "is_correct": False},
            {"option_text": "b", "option_order": 2, "is_correct": True},
        ],
    }
    resp = client.post("/api/admin/questions", json=payload, headers=_auth(admin_token))
    assert resp.status_code == 201
    return resp.json()["data"]


def _practice_session(client: TestClient, token: str, topic_id: int, n: int = 2) -> tuple[int, list[dict]]:
    resp = client.post(
        "/api/students/practice/start",
        json={"topic_id": topic_id, "question_count": n},
        headers=_auth(token),
    )
    data = resp.json()["data"]
    return data["session_id"], data["questions"]


def _complete_practice(client: TestClient, token: str, topic_id: int, n: int = 2, correct: bool = True) -> dict:
    sid, questions = _practice_session(client, token, topic_id, n)
    for q in questions:
        client.post(
            f"/api/students/practice/{sid}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1 if correct else 0]["id"]},
            headers=_auth(token),
        )
    resp = client.post(f"/api/students/practice/{sid}/complete", headers=_auth(token))
    assert resp.status_code == 200
    return resp.json()["data"]


def _seed_questions(client: TestClient, admin_token: str, topic_id: int, count: int = 20) -> list[dict]:
    return [_question(client, admin_token, topic_id) for _ in range(count)]


def _gam_summary(client: TestClient, token: str) -> dict:
    resp = client.get("/api/gamification/me", headers=_auth(token))
    assert resp.status_code == 200
    return resp.json()["data"]


def _student_profile(db, email: str):
    from app.models.profile import StudentProfile
    from app.models.user import User

    user = db.query(User).filter_by(email=email).first()
    return db.query(StudentProfile).filter_by(user_id=user.id).first()


# ============================================================ XP & LEVELS

class TestXPAndLevels:
    def test_practice_awards_xp_via_ledger(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        token = _register(client, "xp1@example.com")
        _complete_practice(client, token, t["id"], n=2, correct=True)

        profile = _student_profile(db, "xp1@example.com")
        # 2 correct * 5 + 25 = 35
        assert profile.xp == 35
        assert profile.level == 1

        from app.models.gamification import XPTransaction
        txs = db.query(XPTransaction).filter_by(student_id=profile.id).all()
        assert len(txs) == 1
        assert txs[0].activity_type == "PRACTICE_COMPLETE"
        assert txs[0].xp_amount == 35

    def test_xp_summary_and_level_progress(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        token = _register(client, "xp2@example.com")
        _complete_practice(client, token, t["id"], n=15, correct=True)  # 100 XP → L2

        data = _gam_summary(client, token)
        assert data["xp"] == 100
        assert data["level"] == 2
        assert data["current_level_floor"] == 100
        assert data["next_level_xp"] == 250
        assert data["xp_to_next_level"] == 150

    def test_duplicate_xp_prevented_on_reference(self, client, db):
        from app.services.gamification import GamificationService

        token = _register(client, "xp3@example.com")
        profile = _student_profile(db, "xp3@example.com")
        gam = GamificationService(db)

        gam.award_xp(profile, 50, "TEST_EVENT", reference_id=42)
        gam.award_xp(profile, 50, "TEST_EVENT", reference_id=42)  # duplicate
        db.commit()
        db.refresh(profile)
        assert profile.xp == 50

    def test_level_curve_deterministic(self, client, db):
        from app.services.gamification import level_for_xp

        assert level_for_xp(0) == 1
        assert level_for_xp(99) == 1
        assert level_for_xp(100) == 2
        assert level_for_xp(250) == 3
        assert level_for_xp(99999) == len([0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200, 4000]) + (99999 - 4000) // 500

    def test_level_progress_no_dead_zone_at_table_edge(self, client, db):
        """Regression: level 11 (4000–4499 XP) previously reported
        floor=3500/ceiling=4000 → progress stuck at 100% with 0 XP to next."""
        from app.services.gamification import level_progress

        floor, ceiling = level_progress(4200)
        assert (floor, ceiling) == (4000, 4500)
        floor, ceiling = level_progress(4600)
        assert (floor, ceiling) == (4500, 5000)
        floor, ceiling = level_progress(4000)
        assert (floor, ceiling) == (4000, 4500)


# ============================================================ STREAKS

class TestStreaks:
    def test_streak_same_day_not_double_counted(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        token = _register(client, "streak1@example.com")

        _complete_practice(client, token, t["id"])
        _complete_practice(client, token, t["id"])

        profile = _student_profile(db, "streak1@example.com")
        assert profile.current_streak == 1

    def test_streak_first_activity(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        token = _register(client, "streak2@example.com")
        _complete_practice(client, token, t["id"])
        profile = _student_profile(db, "streak2@example.com")
        assert profile.current_streak == 1
        assert profile.longest_streak == 1
        assert profile.last_activity_date == datetime.now(timezone.utc).date()

    def test_streak_next_day_increments_missed_day_resets(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        token = _register(client, "streak3@example.com")
        _complete_practice(client, token, t["id"])

        # Simulate activity 2 days ago (gap) → streak resets to 1
        profile = _student_profile(db, "streak3@example.com")
        profile.last_activity_date = datetime.now(timezone.utc).date() - timedelta(days=2)
        profile.current_streak = 5
        db.commit()

        from app.services.gamification import GamificationService
        GamificationService(db).touch_streak(profile)
        db.commit()
        db.refresh(profile)
        assert profile.current_streak == 1

        # Consecutive day → increments
        profile.last_activity_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        profile.current_streak = 3
        db.commit()
        GamificationService(db).touch_streak(profile)
        db.commit()
        db.refresh(profile)
        assert profile.current_streak == 4


# ============================================================ MISSIONS

class TestMissions:
    def _seed_mission(self, db, mission_type: str = "ANSWER_QUESTION", target: int = 3, xp: int = 75) -> None:
        from app.models.mission import Mission

        db.add(Mission(title=f"Test mission {mission_type}", mission_type=mission_type,
                       target_value=target, xp_reward=xp, is_active=True))
        db.commit()

    def test_mission_progress_from_real_activity(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        self._seed_mission(db, "ANSWER_QUESTION", target=3, xp=75)

        token = _register(client, "mission1@example.com")
        _complete_practice(client, token, t["id"], n=2, correct=True)  # +2 progress
        _complete_practice(client, token, t["id"], n=2, correct=True)  # +2 → completes (clamped 3)

        resp = client.get("/api/gamification/missions", headers=_auth(token))
        missions = resp.json()["data"]
        m = next(x for x in missions if x["mission_type"] == "ANSWER_QUESTION")
        assert m["status"] == "COMPLETED"
        assert m["progress"] == 3

        # Mission XP awarded
        profile = _student_profile(db, "mission1@example.com")
        # sessions: 2*(2*5+25)=70, mission 75
        assert profile.xp == 70 + 75

    def test_mission_not_double_rewarded(self, client, db):
        from app.models.mission import StudentMission

        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        self._seed_mission(db, "COMPLETE_PRACTICE", target=1, xp=50)

        token = _register(client, "mission2@example.com")
        _complete_practice(client, token, t["id"], n=1)
        _complete_practice(client, token, t["id"], n=1)

        profile = _student_profile(db, "mission2@example.com")
        # practice XP: (5+25)*2 = 60, mission only once: 50
        assert profile.xp == 60 + 50

    def test_daily_missions_reset_next_day(self, client, db):
        """Date-scoped missions: completing today must NOT block tomorrow."""
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        self._seed_mission(db, "COMPLETE_PRACTICE", target=1, xp=50)

        token = _register(client, "mission3@example.com")
        _complete_practice(client, token, t["id"], n=1)  # day 1: mission done

        from datetime import timedelta as _td

        from app.models.mission import StudentMission

        profile = _student_profile(db, "mission3@example.com")
        xp_day1 = profile.xp
        assert xp_day1 == 30 + 50  # practice (5+25) + mission XP

        # Rewind today's rows to yesterday → simulate the day rolling over.
        yesterday = datetime.now(timezone.utc).date() - _td(days=1)
        db.query(StudentMission).filter_by(student_id=profile.id).update(
            {StudentMission.assigned_date: yesterday}
        )
        db.commit()

        # Day 2: the SAME activity completes the mission AGAIN (new day's row).
        _complete_practice(client, token, t["id"], n=1)
        db.refresh(profile)
        assert profile.xp == xp_day1 + 30 + 50  # fresh mission XP awarded

        # History: two dated rows exist for the same mission.
        rows = db.query(StudentMission).filter_by(student_id=profile.id).all()
        assert len(rows) == 2
        assert {r.assigned_date for r in rows} == {yesterday, datetime.now(timezone.utc).date()}


# ============================================================ BADGES

class TestBadges:
    def _seed_badge(self, db, criteria_type: str, criteria_value: int = 1, xp_reward: int = 50, name: str | None = None) -> None:
        from app.models.gamification import Badge

        db.add(Badge(name=name or f"Badge {criteria_type}", criteria_type=criteria_type,
                     criteria_value=criteria_value, xp_reward=xp_reward, is_active=True))
        db.commit()

    def test_first_assessment_badge(self, client, db):
        from app.models.assessment import Assessment, AssessmentQuestion

        admin = _create_admin(client, db)
        t = _topic(client, admin)
        self._seed_badge(db, "FIRST_ASSESSMENT", xp_reward=150)
        qs = [_question(client, admin, t["id"]) for _ in range(2)]

        token = _register(client, "badge1@example.com")
        _complete_practice(client, token, t["id"], n=1)  # no badge yet

        admin_user = db.query(__import__("app.models.user", fromlist=["User"]).User).filter_by(email="gam_admin@example.com").first()
        assessment = Assessment(title="B1", assessment_type="MOCK_TEST", duration_minutes=10,
                                question_count=2, created_by=admin_user.id, is_active=True)
        db.add(assessment)
        db.flush()
        for i, q in enumerate(qs, 1):
            db.add(AssessmentQuestion(assessment_id=assessment.id, question_id=q["id"], question_order=i))
        db.commit()

        resp = client.post(f"/api/assessments/{assessment.id}/start", headers=_auth(token))
        attempt_id = resp.json()["data"]["attempt_id"]
        client.post(f"/api/attempts/{attempt_id}/submit", headers=_auth(token))

        profile = _student_profile(db, "badge1@example.com")
        resp = client.get("/api/gamification/badges", headers=_auth(token))
        earned = resp.json()["data"]["earned"]
        assert any(b["name"] == "Badge FIRST_ASSESSMENT" for b in earned)
        # assessment 100 XP + badge 150 XP + practice 30 XP
        assert profile.xp == 100 + 150 + 30

    def test_badge_awarded_once(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        self._seed_badge(db, "PRACTICE_SESSIONS", criteria_value=1, xp_reward=50)

        token = _register(client, "badge2@example.com")
        _complete_practice(client, token, t["id"], n=1)
        xp_after_first = _student_profile(db, "badge2@example.com").xp
        _complete_practice(client, token, t["id"], n=1)
        xp_after_second = _student_profile(db, "badge2@example.com").xp

        # Only session XP differences (30 each); badge XP applied once
        assert xp_after_second - xp_after_first == 30

    def test_user_cannot_self_award_badge(self, client, db):
        self._seed_badge(db, "STREAK_DAYS", criteria_value=7)
        token = _register(client, "badge3@example.com")
        # No endpoint exists to create badges/award them; verify POSTing to
        # gamification endpoints cannot mutate badges.
        resp = client.post("/api/gamification/badges", json={"badge_id": 1}, headers=_auth(token))
        assert resp.status_code == 405  # method not allowed — no such route


# ============================================================ LEADERBOARD

class TestLeaderboard:
    def test_leaderboard_ranks_by_xp_with_ties(self, client, db):
        from app.services.gamification import GamificationService

        admin = _create_admin(client, db)
        a = _register(client, "lb_a@example.com")
        b = _register(client, "lb_b@example.com")
        c = _register(client, "lb_c@example.com")

        ga = GamificationService(db)
        pa, pb, pc = (_student_profile(db, e) for e in ("lb_a@example.com", "lb_b@example.com", "lb_c@example.com"))
        ga.award_xp(pa, 100, "MANUAL_SEED_A")
        ga.award_xp(pb, 100, "MANUAL_SEED_B")
        ga.award_xp(pc, 50, "MANUAL_SEED_C")
        db.commit()

        resp = client.get("/api/gamification/leaderboard?period=ALL_TIME", headers=_auth(a))
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        assert entries[0]["rank"] == 1
        assert entries[0]["xp"] == 100
        # Tie: both rank 1
        ranks = [e["rank"] for e in entries if e["xp"] == 100]
        assert ranks == [1, 1]
        # Third distinct score gets rank 3 (competition ranking)
        last = entries[-1]
        assert last["rank"] == 3

    def test_weekly_leaderboard_empty(self, client, db):
        admin = _create_admin(client, db)
        token = _register(client, "lb_week@example.com")
        resp = client.get("/api/gamification/leaderboard?period=WEEKLY", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["period_type"] == "WEEKLY"
        assert all(e["xp"] >= 0 for e in data["entries"])

    def test_leaderboard_requires_auth(self, client, db):
        resp = client.get("/api/gamification/leaderboard")
        assert resp.status_code == 401


# ============================================================ SECURITY

class TestGamificationSecurity:
    def test_no_client_xp_endpoint(self, client, db):
        """Students must NOT be able to POST arbitrary XP."""
        token = _register(client, "sec1@example.com")
        for path in ("/api/gamification/xp", "/api/gamification/award"):
            resp = client.post(path, json={"xp": 100000}, headers=_auth(token))
            assert resp.status_code in (404, 405), f"{path} should not exist"
        profile = _student_profile(db, "sec1@example.com")
        assert profile.xp == 0

    def test_activity_feed_visible_only_to_owner(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin)
        _seed_questions(client, admin, t["id"])
        owner = _register(client, "sec_owner@example.com")
        _complete_practice(client, owner, t["id"], n=1)

        other = _register(client, "sec_other@example.com")
        resp = client.get("/api/gamification/activity", headers=_auth(other))
        events = resp.json()["data"]
        # other has no activity
        assert events == []
