"""Model-layer tests: constraints, relationships, and cascade rules."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Answer,
    Assessment,
    Attempt,
    Company,
    Question,
    QuestionOption,
    StudentProfile,
    TeacherProfile,
    TeacherStudent,
    Topic,
    User,
)


def test_user_unique_email(db):
    db.add(User(name="A", email="a@x.com", password_hash="h", role="student"))
    db.commit()
    db.add(User(name="B", email="a@x.com", password_hash="h", role="teacher"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_user_unique_student_id(db):
    db.add(User(name="A", email="a@x.com", password_hash="h", role="student"))
    db.commit()
    db.add(StudentProfile(user_id=1, student_id="SS202600001"))
    db.commit()
    db.add(User(name="B", email="b@x.com", password_hash="h", role="student"))
    db.commit()
    db.add(StudentProfile(user_id=2, student_id="SS202600001"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_teacher_student_relationship_unique(db):
    u1 = User(name="T", email="t@x.com", password_hash="h", role="teacher")
    u2 = User(name="S", email="s@x.com", password_hash="h", role="student")
    db.add_all([u1, u2])
    db.commit()
    tp = TeacherProfile(user_id=u1.id)
    sp = StudentProfile(user_id=u2.id, student_id="SS202600002")
    db.add_all([tp, sp])
    db.commit()
    db.add(TeacherStudent(teacher_id=tp.id, student_id=sp.id, status="ACTIVE"))
    db.commit()
    db.add(TeacherStudent(teacher_id=tp.id, student_id=sp.id, status="ACTIVE"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_deleting_user_cascades_profile(db):
    u = User(name="A", email="a@x.com", password_hash="h", role="student")
    db.add(u)
    db.commit()
    db.add(StudentProfile(user_id=u.id, student_id="SS202600003"))
    db.commit()
    db.delete(u)
    db.commit()
    assert db.query(StudentProfile).count() == 0


def test_topic_company_question_chain(db):
    topic = Topic(name="Percentages", category="Quantitative")
    company = Company(name="TCS")
    db.add_all([topic, company])
    db.commit()
    q = Question(
        question_text="20% of 150?", topic_id=topic.id, company_id=company.id, difficulty="EASY"
    )
    db.add(q)
    db.commit()
    db.add_all(
        [
            QuestionOption(question_id=q.id, option_text="20", option_order=1, is_correct=False),
            QuestionOption(question_id=q.id, option_text="30", option_order=2, is_correct=True),
        ]
    )
    db.commit()
    assert q.options[1].is_correct is True


def test_attempt_deletion_cascades_answers(db):
    topic = Topic(name="Probability", category="Quantitative")
    user = User(name="A", email="a@x.com", password_hash="h", role="student")
    db.add_all([topic, user])
    db.commit()
    sp = StudentProfile(user_id=user.id, student_id="SS202600004")
    asm = Assessment(title="Mock 1", assessment_type="MOCK_TEST", duration_minutes=30)
    db.add_all([sp, asm])
    db.commit()
    q = Question(question_text="Q?", topic_id=topic.id, difficulty="EASY")
    db.add(q)
    db.commit()
    attempt = Attempt(student_id=sp.id, assessment_id=asm.id, status="COMPLETED")
    db.add(attempt)
    db.commit()
    db.add(
        Answer(
            attempt_id=attempt.id, question_id=q.id, selected_option_id=None, is_correct=False
        )
    )
    db.commit()
    db.delete(attempt)
    db.commit()
    assert db.query(Answer).count() == 0
