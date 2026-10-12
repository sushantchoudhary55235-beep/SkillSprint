"""Server-side answer-key tickets for AI-generated questions (Phase 15C hardening).

Problem this solves: `POST /ai/questions/generate` previously returned the
correct answer to the browser, and `POST /ai/questions/evaluate` trusted the
client to send the same answer back. Any student could self-grade (+5 XP,
fabricated accuracy) by scripting evaluate with matching answers.

Fix: at generate time the backend keeps the validated question (options +
correct answer) in a short-lived, single-use, per-student ticket and returns
only an opaque ``ticket`` id plus a client copy of the options. At evaluate
time the client sends the ticket; the answer key NEVER leaves the server.
The client answer is graded against the stored key — client-supplied
``correct_answer`` is ignored (kept only as an optional cross-check).

Design constraints honored:
- Volatile in-process store (no DB rows): the "questions are never persisted"
  rule still holds. Restart simply invalidates outstanding tickets.
- Single use + short TTL + per-student ownership: a ticket cannot be replayed,
  shared, or used after expiry, and each evaluate consumes exactly one ticket.
"""
import secrets
import threading
import time
from dataclasses import dataclass

TTL_SECONDS = 30 * 60          # generous window to answer one question
_MAX_TICKETS_PER_STUDENT = 20  # bounds memory; oldest evicted
_MAX_TICKETS_TOTAL = 10_000    # global bound


@dataclass
class QuestionTicket:
    student_id: int
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: str | None
    topic_id: int | None
    topic_name: str | None
    difficulty: str
    expires_at: float


class TicketStore:
    """Thread-safe, volatile, single-use store of question tickets."""

    def __init__(self) -> None:
        self._tickets: dict[str, QuestionTicket] = {}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _prune_expired(store: dict[str, QuestionTicket], now: float) -> None:
        expired = [tid for tid, t in store.items() if t.expires_at <= now]
        for tid in expired:
            del store[tid]

    def _evict_for_student(self, student_id: int, now: float) -> None:
        self._prune_expired(self._tickets, now)
        mine = [(tid, t) for tid, t in self._tickets.items() if t.student_id == student_id]
        mine.sort(key=lambda pair: pair[1].expires_at)  # oldest first
        excess = len(mine) - (_MAX_TICKETS_PER_STUDENT - 1)
        for tid, _t in mine[:max(0, excess)]:
            del self._tickets[tid]

    # ---------------------------------------------------------------- public

    def issue(self, ticket: QuestionTicket) -> str:
        """Store a question server-side and return its opaque ticket id."""
        now = time.monotonic()
        with self._lock:
            self._evict_for_student(ticket.student_id, now)
            if len(self._tickets) >= _MAX_TICKETS_TOTAL:
                # Global pressure: drop the soonest-expiring entries.
                for tid, _t in sorted(self._tickets.items(), key=lambda kv: kv[1].expires_at)[
                    : len(self._tickets) - _MAX_TICKETS_TOTAL + 1
                ]:
                    del self._tickets[tid]
            ticket_id = secrets.token_urlsafe(24)
            ticket.expires_at = now + TTL_SECONDS  # store owns the TTL
            self._tickets[ticket_id] = ticket
            return ticket_id

    def consume(self, ticket_id: str, student_id: int) -> QuestionTicket | None:
        """Atomically pop a ticket if it exists, is unexpired, and is owned
        by ``student_id``. Single use: gone after this call."""
        now = time.monotonic()
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return None
            del self._tickets[ticket_id]  # single use — remove first
            if ticket.student_id != student_id:
                return None  # wrong owner: do not leak the stored question
            if ticket.expires_at <= now:
                return None
            return ticket

    def clear(self) -> None:
        """Test helper: empty the store."""
        with self._lock:
            self._tickets.clear()


# Process-wide store used by the AI question routes.
question_ticket_store = TicketStore()
