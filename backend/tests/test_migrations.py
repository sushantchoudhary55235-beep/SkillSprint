"""Migration integrity: alembic upgrade head builds the full schema from scratch."""
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_alembic_upgrade_creates_all_tables(tmp_path):
    import os

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tmp_path}/mig_test.db"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr

    import sqlite3

    con = sqlite3.connect(tmp_path / "mig_test.db")
    tables = {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    con.close()

    expected = {
        "users", "student_profiles", "teacher_profiles", "teacher_students",
        "topics", "companies", "questions", "question_options",
        "assessments", "assessment_questions", "attempts", "answers",
        "topic_performance", "performance_snapshots",
        "roadmaps", "roadmap_items", "recommendations",
        "missions", "student_missions",
        "xp_transactions", "badges", "student_badges",
        "leaderboards", "leaderboard_entries",
        "coding_problems", "test_cases", "code_submissions",
        "activity_events",
    }
    missing = expected - tables
    assert not missing, f"Tables missing from migration: {missing}"
