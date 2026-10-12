"""Placement-readiness engine (Feature Group 9 — explained, non-black-box).

Deterministic, documented formula. Every component is computed from real
student activity in the database; nothing is AI-generated or client-supplied.

    readiness = weighted mean of five components, each 0–100:

    1. aptitude_component   (weight 0.30)
       Accuracy over aptitude practice/assessment answers, scaled by volume
       confidence: min(1, attempts / 30). Students with very few attempts get
       a proportionally lower score instead of a fake 100% on one question.
    2. coding_component     (weight 0.25)
       problems_solved / problems_attempted * 100, confidence-scaled by
       min(1, attempted / 5). Solved counts distinct problems.
    3. consistency_component (weight 0.15)
       Distinct activity days (STREAK_DAY events = qualifying learning
       activity) over the last 14 days, / 14 * 100. Not login-spammable:
       only real learning events create STREAK_DAY rows.
    4. coverage_component   (weight 0.15)
       Distinct topics attempted / min(12, total active topics) * 100 —
       breadth of preparation across the syllabus.
    5. assessment_component (weight 0.15)
       Mean of submitted assessment scores, confidence-scaled by
       min(1, attempts / 3).

Components with no data contribute 0; ``data_completeness`` (0–1) tells the
caller whether to show an "insufficient data" state instead of the score.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.models.assessment import Answer, Attempt
from app.models.coding import CodeSubmission
from app.models.content import Topic
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile
from app.models.question import Question

WEIGHTS = {
    "aptitude": 0.30,
    "coding": 0.25,
    "consistency": 0.15,
    "coverage": 0.15,
    "assessment": 0.15,
}

APTITUDE_CONFIDENCE_ATTEMPTS = 30
CODING_CONFIDENCE_ATTEMPTS = 5
ASSESSMENT_CONFIDENCE_ATTEMPTS = 3
CONSISTENCY_WINDOW_DAYS = 14
COVERAGE_TARGET_TOPICS = 12

COMPONENT_LABELS = {
    "aptitude": "Aptitude",
    "coding": "Coding",
    "consistency": "Consistency",
    "coverage": "Skill Coverage",
    "assessment": "Assessment Performance",
}


def compute_readiness(db: Session, student: StudentProfile) -> dict:
    """Compute the full readiness breakdown for a student. Read-only."""
    # ---------------- aptitude (practice + assessment answers) ----------------
    practice_correct, practice_attempted = db.execute(
        select(
            func.coalesce(func.sum(func.cast(PracticeAnswer.is_correct, Integer)), 0),
            func.count(PracticeAnswer.id),
        )
        .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
        .where(
            PracticeSession.student_id == student.id,
            PracticeSession.status == "COMPLETED",
            PracticeAnswer.selected_option_id.isnot(None),
        )
    ).one()

    assessment_correct, assessment_attempted = db.execute(
        select(
            func.coalesce(func.sum(func.cast(Answer.is_correct, Integer)), 0),
            func.count(Answer.id),
        )
        .join(Attempt, Answer.attempt_id == Attempt.id)
        .where(Attempt.student_id == student.id, Answer.selected_option_id.isnot(None))
    ).one()

    apt_attempted = int(practice_attempted) + int(assessment_attempted)
    apt_correct = int(practice_correct) + int(assessment_correct)
    apt_accuracy = (apt_correct / apt_attempted * 100) if apt_attempted else 0.0
    apt_conf = min(1.0, apt_attempted / APTITUDE_CONFIDENCE_ATTEMPTS)
    aptitude_component = round(apt_accuracy * apt_conf, 2)

    # ---------------- coding ----------------
    coding_attempted = db.scalar(
        select(func.count(func.distinct(CodeSubmission.problem_id))).where(
            CodeSubmission.student_id == student.id
        )
    ) or 0
    coding_solved = db.scalar(
        select(func.count(func.distinct(CodeSubmission.problem_id))).where(
            CodeSubmission.student_id == student.id, CodeSubmission.status == "ACCEPTED"
        )
    ) or 0
    coding_ratio = (coding_solved / coding_attempted * 100) if coding_attempted else 0.0
    coding_conf = min(1.0, coding_attempted / CODING_CONFIDENCE_ATTEMPTS)
    coding_component = round(coding_ratio * coding_conf, 2)

    # ---------------- consistency (activity days in last 14 days) ----------------
    window_start = datetime.now(timezone.utc) - timedelta(days=CONSISTENCY_WINDOW_DAYS)
    active_days = db.execute(
        select(func.count(func.distinct(func.date(ActivityEvent.created_at)))).where(
            ActivityEvent.student_id == student.id,
            ActivityEvent.created_at >= window_start,
            ActivityEvent.event_type.in_(["STREAK_DAY"]),
        )
    ).scalar() or 0
    consistency_component = round(min(1.0, active_days / CONSISTENCY_WINDOW_DAYS) * 100, 2)

    # ---------------- coverage (distinct topics attempted) ----------------
    total_active_topics = db.scalar(select(func.count(Topic.id)).where(Topic.is_active.is_(True))) or 0
    coverage_target = min(COVERAGE_TARGET_TOPICS, total_active_topics) or COVERAGE_TARGET_TOPICS
    practice_topics = db.execute(
        select(func.count(func.distinct(Question.topic_id)))
        .join(PracticeAnswer, PracticeAnswer.question_id == Question.id)
        .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
        .where(PracticeSession.student_id == student.id, Question.topic_id.isnot(None))
    ).scalar() or 0
    assessment_topics = db.execute(
        select(func.count(func.distinct(Question.topic_id)))
        .join(Answer, Answer.question_id == Question.id)
        .join(Attempt, Answer.attempt_id == Attempt.id)
        .where(Attempt.student_id == student.id, Question.topic_id.isnot(None))
    ).scalar() or 0
    distinct_topics = max(int(practice_topics), int(assessment_topics))
    coverage_component = round(min(1.0, distinct_topics / coverage_target) * 100, 2)

    # ---------------- assessment performance ----------------
    avg_score = db.scalar(
        select(func.avg(Attempt.score)).where(Attempt.student_id == student.id, Attempt.status == "SUBMITTED")
    )
    assessment_count = db.scalar(
        select(func.count(Attempt.id)).where(Attempt.student_id == student.id, Attempt.status == "SUBMITTED")
    ) or 0
    assessment_avg = float(avg_score) if avg_score is not None else 0.0
    assessment_conf = min(1.0, assessment_count / ASSESSMENT_CONFIDENCE_ATTEMPTS)
    assessment_component = round(assessment_avg * assessment_conf, 2)

    components = {
        "aptitude": aptitude_component,
        "coding": coding_component,
        "consistency": consistency_component,
        "coverage": coverage_component,
        "assessment": assessment_component,
    }
    score = round(sum(components[k] * WEIGHTS[k] for k in components), 2)

    # Data completeness: share of components with any underlying signal.
    signals = [
        apt_attempted > 0,
        coding_attempted > 0,
        active_days > 0,
        distinct_topics > 0,
        assessment_count > 0,
    ]
    data_completeness = round(sum(1 for s in signals if s) / len(signals), 2)

    return {
        "score": score,
        "components": components,
        "weights": WEIGHTS,
        "labels": COMPONENT_LABELS,
        "aptitude": {"accuracy": round(apt_accuracy, 2), "attempted": apt_attempted},
        "coding": {"attempted": coding_attempted, "solved": coding_solved},
        "assessment": {
            "attempts": assessment_count,
            "average_score": round(assessment_avg, 2) if assessment_count else None,
        },
        "consistency": {"active_days": int(active_days), "window_days": CONSISTENCY_WINDOW_DAYS},
        "coverage": {"topics_attempted": distinct_topics, "topics_target": coverage_target},
        "data_completeness": data_completeness,
    }


def sync_profile_readiness(db: Session, student: StudentProfile) -> float:
    """Recompute readiness and persist it on the profile. Called after events.

    Flushes first so activity/XP rows added earlier in the request (with
    autoflush disabled) are visible to the aggregation queries.
    """
    db.flush()
    result = compute_readiness(db, student)
    student.readiness_score = Decimal(str(round(result["score"], 2)))
    return result["score"]
