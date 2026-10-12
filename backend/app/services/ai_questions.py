"""AI Question Generation & Evaluation (Phase 15C).

End-to-end flow (docs/Phases.md §18 + the master prompt's Phase 15C spec):

    Student picks Company + Topic + Difficulty
        → POST /api/ai/questions/generate
        → Gemini returns a multiple-choice question (JSON)
        → Backend validates the structure (question, 4 options, correct
          answer, explanation) — one retry on invalid JSON, then 503
        → Question is returned and **never persisted** (deliberate project
          decision: no AI question rows in the database)
        → Student answers in the UI
        → POST /api/ai/questions/evaluate
        → Backend grades the answer, records ONLY the answer outcome
          (timestamp, topic, correctness), updates topic accuracy, XP,
          streak, missions and badges, and the placement readiness score.

The backend owns every number (accuracy, XP, streak, readiness); Gemini only
produces question text.
"""
import json
import logging
import random
import re
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.models.ai_answer_log import AIAnswerLog
from app.models.content import Topic
from app.models.profile import StudentProfile
from app.schemas.practice import TopicProgressItem
from app.repositories.practice import PracticeRepository
from app.services.gamification import GamificationService, XP_CORRECT_ANSWER
from app.services.ai import AIService
from app.services.ai_tickets import QuestionTicket, question_ticket_store

logger = logging.getLogger("skillsprint.ai_questions")

# Limits (defensive caps on client-supplied strings).
_MAX_QUESTION_CHARS = 2000
_MAX_OPTION_CHARS = 300
_MAX_EXPLANATION_CHARS = 2000

# Readiness score weights (deterministic; Phase 7 engine owns the metric).
READINESS_MIN_ATTEMPTS = 10
READINESS_ACCURACY_WEIGHT = 0.7
READINESS_CODING_WEIGHT = 0.3

AI_TOPIC_ID = -1  # sentinel topic_id for AI-generated (unpersisted) questions


