"""Per-user sliding-window rate limiting for AI (Gemini) endpoints.

Phase 15 requirement: maximum 10 AI requests per user per minute; exceeding
returns HTTP 429 with the standard error envelope.

Implementation: an in-memory sliding window keyed by user id. This keeps the
platform dependency-free and is correct for a single-process deployment (the
default for this project). For horizontally scaled deployments the same
interface can be backed by Redis without touching call sites.
"""
import threading
import time
from collections import defaultdict, deque

from app.core.config import settings
from app.core.exceptions import SkillSprintError


class RateLimitExceededError(SkillSprintError):
    """Raised when a client exceeds the AI request budget (429)."""

    status_code = 429
    error_code = "RATE_LIMITED"

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            f"AI rate limit exceeded: maximum {settings.AI_RATE_LIMIT_PER_MINUTE} "
            f"requests per minute. Try again in {retry_after_seconds}s."
        )
        self.retry_after_seconds = retry_after_seconds


class SlidingWindowLimiter:
    """Thread-safe sliding-window limiter keyed by integer user ids."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[int, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user_id: int) -> None:
        """Record a hit for ``user_id`` or raise RateLimitExceededError."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[user_id]
            cutoff = now - self.window_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                raise RateLimitExceededError(retry_after)
            hits.append(now)
            # Opportunistic cleanup so idle users do not pin memory.
            if len(self._hits) > 10_000:
                for uid in [uid for uid, q in self._hits.items() if not q]:
                    del self._hits[uid]


# Process-wide limiter for AI (Gemini) endpoints.
ai_limiter = SlidingWindowLimiter(max_requests=settings.AI_RATE_LIMIT_PER_MINUTE)
