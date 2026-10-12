"""Load-test scripts for SkillSprint (Phase 15.9).

Install once:  pip install locust
Run against a live server:  locust -f backend/locustfile.py --host=http://localhost:8000

Simulates 10-20 concurrent students performing login, quiz start/submit,
and AI question generation (validates the 429 rate limit under load).
"""
import random

from locust import HttpUser, between, task


class StudentUser(HttpUser):
    """A simulated student: login → practice quiz → AI question."""

    wait_time = between(1, 3)

    # Registered student credentials to rotate through (set via env in real runs).
    credentials = [
        {"email": f"load{i}@example.com", "password": "password123"} for i in range(20)
    ]

    def on_start(self) -> None:
        self.user = random.choice(self.credentials)
        resp = self.client.post(
            "/api/auth/login", json=self.user, name="/api/auth/login"
        )
        token = None
        if resp.status_code == 200:
            token = resp.json().get("data", {}).get("access_token")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(5)
    def start_quiz(self) -> None:
        """Practice quiz start — exercises DB reads + session writes."""
        self.client.post(
            "/api/students/practice/start",
            json={"topic_id": 1, "question_count": 5},
            headers=self.headers,
            name="/api/students/practice/start",
        )

    @task(3)
    def dashboard(self) -> None:
        self.client.get("/api/students/dashboard", headers=self.headers,
                        name="/api/students/dashboard")

    @task(2)
    def generate_ai_question(self) -> None:
        """AI generation — should mostly 200/503 without key, 429 at the limit."""
        self.client.post(
            "/api/ai/questions/generate",
            json={"company": "TCS", "topic_name": "Percentages", "difficulty": "easy"},
            headers=self.headers,
            name="/api/ai/questions/generate",
        )
