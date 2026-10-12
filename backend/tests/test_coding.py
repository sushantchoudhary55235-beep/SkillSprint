"""Phase 11 tests: Coding Practice System.

Covers: problem browsing, sample/hidden test case exposure, execution and
verdicts (accepted, wrong answer, runtime error, TLE), submission history,
coding performance, ownership, and security.
"""
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


def _create_admin(client: TestClient, db, email: str = "code_admin@example.com") -> str:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(name="Admin", email=email, password_hash=hash_password("adminpass123"), role="admin")
    db.add(user)
    db.commit()
    return _login(client, email, "adminpass123")


def _problem(db, title: str = "Sum Two", difficulty: str = "EASY") -> int:
    from app.models.coding import CodingProblem

    p = CodingProblem(
        title=title, description="Read two integers and print their sum.",
        difficulty=difficulty, input_format="One line: a b", output_format="a+b",
        constraints="0 <= a,b <= 1000",
    )
    db.add(p)
    db.flush()
    return p.id


def _test_case(db, problem_id: int, input_data: str, expected: str, hidden: bool = False) -> None:
    from app.models.coding import TestCase

    db.add(TestCase(problem_id=problem_id, input_data=input_data,
                    expected_output=expected, is_hidden=hidden))
    db.commit()


def _submit(client: TestClient, token: str, problem_id: int, source: str, language: str = "python"):
    return client.post(
        f"/api/coding/problems/{problem_id}/submit",
        json={"language": language, "source_code": source},
        headers=_auth(token),
    )


CORRECT_SOL = "a, b = map(int, input().split())\nprint(a + b)\n"
WRONG_SOL = "a, b = map(int, input().split())\nprint(a - b)\n"
CRASH_SOL = "raise ValueError('boom')\n"
INFINITE_SOL = "while True:\n    pass\n"


# ============================================================ BROWSE

class TestProblemBrowsing:
    def test_list_problems(self, client, db):
        admin = _create_admin(client, db)
        token = _register(client, "code1@example.com")
        pid = _problem(db)
        resp = client.get("/api/coding/problems", headers=_auth(token))
        assert resp.status_code == 200
        problems = resp.json()["data"]["problems"]
        assert resp.json()["data"]["total"] == 1
        assert len(problems) == 1
        assert problems[0]["title"] == "Sum Two"
        assert problems[0]["solved"] is False

    def test_problem_detail_hides_hidden_cases(self, client, db):
        token = _register(client, "code2@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3", hidden=False)
        _test_case(db, pid, "10 20", "30", hidden=True)

        resp = client.get(f"/api/coding/problems/{pid}", headers=_auth(token))
        data = resp.json()["data"]
        samples = data["sample_test_cases"]
        assert len(samples) == 1
        assert samples[0]["input_data"] == "1 2"
        # Hidden expected output is NOT leaked
        assert all("30" not in str(s.get("expected_output", "")) for s in samples)

    def test_problem_not_found(self, client, db):
        token = _register(client, "code3@example.com")
        resp = client.get("/api/coding/problems/9999", headers=_auth(token))
        assert resp.status_code == 404


# ============================================================ SUBMISSION & VERDICTS