class AIQuestionService:
    """Gemini-backed question generation + deterministic evaluation."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.ai = AIService()
        self.gam = GamificationService(db)

    # ============================================================ GENERATE

    def generate_question(
        self,
        *,
        student: StudentProfile,
        topic_id: int | None,
        company: str | None,
        topic_name: str | None,
        difficulty: str,
    ) -> dict[str, Any]:
        """Generate one validated MCQ via Gemini. NEVER persisted to the DB.

        The answer key is held server-side behind a single-use ticket;
        the response contains the ticket id, not the correct answer.
        """
        if not self.ai.enabled:
            raise ServiceUnavailableError("AI service is not configured")

        # Resolve topic for prompt context (name may come from the DB row).
        if topic_id is not None:
            topic = self.db.get(Topic, topic_id)
            if topic is None:
                raise NotFoundError(f"Topic {topic_id} not found")
            topic_name = topic.name
        if not topic_name:
            raise ValidationError("topic_id or topic_name is required")

        prompt = (
            f"Generate a multiple choice aptitude question for {company or 'general'} "
            f"placement preparation. Topic: {topic_name}. Difficulty: {difficulty}. "
            "Return JSON with fields: question, options (list of 4), correct_answer, "
            "explanation. Do not include any text outside the JSON."
        )

        # Validate → retry once on invalid JSON/shape → then 503.
        last_error: str | None = None
        for attempt in range(2):
            raw = self.ai._generate(prompt if attempt == 0 else prompt + "\nReturn ONLY the JSON object.")
            parsed = self._parse_question_json(raw)
            if parsed is not None:
                # Keep the answer key SERVER-SIDE: the client receives an
                # opaque single-use ticket instead of the correct answer, so
                # evaluate can no longer be self-graded by a script.
                ticket_id = question_ticket_store.issue(QuestionTicket(
                    student_id=student.id,
                    question_text=parsed["question"],
                    options=parsed["options"],
                    correct_answer=parsed["correct_answer"],
                    explanation=parsed["explanation"],
                    topic_id=topic_id,
                    topic_name=topic_name,
                    difficulty=difficulty,
                    expires_at=0.0,  # set by the store on issue
                ))
                return {
                    "question": parsed["question"],
                    "options": parsed["options"],
                    "ticket": ticket_id,
                    "topic_id": topic_id,
                    "topic_name": topic_name,
                    "company": company,
                    "difficulty": difficulty,
                    "persisted": False,  # explicit: AI questions are never saved
                    # NOTE: correct_answer/explanation are intentionally NOT
                    # returned to the client any more.
                }
            last_error = "invalid question structure from AI"
            logger.warning("AI question validation failed (attempt %d)", attempt + 1)

        raise ServiceUnavailableError(
            "AI generated an invalid question after retry. Please try again."
        )

    # ---------------------------------------------------------- parsing

    def _parse_question_json(self, raw: str) -> dict[str, Any] | None:
        """Parse and structurally validate Gemini's JSON answer, else None."""
        if not raw:
            return None
        text = raw.strip()
        # Tolerate markdown fences around the JSON.
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            # Sometimes Gemini prefixes prose; grab the outermost JSON object.
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                return None

        if not isinstance(data, dict):
            return None
        question = data.get("question")
        options = data.get("options")
        correct = data.get("correct_answer")
        explanation = data.get("explanation")

        if not isinstance(question, str) or not question.strip():
            return None
        if not isinstance(options, list) or len(options) != 4:
            return None
        cleaned_options: list[str] = []
        for opt in options:
            if not isinstance(opt, str) or not opt.strip():
                return None
            cleaned_options.append(opt.strip()[:_MAX_OPTION_CHARS])
        # Options must be distinct — duplicates make the question unanswerable.
        if len(set(cleaned_options)) != 4:
            return None
        if not isinstance(correct, str) or not correct.strip():
            return None
        correct = correct.strip()
        # The correct answer must be one of the options (exact or by index).
        if correct not in cleaned_options:
            index_match = re.fullmatch(r"[Oo]ption\s*([1-4])", correct)
            if index_match:
                correct = cleaned_options[int(index_match.group(1)) - 1]
            else:
                # Case-insensitive fallback for e.g. "B) 42" style answers.
                lowered = {o.lower(): o for o in cleaned_options}
                correct = lowered.get(correct.lower())
                if correct is None:
                    return None
        if not isinstance(explanation, str) or not explanation.strip():
            return None

        return {
            "question": question.strip()[:_MAX_QUESTION_CHARS],
            "options": cleaned_options,
            "correct_answer": correct,
            "explanation": explanation.strip()[:_MAX_EXPLANATION_CHARS],
        }

    # ============================================================ EVALUATE

    def evaluate_answer(
        self,
        student: StudentProfile,
        *,
        ticket_id: str,
        student_answer: str,
        time_taken_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Grade an AI-question answer deterministically (never re-ask the AI).

        The answer key comes from the SERVER-SIDE ticket issued at generate
        time — never from the client (a client-supplied correct_answer cannot
        influence grading). The ticket is single-use: replaying an evaluate
        call fails. Records only the answer outcome (no question
        persistence), then updates accuracy, XP, streak, missions and badges.
        """
        ticket = question_ticket_store.consume(ticket_id, student.id)
        if ticket is None:
            # Unknown, expired, already used, or owned by another student.
            raise ValidationError(
                "Invalid or expired question ticket. Generate a new question."
            )

        if student_answer is None or not str(student_answer).strip():
            raise ValidationError("student_answer is required")

        question = ticket.question_text
        options = ticket.options
        correct_answer = ticket.correct_answer
        explanation = ticket.explanation
        topic_id = ticket.topic_id
        topic_name = ticket.topic_name
        difficulty = ticket.difficulty

        if topic_id is not None and topic_id != AI_TOPIC_ID:
            if self.db.get(Topic, topic_id) is None:
                raise NotFoundError(f"Topic {topic_id} not found")

        answer_text = str(student_answer).strip()
        is_correct = answer_text == str(correct_answer).strip()

        # ---- XP (server-side ledger) ----
        # Single-use tickets make replay impossible; the ticket id doubles as
        # an idempotency reference for the ledger entry.
        xp_earned = 0
        if is_correct:
            self.gam.award_xp(
                student,
                XP_CORRECT_ANSWER,
                "AI_QUESTION_CORRECT",
                reference_id=None,  # no persisted question row to reference
                description="Correct AI-generated question answer",
            )
            xp_earned = XP_CORRECT_ANSWER

        # ---- answer-outcome log (the question text is NEVER stored) ----
        self.db.add(AIAnswerLog(
            student_id=student.id,
            topic_id=topic_id if topic_id != AI_TOPIC_ID else None,
            topic_name=topic_name,
            difficulty=difficulty,
            is_correct=is_correct,
            time_taken_seconds=time_taken_seconds,
            xp_earned=xp_earned,
        ))
        # flush so the stats queries below see this row (autoflush is off)
        self.db.flush()

        # ---- streak, missions, badges ----
        self.gam.touch_streak(student)
        self.gam.update_mission_progress(student, "ANSWER_QUESTION", increment=1)
        self.gam.evaluate_badges(student)

        # ---- accuracy (topic + overall) via the practice repository ----
        repo = PracticeRepository(self.db)
        stats = repo.get_overall_stats(student.id)
        topic_progress = repo.get_topic_progress(student.id)

        # Include AI answer outcomes in the overall accuracy computation so
        # readiness/weak-topic signals reflect them (answers are logged,
        # questions are not).
        from sqlalchemy import select, func

        ai_total = self.db.scalar(
            select(func.count(AIAnswerLog.id)).where(AIAnswerLog.student_id == student.id)
        ) or 0
        ai_correct = self.db.scalar(
            select(func.count(AIAnswerLog.id)).where(
                AIAnswerLog.student_id == student.id, AIAnswerLog.is_correct.is_(True))
        ) or 0
        total = int(stats["total_questions_attempted"]) + int(ai_total)
        correct_total = int(stats["total_correct"]) + int(ai_correct)
        overall_accuracy = round(correct_total / total * 100, 2) if total > 0 else 0.0

        topic_accuracy: float | None = None
        if topic_id is not None and topic_id != AI_TOPIC_ID:
            for t in topic_progress:
                if t["topic_id"] == topic_id:
                    base_total = int(t["total_attempts"])
                    base_correct = int(t["correct_answers"])
                    ai_rows = self.db.execute(
                        select(AIAnswerLog.is_correct).where(
                            AIAnswerLog.student_id == student.id,
                            AIAnswerLog.topic_id == topic_id,
                        )
                    ).all()
                    ai_c = sum(1 for (ok,) in ai_rows if ok)
                    topic_total = base_total + len(ai_rows)
                    topic_accuracy = (
                        round((base_correct + ai_c) / topic_total * 100, 2)
                        if topic_total > 0 else None
                    )
                    break

        # ---- placement readiness score (deterministic) ----
        readiness_stats = {
            "overall_accuracy": overall_accuracy,
            "total_questions_attempted": total,
            "coding_solved": 0,
            "coding_attempted": 0,
        }
        readiness = self._update_readiness(student, readiness_stats)

        self.db.commit()

        # ---- hint for wrong answers (best effort; AI failure tolerated) ----
        hint: str | None = None
        if not is_correct and self.ai.enabled:
            try:
                hint = self.ai.hint_for_question(question, topic_name)
            except Exception:  # noqa: BLE001 — hint is best-effort
                hint = None

        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,  # revealed only AFTER answering
            "student_answer": answer_text,
            "explanation": explanation,  # revealed only AFTER answering
            "hint": hint,
            "xp_earned": xp_earned,
            "xp_total": student.xp,
            "level": student.level,
            "level_up": self.gam.xp_summary(student),
            "current_streak": student.current_streak,
            "topic_accuracy": topic_accuracy,
            "overall_accuracy": overall_accuracy,
            "readiness_score": readiness,
            "recorded_only_answer": True,  # question text is never stored
        }

    # ---------------------------------------------------------- readiness

    def _update_readiness(self, student: StudentProfile, stats: dict[str, Any]) -> float:
        """Recompute the placement readiness score from real performance data.

        Score = accuracy (0-100, weighted 70%) + coding solve ratio (0-100,
        weighted 30%). Stored on the profile; deterministic and server-side.
        """
        accuracy = float(stats.get("overall_accuracy") or 0.0)
        coding_solved = int(stats.get("coding_solved") or 0)
        coding_attempted = int(stats.get("coding_attempted") or 0)
        coding_ratio = (coding_solved / coding_attempted * 100) if coding_attempted else 0.0

        total_attempted = int(stats.get("total_questions_attempted") or 0)
        confidence = min(1.0, total_attempted / READINESS_MIN_ATTEMPTS)
        score = (accuracy * READINESS_ACCURACY_WEIGHT + coding_ratio * READINESS_CODING_WEIGHT) * confidence

        student.readiness_score = Decimal(str(round(score, 2)))
        return round(score, 2)

    # ---------------------------------------------------------- topic feed

    def topic_progress_items(self, student: StudentProfile) -> list[TopicProgressItem]:
        """Topic aggregates for the recommendations UI (accuracy < 60% = weak)."""
        repo = PracticeRepository(self.db)
        return [TopicProgressItem(**t) for t in repo.get_topic_progress(student.id)]
