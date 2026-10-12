"""Seed required production/dev data: admin user, topics, companies, badges, missions.

Run:  python -m app.seed
Idempotent: existing rows are skipped (safe to run on every deploy).

Seeds (docs/Phases.md Phase 16 §3 — "seed required data"):
- Admin user (from ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD env, or defaults)
- Core aptitude topics
- Placement companies
- Badge catalogue
- Daily missions
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.content import Company, Topic  # noqa: E402
from app.models.gamification import Badge  # noqa: E402
from app.models.mission import Mission  # noqa: E402
from app.models.user import User  # noqa: E402

TOPICS = [
    ("Percentages", "quantitative"),
    ("Profit and Loss", "quantitative"),
    ("Time Speed and Distance", "quantitative"),
    ("Time and Work", "quantitative"),
    ("Permutation and Combination", "quantitative"),
    ("Probability", "quantitative"),
    ("Number Series", "logical"),
    ("Seating Arrangements", "logical"),
    ("Blood Relations", "logical"),
    ("Synonyms", "verbal"),
    ("Antonyms", "verbal"),
    ("Reading Comprehension", "verbal"),
]

COMPANIES = [
    ("TCS", "Tata Consultancy Services — aptitude + coding focused drives"),
    ("Infosys", "Infosys placement pattern"),
    ("Wipro", "Wipro national talent hunt pattern"),
    ("Accenture", "Accenture placement pattern"),
    ("Cognizant", "Cognizant GenC pattern"),
    ("Capgemini", "Capgemini placement pattern"),
]

BADGES = [
    ("First Steps", "Complete your first assessment", "🎯", "FIRST_ASSESSMENT", 1, 50),
    ("Persistent", "Answer 50 questions", "📚", "QUESTIONS_ANSWERED", 50, 50),
    ("Century", "Answer 100 questions", "💯", "QUESTIONS_ANSWERED", 100, 75),
    ("On Fire", "Reach a 7-day streak", "🔥", "STREAK_DAYS", 7, 50),
    ("Unstoppable", "Reach a 30-day streak", "⚡", "STREAK_DAYS", 30, 150),
    ("Perfect Score", "Score 100 on an assessment", "🏆", "PERFECT_SCORE", 100, 100),
    ("Hello World", "Solve your first coding problem", "💻", "CODING_SOLVED", 1, 50),
    ("Code Ninja", "Solve 5 coding problems", "🥷", "CODING_SOLVED", 5, 100),
    ("Practice Makes Perfect", "Complete 5 practice sessions", "🏋️", "PRACTICE_SESSIONS", 5, 50),
    ("First Practice", "Complete your first practice session", "🚀", "PRACTICE_SESSIONS", 1, 25),
    ("Ten Down", "Answer 10 questions", "✏️", "QUESTIONS_ANSWERED", 10, 25),
    ("Problem Solver", "Solve 10 coding problems", "🧩", "CODING_SOLVED", 10, 150),
    ("Mock Ready", "Complete 3 assessments", "📋", "FIRST_ASSESSMENT", 3, 75),
]

MISSIONS = [
    ("Daily Warm-up", "Answer 10 questions today", "DAILY", "ANSWER_QUESTION", 10, 30),
    ("Complete a Practice", "Finish 1 practice session today", "DAILY", "COMPLETE_PRACTICE", 1, 20),
    ("Daily Quiz", "Complete today's daily quiz", "DAILY", "COMPLETE_DAILY_QUIZ", 1, 25),
]


def seed() -> None:
    db = SessionLocal()
    try:
        # ---- Admin user ----
        admin_email = os.environ.get("ADMIN_SEED_EMAIL", "admin@skillsprint.com")
        admin_password = os.environ.get("ADMIN_SEED_PASSWORD", "ChangeMe!123")
        if db.query(User).filter_by(email=admin_email).first() is None:
            db.add(User(name="Admin", email=admin_email,
                        password_hash=hash_password(admin_password), role="admin"))
            print(f"  + admin user {admin_email}")
        else:
            print(f"  = admin user {admin_email} exists")

        # ---- Topics ----
        for name, category in TOPICS:
            if db.query(Topic).filter_by(name=name).first() is None:
                db.add(Topic(name=name, category=category))
                print(f"  + topic {name}")
        db.commit()

        # ---- Companies ----
        for name, description in COMPANIES:
            if db.query(Company).filter_by(name=name).first() is None:
                db.add(Company(name=name, description=description))
                print(f"  + company {name}")
        db.commit()

        # ---- Badges ----
        for name, description, icon, criteria_type, criteria_value, xp in BADGES:
            if db.query(Badge).filter_by(name=name).first() is None:
                db.add(Badge(name=name, description=description, icon=icon,
                             criteria_type=criteria_type, criteria_value=criteria_value,
                             xp_reward=xp, is_active=True))
                print(f"  + badge {name}")
        db.commit()

        # ---- Missions ----
        for title, description, mtype, event, target, xp in MISSIONS:
            if db.query(Mission).filter_by(title=title).first() is None:
                db.add(Mission(title=title, description=description, mission_type=event,
                               target_value=target, xp_reward=xp, is_active=True))
                print(f"  + mission {title}")
        db.commit()

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