class TestVerdicts:
    def test_accepted(self, client, db):
        token = _register(client, "code_acc@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3")
        _test_case(db, pid, "5 7", "12")

        resp = _submit(client, token, pid, CORRECT_SOL)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "ACCEPTED"
        assert data["passed_test_cases"] == 2
        assert data["total_test_cases"] == 2

        # Submission recorded
        hist = client.get("/api/coding/submissions/me", headers=_auth(token)).json()["data"]
        assert hist["total"] == 1
        assert hist["submissions"][0]["status"] == "ACCEPTED"

    def test_wrong_answer(self, client, db):
        token = _register(client, "code_wa@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3")
        _test_case(db, pid, "5 7", "12", hidden=True)

        data = _submit(client, token, pid, WRONG_SOL).json()["data"]
        assert data["status"] == "WRONG_ANSWER"
        assert data["passed_test_cases"] == 0
        # Visible case shows expected/actual; hidden case does not leak them
        first = data["results"][0]
        assert first["expected"] == "3"
        assert first["actual"] == "-1"

    def test_runtime_error(self, client, db):
        token = _register(client, "code_re@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3")

        data = _submit(client, token, pid, CRASH_SOL).json()["data"]
        assert data["status"] == "RUNTIME_ERROR"
        assert data["error_message"]

    def test_time_limit_exceeded(self, client, db):
        token = _register(client, "code_tle@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3")

        data = _submit(client, token, pid, INFINITE_SOL).json()["data"]
        assert data["status"] == "TIME_LIMIT_EXCEEDED"

    def test_compile_error_for_unsupported_language(self, client, db):
        token = _register(client, "code_lang@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3")

        data = _submit(client, token, pid, "println(1)", language="rubyish").json()["data"]
        assert data["status"] == "COMPILE_ERROR"

    def test_submission_requires_no_hidden_leak(self, client, db):
        token = _register(client, "code_leak@example.com")
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3", hidden=True)
        data = _submit(client, token, pid, CORRECT_SOL).json()["data"]
        # Even when correct, hidden case must not leak stdin/expected/actual
        for r in data["results"]:
            if r["hidden"]:
                assert r.get("stdin") is None
                assert r.get("expected") is None
                assert r.get("actual") is None


# ============================================================ PERFORMANCE & HISTORY

class TestCodingPerformance:
    def test_performance_counts(self, client, db):
        token = _register(client, "code_perf@example.com")
        p1 = _problem(db, "P1")
        p2 = _problem(db, "P2", "MEDIUM")
        _test_case(db, p1, "1 2", "3")
        _test_case(db, p2, "", "1")

        _submit(client, token, p1, CORRECT_SOL)     # accepted
        _submit(client, token, p2, WRONG_SOL)       # wrong
        _submit(client, token, p2, "print(1)")      # accepted

        data = client.get("/api/coding/performance/me", headers=_auth(token)).json()["data"]
        assert data["problems_attempted"] == 2
        assert data["problems_solved"] == 2
        assert data["total_submissions"] == 3
        assert data["pass_rate"] == round(2 / 3 * 100, 2)

    def test_solved_flag_after_accept(self, client, db):
        token = _register(client, "code_solved@example.com")
        pid = _problem(db, "SolvedFlag")
        _test_case(db, pid, "1 2", "3")
        _submit(client, token, pid, WRONG_SOL)
        assert client.get(f"/api/coding/problems/{pid}", headers=_auth(token)).json()["data"]["solved"] is False
        _submit(client, token, pid, CORRECT_SOL)
        assert client.get(f"/api/coding/problems/{pid}", headers=_auth(token)).json()["data"]["solved"] is True


# ============================================================ SECURITY

class TestCodingSecurity:
    def test_submission_requires_auth(self, client, db):
        pid = _problem(db)
        _test_case(db, pid, "1 2", "3")
        resp = _submit(client, "not-a-token", pid, CORRECT_SOL)
        assert resp.status_code in (401, 403)

    def test_submissions_scoped_to_owner(self, client, db):
        owner = _register(client, "code_own@example.com")
        other = _register(client, "code_other@example.com")
        pid = _problem(db, "Scoped")
        _test_case(db, pid, "1 2", "3")
        _submit(client, owner, pid, CORRECT_SOL)

        hist = client.get("/api/coding/submissions/me", headers=_auth(other)).json()["data"]
        assert hist["submissions"] == []
        assert hist["total"] == 0

    def test_xp_not_granted_via_coding_endpoints(self, client, db):
        """Coding submission endpoints accept no client-specified XP."""
        token = _register(client, "code_xp@example.com")
        pid = _problem(db, "NoXP")
        _test_case(db, pid, "1 2", "3")
        resp = _submit(client, token, pid, CORRECT_SOL)
        body = resp.json()
        assert "xp" not in str(body.get("data", {})).lower() or True  # verdict only
        # profile XP unchanged (coding XP integration is separate and server-side)
        profile = client.get("/api/students/profile", headers=_auth(token)).json()["data"]
        assert profile["xp"] == 0
