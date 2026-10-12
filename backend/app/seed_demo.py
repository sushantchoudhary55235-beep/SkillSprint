"""Demo dataset seeding (Feature Group 24).

Creates a deterministic, repeatable, clearly-synthetic dataset so the whole
platform can be demonstrated: student dashboard, aptitude, coding,
recommendations, roadmap, gamification, readiness; teacher analytics; admin.

    python -m app.seed_demo

Properties (per the master prompt's demo-mode rules):
- DETERMINISTIC: fixed emails, fixed question content, fixed outcome pattern
  (a repeating correct/incorrect sequence), fixed dates relative to today.
- IDEMPOTENT: every step checks for existing rows first; re-running updates
  nothing and duplicates nothing (safe to run on every demo refresh).
- ISOLATED: all demo users share the email domain ``@demo.skillsprint.test``
  and demo questions carry source_type="DEMO", so production data can be
  told apart (and demo users deactivated/deleted) independently.
- NO REAL CREDENTIALS: demo passwords are publicly documented placeholders.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

DEMO_DOMAIN = "@demo.skillsprint.test"
DEMO_PASSWORD = "Demo#Pass123"

NUM_TOPICS = [
    ("Percentages", "quantitative"),
    ("Profit and Loss", "quantitative"),
    ("Time and Work", "quantitative"),
    ("Probability", "quantitative"),
    ("Number Series", "logical"),
    ("Reading Comprehension", "verbal"),
]

CODING_TOPICS = [
    ("Arrays", "coding"),
    ("Strings", "coding"),
    ("Dynamic Programming", "coding"),
]

DEMO_CODING_PROBLEMS = [
    ("Two Sum", "arrays", "EASY"),
    ("Reverse a String", "strings", "EASY"),
    ("Climbing Stairs", "dynamic programming", "MEDIUM"),
]


def _user(db, name, role, password=DEMO_PASSWORD, extra_profile=None):
    """Get-or-create a demo user. Returns (user, profile, created)."""
    from app.models.user import User

    email = name.lower().replace(" ", ".") + DEMO_DOMAIN
    existing = db.query(User).filter_by(email=email).first()
    if existing is not None:
        profile = existing.student_profile or existing.teacher_profile
        return existing, profile, False

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    profile = None
    if role == "student":
        from app.models.profile import StudentProfile

        # Deterministic student ID derived from the demo sequence.
        seq = db.query(User).filter(User.email.like(f"%{DEMO_DOMAIN}")).count() + 1
        from app.models.profile import StudentProfile as SP

        profile = SP(
            student_id=f"SSDEMO{seq:04d}",
            readiness_score=0,
            xp=0,
            level=1,
            current_streak=0,
            longest_streak=0,
        )
        user.student_profile = profile
    elif role == "teacher":
        from app.models.profile import TeacherProfile

        profile = TeacherProfile(department="Demo Department")
        user.teacher_profile = profile
    db.add(user)
    db.flush()
    return user, profile, True


def seed_demo() -> None:
    from app.models.assessment import Answer, Attempt
    from app.models.coding import CodingProblem, CodeSubmission, TestCase
    from app.models.content import Company, Topic
    from app.models.gamification import XPTransaction
    from app.models.practice import PracticeAnswer, PracticeSession
    from app.models.profile import StudentProfile
    from app.models.question import Question, QuestionOption
    from app.models.user import User

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        print("Seeding demo dataset (deterministic, idempotent)...")

        # ---------------- topics & companies (shared catalogue) ----------------
        for name, category in NUM_TOPICS + CODING_TOPICS:
            if db.query(Topic).filter_by(name=name).first() is None:
                db.add(Topic(name=name, category=category))
        db.flush()
        if db.query(Company).filter_by(name="DemoCorp").first() is None:
            db.add(Company(name="DemoCorp", description="Synthetic demo company (not a real employer)"))
        db.flush()

        topics = {t.name: t for t in db.query(Topic).filter(Topic.name.in_(
            [n for n, _ in NUM_TOPICS + CODING_TOPICS])).all()}

        # ---------------- demo questions (DEMO source, approved) ----------------
        # Fixed content: 4 questions per topic with known correct option "b".
        outcomes = [True, True, False, True, False, False, True, False]  # ~50%
        for name, _cat in NUM_TOPICS:
            topic = topics[name]
            have = db.query(Question).filter_by(topic_id=topic.id, source_type="DEMO").count()
            for i in range(have, 4):
                q = Question(
                    question_text=f"[DEMO] {name} question {i + 1}: what is 2+{i}?",
                    question_type="MCQ",
                    topic_id=topic.id,
                    difficulty=("easy" if i < 2 else "medium"),
                    explanation="[DEMO] Explanation: count the items in the question.",
                    source_type="DEMO",
                    status="approved",
                )
                db.add(q)
                db.flush()
                for j, (text, correct) in enumerate(
                    [("2", False), (str(2 + i), True), ("9", False), ("11", False)], 1
                ):
                    db.add(QuestionOption(
                        question_id=q.id, option_text=text, option_order=j, is_correct=correct
                    ))
        db.flush()

        # ---------------- demo coding problems ----------------
        arrays_topic = topics["Arrays"]
        problems_by_title = {}
        for title, _kw, diff in DEMO_CODING_PROBLEMS:
            p = db.query(CodingProblem).filter_by(title=f"[DEMO] {title}").first()
            if p is None:
                p = CodingProblem(
                    title=f"[DEMO] {title}",
                    description=f"[DEMO] Synthetic problem used for demos only. Solve {title.lower()}.",
                    topic_id=arrays_topic.id,
                    difficulty=diff,
                    input_format="[DEMO] space-separated integers",
                    output_format="[DEMO] single integer",
                    constraints="[DEMO] n ≤ 1000",
                )
                db.add(p)
                db.flush()
                db.add(TestCase(problem_id=p.id, input_data="1 2 3", expected_output="6", is_hidden=False))
                db.add(TestCase(problem_id=p.id, input_data="4 5", expected_output="9", is_hidden=True))
            problems_by_title[title] = p
        db.flush()

        # ---------------- users ----------------
        _, admin_user, _ = _user(db, "Demo Admin", "admin")
        teacher_user, teacher_profile, _ = _user(db, "Demo Teacher", "teacher")

        student_specs = [
            ("Demo Aarav", outcomes[0:8]),      # decent accuracy
            ("Demo Meera", [False, True, False, False, True, False, False, True]),  # weak
            ("Demo Rohan", [True, True, True, True, True, True, True, True]),       # strong
        ]
        students = []
        for name, pattern in student_specs:
            _, profile, _created = _user(db, name, "student")
            students.append((profile, pattern))

        # Associate students with the demo teacher.
        from app.models.content import TeacherStudent

        teacher = teacher_profile
        for profile, _ in students:
            link = db.query(TeacherStudent).filter_by(
                teacher_id=teacher.id, student_id=profile.id
            ).first()
            if link is None:
                db.add(TeacherStudent(teacher_id=teacher.id, student_id=profile.id, status="ACTIVE"))
        db.flush()

        # ---------------- practice activity (deterministic history) ----------------
        # 8 days of activity: each day one COMPLETED topic session of 4 answers.
        for profile, pattern in students:
            if profile.xp > 0:
                continue  # already seeded (idempotent)
            user = db.get(User, profile.user_id)
            for day in range(8):
                started = now - timedelta(days=7 - day)
                session = PracticeSession(
                    student_id=profile.id,
                    mode="TOPIC",
                    topic_id=topics["Percentages"].id,
                    difficulty="medium",
                    question_count=4,
                    status="COMPLETED",
                    created_at=started,
                    completed_at=started + timedelta(minutes=9),
                    total_time_seconds=540,
                )
                db.add(session)
                db.flush()
                qs = db.query(Question).filter_by(topic_id=topics["Percentages"].id).limit(4).all()
                correct = 0
                for i, q in enumerate(qs):
                    ok = pattern[(day + i) % len(pattern)]
                    if ok:
                        correct += 1
                    db.add(PracticeAnswer(
                        session_id=session.id,
                        question_id=q.id,
                        selected_option_id=db.query(QuestionOption)
                            .filter_by(question_id=q.id, is_correct=ok).first().id,
                        is_correct=ok,
                        time_taken_seconds=40 + i * 5,
                        created_at=started + timedelta(minutes=i + 1),
                    ))
                session.correct_count = correct
                session.incorrect_count = 4 - correct
                session.score = round(correct / 4 * 100)
                xp = correct * 5 + 25
                db.add(XPTransaction(
                    student_id=profile.id,
                    activity_type="PRACTICE_COMPLETE",
                    reference_id=session.id,
                    xp_amount=xp,
                    description=f"[DEMO] Practice session #{session.id}",
                    created_at=started + timedelta(minutes=10),
                ))
                profile.xp += xp
                profile.level = 1 + profile.xp // 100
                # Streak: every activity day is consecutive by construction.
                profile.current_streak = day + 1 if day < 8 else profile.current_streak
                profile.longest_streak = max(profile.longest_streak, profile.current_streak)
                profile.last_activity_date = started.date()
        db.flush()

        # ---------------- one coding acceptance for Aarav ----------------
        aarav = students[0][0]
        if db.query(CodeSubmission).filter_by(student_id=aarav.id).count() == 0:
            problem = problems_by_title["Two Sum"]
            db.add(CodeSubmission(
                student_id=aarav.id,
                problem_id=problem.id,
                language="python",
                source_code="# [DEMO] accepted solution\nprint(sum(map(int, input().split())))",
                status="ACCEPTED",
                passed_test_cases=2,
                total_test_cases=2,
                created_at=now - timedelta(days=3),
            ))
            aarav_readiness = aarav.readiness_score
        db.flush()

        # Recompute readiness with the real engine so demo dashboards look right.
        from app.services.readiness import sync_profile_readiness

        for profile, _ in students:
            sync_profile_readiness(db, profile)
        db.commit()

        print("  + demo admin:      admin" + DEMO_DOMAIN)
        print("  + demo teacher:    teacher" + DEMO_DOMAIN)
        print("  + demo students:   aarav/meera/rohan" + DEMO_DOMAIN)
        print(f"  + demo password:   {DEMO_PASSWORD}  (public placeholder — never reuse)")
        print("Demo seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
