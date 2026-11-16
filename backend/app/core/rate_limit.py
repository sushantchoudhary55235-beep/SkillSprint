"""Rate limiting for API endpoints.

Phase 15 requirement: maximum 10 AI requests per user per minute.
Phase 16: general API rate limiting for production (configurable).
"""
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from app.core.config import settings
from app.core.exceptions import SkillSprintError


class RateLimitExceededError(SkillSprintError):
    """Raised when a client exceeds the request budget (429)."""

    status_code = 429
    error_code = "RATE_LIMITED"

    def __init__(self, retry_after_seconds: int, detail: str = "Rate limit exceeded") -> None:
        super().__init__(f"{detail}. Try again in {retry_after_seconds}s.")
        self.retry_after_seconds = retry_after_seconds


class SlidingWindowLimiter:
    """Thread-safe sliding-window limiter keyed by integer user ids."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 60.0,
        detail: Optional[str] = None,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Default detail includes the limit info for better error messages.
        self.detail = detail or f"Rate limit exceeded: maximum {max_requests} requests per {int(window_seconds)} seconds"
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
                raise RateLimitExceededError(retry_after, detail=self.detail)
            hits.append(now)
            # Opportunistic cleanup so idle users do not pin memory.
            if len(self._hits) > 10_000:
                for uid in [uid for uid, q in self._hits.items() if not q]:
                    del self._hits[uid]


# Process-wide limiter for AI (Gemini) endpoints.
# Uses custom detail message for AI-specific error reporting.
ai_limiter = SlidingWindowLimiter(
    max_requests=settings.AI_RATE_LIMIT_PER_MINUTE,
    detail=f"AI rate limit exceeded: maximum {settings.AI_RATE_LIMIT_PER_MINUTE} requests per minute",
)

# Process-wide general API rate limiter (production only, configurable via env).
# Default: 100 requests per minute per user.
_GENERAL_RATE_LIMIT_PER_MINUTE = getattr(settings, "GENERAL_RATE_LIMIT_PER_MINUTE", 100)
general_limiter = SlidingWindowLimiter(max_requests=_GENERAL_RATE_LIMIT_PER_MINUTE)


def get_general_limiter() -> Optional[SlidingWindowLimiter]:
    """Return the general limiter if production, else None (no-op in dev)."""
    if settings.is_production:
        return general_limiter
    return None