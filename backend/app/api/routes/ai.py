"""AI endpoints (docs/API_Specification.md §20, docs/Phases.md §18 — Phase 14).

All endpoints are student-facing read-only text helpers. None of them accept
metrics from the client; facts are computed server-side (Phase 14 rule: the
backend owns numbers, AI owns prose). Failures degrade to 503 with the standard
error envelope.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.core.rate_limit import ai_limiter
from app.db.session import get_db
from app.schemas.ai_questions import (
    AIQuestionEvaluateRequest,
    AIQuestionGenerateRequest,
)
from app.schemas.chat import ChatRequest
from app.services.ai import AIService
from app.services.ai_questions import AIQuestionService
from app.services.performance import PerformanceService
from app.utils.responses import success_response

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_ai_service() -> AIService:
    return AIService()


def _get_performance_service(db: Session = Depends(get_db)) -> PerformanceService:
    return PerformanceService(db)


def _get_ai_question_service(db: Session = Depends(get_db)) -> AIQuestionService:
    return AIQuestionService(db)


class AIRequest(BaseModel):
    question_text: str = Field(min_length=1, max_length=2000)
    correct_answer: str | None = Field(default=None, max_length=500)
    explanation: str | None = Field(default=None, max_length=2000)
    topic_name: str | None = Field(default=None, max_length=100)


class HintRequest(BaseModel):
    """Progressive hint request (Feature Group 5).

    ``level`` 1..4: conceptual clue → approach → pseudocode → solution
    explanation. Server-side rate limited like every AI endpoint. Hints never
    give the complete answer before the final level.
    """

    problem_text: str = Field(min_length=1, max_length=4000)
    topic_name: str | None = Field(default=None, max_length=100)
    level: int = Field(default=1, ge=1, le=4)
    source_code: str | None = Field(default=None, max_length=10000)


def _enforce_ai_rate_limit(user: Annotated[object, Depends(require_student)]) -> object:
    """Every Gemini-backed endpoint is limited per user (Phase 15.4).

    Budget: AI_RATE_LIMIT_PER_MINUTE requests/minute/user (default 10).
    Exceeding it raises RateLimitExceededError → 429 + standard envelope.
    Depends on require_student so RBAC is preserved (student-only).
    """
    ai_limiter.check(user.id)
    return user


@router.post("/explain")
def explain_question(
    req: AIRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    ai: AIService = Depends(_get_ai_service),
):
    """Step-by-step explanation for a question the student has already answered."""
    text = ai.explain_question(
        req.question_text,
        req.correct_answer or "not provided",
        req.explanation,
    )
    return success_response(data={"text": text}, message="Explanation generated")


@router.post("/hint")
def hint_for_question(
    req: AIRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    ai: AIService = Depends(_get_ai_service),
):
    """Hint without revealing the answer."""
    text = ai.hint_for_question(req.question_text, req.topic_name)
    return success_response(data={"text": text}, message="Hint generated")


@router.post("/hints/progressive")
def progressive_hint(
    req: HintRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    ai: AIService = Depends(_get_ai_service),
):
    """Progressive hint ladder (Feature Group 5).

    Level 1 = conceptual clue, 2 = approach, 3 = pseudocode, 4 = solution
    explanation. Each level's prompt is engineered not to leak the answer
    early; usage is rate-limited like all AI endpoints.
    """
    data = ai.progressive_hint(
        req.problem_text,
        req.topic_name,
        level=req.level,
        source_code=req.source_code,
    )
    return success_response(data=data, message=f"Hint level {data['level']} generated")


@router.post("/performance-interpretation")
def interpret_performance(
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    ai: AIService = Depends(_get_ai_service),
    perf: PerformanceService = Depends(_get_performance_service),
):
    """AI prose over server-computed performance facts (never client-supplied)."""
    student = user.student_profile
    overall = perf.get_overall(student)
    weaknesses = perf.get_weaknesses(student, limit=3)
    facts = {
        "overall_accuracy": overall.overall_accuracy,
        "questions_attempted": overall.total_questions_attempted,
        "assessment_avg_score": overall.assessment_avg_score,
        "weakest_topics": [f"{w.topic_name} ({w.accuracy}%)" for w in weaknesses],
    }
    text = ai.interpret_performance(facts)
    return success_response(data={"text": text, "facts": facts}, message="Performance interpretation generated")


# ============================================================ PHASE 15C
# ============================================================ AI QUESTIONS

# ============================================================ CHATBOT

@router.post("/chat")
def chat(
    req: ChatRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    ai: AIService = Depends(_get_ai_service),
):
    """General-purpose study chatbot (Phase 15: student Q&A).

    Students ask anything (aptitude doubts, coding concepts, interview prep,
    study planning). The recent conversation history can be sent so replies
    stay in context; it is capped server-side by the schema. Chat content is
    never persisted — only the AI answer log (outcome, no text) is written.
    Rate limited like every other Gemini-backed endpoint (10/min/user).
    """
    reply = ai.chat(req.message, history=[m.model_dump() for m in req.history])
    return success_response(data={"reply": reply, "model": "gemini-2.0-flash"}, message="Chat reply generated")


@router.post("/questions/generate")
def generate_question(
    req: AIQuestionGenerateRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    service: AIQuestionService = Depends(_get_ai_question_service),
):
    """Generate ONE validated multiple-choice question via Gemini.

    Rate limited (10/min/user). The question is returned to the client and is
    NEVER saved to the database (deliberate Phase 15C decision). The correct
    answer is NOT returned — the client receives a single-use ticket id that
    evaluate consumes to grade server-side.
    """
    data = service.generate_question(
        student=user.student_profile,
        topic_id=req.topic_id,
        company=req.company,
        topic_name=req.topic_name,
        difficulty=req.difficulty,
    )
    return success_response(data=data, message="AI question generated")


@router.post("/questions/evaluate")
def evaluate_question(
    req: AIQuestionEvaluateRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    service: AIQuestionService = Depends(_get_ai_question_service),
):
    """Grade an AI-question answer (deterministic, server-side).

    Grading uses the SERVER-SIDE ticket issued at generate time; the client
    cannot self-grade. Rate limited like every AI endpoint: it writes rows
    (ai_answer_logs, XP ledger) and may trigger a best-effort Gemini hint, so
    it must not be freely scriptable.
    Records only the answer outcome — never the question text — then updates
    topic accuracy, XP, streak, and the placement readiness score.
    """
    data = service.evaluate_answer(
        user.student_profile,
        ticket_id=req.ticket,
        student_answer=req.student_answer,
        time_taken_seconds=req.time_taken_seconds,
    )
    return success_response(data=data, message="Answer evaluated")
