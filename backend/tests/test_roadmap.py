"""Phase 9 tests: Personalized Roadmap."""
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
    client.post("/api/auth/register/student",
                json={"name": email.split("@")[0], "email": email, "password": "password123"})
    return _login(client, email)


def _create_admin(client: TestClient, db, email: str = "road_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    return _login(client, email, "adminpass123")


def _topic(client: TestClient, admin_token: str, name: str, category: str = "quantitative") -> dict:
    resp = client.post("/api/admin/topics", json={"name": name, "category": category}, headers=_auth(admin_token))
    assert resp.status_code == 201
    return resp.json()["data"]


def _question(client: TestClient, admin_token: str, topic_id: int) -> dict:
    payload = {
        "question_text": f"Q for topic {topic_id}",
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


def _practice(client: TestClient, token: str, topic_id: int, questions: list[dict], outcomes: list[bool]) -> None:
    resp = client.post(
        "/api/students/practice/start",
        json={"topic_id": topic_id, "question_count": len(questions)},
        headers=_auth(token),
    )
    sid = resp.json()["data"]["session_id"]
    for q, ok in zip(questions, outcomes):
        client.post(
            f"/api/students/practice/{sid}/answer",
            json={"question_id": q["id"], "selected_option_id": q["options"][1 if ok else 0]["id"]},
            headers=_auth(token),
        )
    client.post(f"/api/students/practice/{sid}/complete", headers=_auth(token))


def _roadmap(client: TestClient, token: str) -> dict:
    resp = client.get("/api/roadmap/me", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestRoadmapGeneration:
    def test_new_student_empty_roadmap(self, client, db):
        token = _register(client, "road_empty@example.com")
        data = _roadmap(client, token)
        assert data["items"] == []
        assert data["overall_progress"] == 0

    def test_roadmap_orders_weak_first(self, client, db):
        admin = _create_admin(client, db)
        t_weak = _topic(client, admin, "Weak Topic X")
        t_strong = _topic(client, admin, "Strong Topic Y")
        wq = [_question(client, admin, t_weak["id"]) for _ in range(4)]
        sq = [_question(client, admin, t_strong["id"]) for _ in range(4)]

        token = _register(client, "road_order@example.com")
        _practice(client, token, t_weak["id"], wq, [False] * 4)     # weak → HIGH
        _practice(client, token, t_strong["id"], sq, [True] * 4)    # strong → LOW

        data = _roadmap(client, token)
        assert len(data["items"]) == 2
        assert data["items"][0]["topic_id"] == t_weak["id"]
        assert data["items"][0]["priority"] == "HIGH"
        assert data["items"][0]["status"] == "NOT_STARTED"
        assert data["items"][1]["topic_id"] == t_strong["id"]
        assert data["items"][1]["priority"] == "LOW"
        assert "topic test" in data["items"][1]["reason"].lower()

    def test_roadmap_has_targets_and_progress_fields(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Targets Topic")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        token = _register(client, "road_targets@example.com")
        _practice(client, token, t["id"], qs, [True, False, False, False])  # 25% weak

        data = _roadmap(client, token)
        item = data["items"][0]
        assert item["target_accuracy"] == 60.0
        assert item["reason"]
        assert item["sequence_order"] == 1
        assert item["topic_name"] == "Targets Topic"

    def test_roadmap_regenerates_after_improvement(self, client, db):
        """Roadmap must not remain static: after new assessment → snapshot → stale → rebuild."""
        admin = _create_admin(client, db)
        t_weak = _topic(client, admin, "Stale Weak")
        t_new_weak = _topic(client, admin, "Fresh Weak")
        wq = [_question(client, admin, t_weak["id"]) for _ in range(4)]
        nq = [_question(client, admin, t_new_weak["id"]) for _ in range(4)]

        token = _register(client, "road_stale@example.com")
        _practice(client, token, t_weak["id"], wq, [False] * 4)
        first = _roadmap(client, token)
        assert first["items"][0]["topic_id"] == t_weak["id"]

        # Simulate a new assessment snapshot created *after* the roadmap was
        # generated (SQLite CURRENT_TIMESTAMP has second precision, so we make
        # the ordering explicit).
        from datetime import datetime, timedelta, timezone

        from app.models.performance import PerformanceSnapshot

        profile = _student_profile(db, token)
        snap = PerformanceSnapshot(
            student_id=profile.id,
            overall_score=10,
            accuracy=10,
            created_at=datetime.now(timezone.utc) + timedelta(seconds=10),
        )
        db.add(snap)
        db.commit()

        # Student also practices the new topic poorly
        _practice(client, token, t_new_weak["id"], nq, [False] * 4)

        second = _roadmap(client, token)
        # Roadmap was rebuilt (generated_at newer) and now includes both topics,
        # weak topics ordered by accuracy
        topic_ids = [i["topic_id"] for i in second["items"]]
        assert t_weak["id"] in topic_ids
        assert t_new_weak["id"] in topic_ids
        assert second["items"][0]["priority"] == "HIGH"

    def test_manual_generation_endpoint(self, client, db):
        token = _register(client, "road_gen@example.com")
        resp = client.post("/api/roadmap/generate", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "My Placement Roadmap"


class TestRoadmapItemUpdate:
    def _setup_one_item(self, client, db):
        admin = _create_admin(client, db)
        t = _topic(client, admin, "Update Topic")
        qs = [_question(client, admin, t["id"]) for _ in range(4)]
        token = _register(client, f"road_upd{t['id']}@example.com")
        _practice(client, token, t["id"], qs, [False] * 4)
        data = _roadmap(client, token)
        return token, data["items"][0]["id"]

    def test_mark_in_progress(self, client, db):
        token, item_id = self._setup_one_item(client, db)
        resp = client.patch(f"/api/roadmap/items/{item_id}?status=IN_PROGRESS", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "IN_PROGRESS"

    def test_mark_completed_updates_progress(self, client, db):
        token, item_id = self._setup_one_item(client, db)
        resp = client.patch(f"/api/roadmap/items/{item_id}?status=COMPLETED", headers=_auth(token))
        assert resp.status_code == 200
        data = _roadmap(client, token)
        assert data["overall_progress"] == 100.0

    def test_invalid_status_rejected(self, client, db):
        token, item_id = self._setup_one_item(client, db)
        resp = client.patch(f"/api/roadmap/items/{item_id}?status=HACKED", headers=_auth(token))
        assert resp.status_code == 422

    def test_other_students_item_denied(self, client, db):
        _token, item_id = self._setup_one_item(client, db)
        other = _register(client, "road_other@example.com")
        resp = client.patch(f"/api/roadmap/items/{item_id}?status=COMPLETED", headers=_auth(other))
        assert resp.status_code == 404


def _student_profile(db, token: str):
    from app.models.profile import StudentProfile

    return db.query(StudentProfile).order_by(StudentProfile.id.desc()).first()
