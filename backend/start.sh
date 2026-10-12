"""Render/Deployment start script for SkillSprint backend.

Runs Alembic migrations before booting uvicorn so the schema is always
current (Phase 16 §2: "run database migrations on the production database
before starting").
"""
import os
import subprocess
import sys


def main() -> None:
    skip = os.environ.get("SKIP_MIGRATIONS", "").lower() in ("1", "true", "yes")
    if not skip:
        print("Running database migrations (alembic upgrade head)…")
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    else:
        print("SKIP_MIGRATIONS set — skipping alembic upgrade.")

    port = os.environ.get("PORT", "8000")
    workers = os.environ.get("WEB_CONCURRENCY", "2")
    subprocess.run(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", port,
            "--workers", workers,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
