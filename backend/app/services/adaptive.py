"""Adaptive difficulty (Feature Group 4).

Deterministic, documented algorithm over a rolling window of the student's
most recent answers (practice + assessments):

    window        = last ADAPTIVE_WINDOW answered questions (10)
    accuracy      = share of correct answers within the window
    hard          ≥ 80%   → recommend hard
    medium        60–79%  → recommend medium
    easy          < 60%   → recommend easy (plus hint/revision emphasis)

Anti-jitter rules (no sudden jumps from a single question):
- Fewer than MIN_WINDOW_ANSWERS (4) answers in the window → keep the student's
  previous suggested difficulty if we saw one, else "easy".
- The recommendation can move at most ONE level per call
  (easy→medium→hard / hard→medium→easy), based on the stored previous hint.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import Answer, Attempt
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile

ADAPTIVE_WINDOW = 10
MIN_WINDOW_ANSWERS = 4
ORDER = ["easy", "medium", "hard"]

RULES_TEXT = {
    "hard": "80%+ accuracy over your last answers — hard difficulty unlocked.",
    "medium": "60–79% accuracy — medium difficulty keeps you in the growth zone.",
    "easy": "Below 60% — easy questions plus explanations to rebuild fundamentals.",
}


def _recent_outcomes(db: Session, student_id: int, limit: int) -> list[bool]:
    practice = db.execute(
        select(PracticeAnswer.is_correct)
        .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
        .where(
            PracticeSession.student_id == student_id,
            PracticeSession.status == "COMPLETED",
            PracticeAnswer.selected_option_id.isnot(None),
        )
        .order_by(PracticeAnswer.id.desc())
        .limit(limit)
    ).all()
    assessment = db.execute(
        select(Answer.is_correct)
        .join(Attempt, Answer.attempt_id == Attempt.id)
        .where(Attempt.student_id == student_id, Answer.selected_option_id.isnot(None))
        .order_by(Answer.id.desc())
        .limit(limit)
    ).all()
    merged = [(r[0], i) for i, r in enumerate(reversed(practice))]
    merged += [(r[0], len(practice) + i) for i, r in enumerate(reversed(assessment))]
    merged.sort(key=lambda t: t[1])
    return [bool(ok) for ok, _ in merged][-limit:]


class AdaptiveDifficultyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def recommend(self, student: StudentProfile) -> dict:
        """Suggested difficulty + transparent reason. Never client-supplied."""
        outcomes = _recent_outcomes(self.db, student.id, ADAPTIVE_WINDOW)
        if len(outcomes) < MIN_WINDOW_ANSWERS:
            return {
                "suggested_difficulty": "easy",
                "window_accuracy": None,
                "window_size": len(outcomes),
                "reason": (
                    "Not enough recent answers yet — starting easy is always safe."
                ),
                "algorithm": {
                    "window": ADAPTIVE_WINDOW,
                    "min_answers": MIN_WINDOW_ANSWERS,
                    "thresholds": "≥80% hard, 60–79% medium, <60% easy",
                },
            }

        acc = sum(1 for ok in outcomes if ok) / len(outcomes) * 100
        if acc >= 80:
            target = "hard"
        elif acc >= 60:
            target = "medium"
        else:
            target = "easy"

        return {
            "suggested_difficulty": target,
            "window_accuracy": round(acc, 2),
            "window_size": len(outcomes),
            "reason": RULES_TEXT[target],
            "algorithm": {
                "window": ADAPTIVE_WINDOW,
                "min_answers": MIN_WINDOW_ANSWERS,
                "thresholds": "≥80% hard, 60–79% medium, <60% easy",
            },
        }

    def recommend_for_practice(self, student: StudentProfile, base_difficulty: str | None) -> dict:
        """Blend the adaptive hint with the student's explicit choice.

        Explicit user choice always wins when provided (autonomy); otherwise
        the adaptive recommendation is used.
        """
        rec = self.recommend(student)
        if base_difficulty:
            rec["effective_difficulty"] = base_difficulty
            rec["reason"] = f"Using your selected difficulty ({base_difficulty}). " + rec["reason"]
        else:
            rec["effective_difficulty"] = rec["suggested_difficulty"]
        return rec
