# Phase 4 Implementation Plan

**Generated**: 2026-11-01  
**Based on**: PHASE_4_VALIDATION_CHECKLIST.md  
**Status**: PLANNING PHASE — Awaiting approval before implementation

---

## Executive Summary

This plan addresses the reliability, security, testability, and multi-worker compatibility gaps in SkillSprint's Gemini AI integration identified during Phase 4 validation. The approved architectural direction uses **existing PostgreSQL/SQLAlchemy infrastructure** instead of introducing Redis.

### Scope
- PostgreSQL-backed AI question ticket store (replaces in-memory `TicketStore`)
- PostgreSQL-backed rate limiter with **atomic advisory locks** (replaces in-memory `SlidingWindowLimiter`)
- Configurable Gemini model and timeout settings
- Retry logic with exponential backoff for transient failures (using `time.sleep` in sync code)
- **Circuit breaker deferred to Phase 5**
- Structured token usage logging from Gemini response metadata
- Comprehensive mocked contract test coverage + **PostgreSQL concurrency tests** (40+ new tests)
- No Redis infrastructure, no new external dependencies

### Out of Scope
- Daily cost budget enforcement (Phase 5+)
- Real Gemini API contract tests (opt-in CI only)
- Redis infrastructure
- AI response caching
- Per-user/feature rate limit tiers
- Circuit breaker implementation (deferred to Phase 5)

---

## 1. PostgreSQL-Backed AI Question Ticket Store

### Current State
- **File**: `backend/app/services/ai_tickets.py`
- **Class**: `TicketStore` (in-memory `dict` with `threading.Lock`)
- **Instance**: `question_ticket_store` (module-level singleton)
- **TTL**: 30 minutes (`TTL_SECONDS = 30 * 60`)
- **Limits**: 20 tickets/student, 10,000 total
- **Behavior**: Lost on restart, not shared across workers

### Proposed Design
- **New model**: `QuestionTicket` in `backend/app/models/question_ticket.py`
- **Table**: `question_tickets`
- **Fields**:
  - `id` (BigInteger PK)
  - `ticket_id` (String(64), unique index) — opaque token returned to client
  - `student_id` (BigInteger FK → student_profiles.id, index)
  - `question_text` (String(2000))
  - `options` (JSONB) — array of 4 strings
  - `correct_answer` (String(300))
  - `explanation` (String(2000), nullable)
  - `topic_id` (BigInteger FK → topics.id, nullable, index)
  - `topic_name` (String(100), nullable)
  - `difficulty` (String(20))
  - `expires_at` (DateTime, index)
  - `consumed_at` (DateTime, nullable)
  - `created_at` (DateTime, server_default=now)
  - `idempotency_key` (String(128), nullable) — **NEW: for duplicate generate protection**

### Indexes
- `ix_question_tickets_student_id` — on `student_id`
- `ix_question_tickets_expires_at` — on `expires_at`
- `ix_question_tickets_student_expires` — composite on `(student_id, expires_at)`
- **Composite unique index for student-scoped idempotency**:
  ```sql
  CREATE UNIQUE INDEX ix_question_tickets_idempotency 
      ON question_tickets(student_id, idempotency_key) 
      WHERE idempotency_key IS NOT NULL;
  ```

### Migration
- **New migration**: `add_question_tickets_table.py`
- **Dependencies**: None (standalone table)
- **Rollback**: Drop table

### Service Changes
- **File**: `backend/app/services/ai_tickets.py`
- **New class**: `DatabaseTicketStore` (implements same interface as `TicketStore`)
- **Methods**:
  - `issue(ticket: QuestionTicket) -> str` — **Claim-then-generate pattern with INSERT ... ON CONFLICT** for idempotency
  - `consume(ticket_id: str, student_id: int) -> QuestionTicket | None` — SELECT FOR UPDATE, verify ownership/expiry, UPDATE consumed_at, return ticket
  - `clear()` — DELETE all (test helper)
  - `prune_expired()` — DELETE WHERE expires_at < now() (periodic cleanup)
- **Transaction behavior**: Each operation in its own transaction; `consume` uses `SELECT FOR UPDATE` to prevent race conditions
- **Expiry strategy**: 
  - On `issue`: set `expires_at = now() + 30 minutes`
  - On `consume`: reject if `expires_at <= now()`
  - Cleanup: periodic job or on-read pruning (DELETE WHERE expires_at < now())
- **Failure behavior**: If DB unavailable → raise `ServiceUnavailableError` (503), consistent with AI service degradation

#### Idempotency-Aware Ticket Issue (Claim-Then-Generate Pattern)

The ticket store implements a **claim-then-generate** pattern to prevent duplicate Gemini calls under concurrency:

```python
def issue(self, ticket: QuestionTicket) -> str:
    """
    Atomically claim or reuse an idempotency key, then generate and store the ticket.
    
    Uses INSERT ... ON CONFLICT to claim the key. If another concurrent request
    already claimed it, we wait for that request to complete and reuse its result.
    """
    ticket_id = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TTL_SECONDS)
    
    # Per-student limit enforcement (atomic within same transaction)
    existing_count = self.db.scalar(
        select(func.count(QuestionTicket.id))
        .where(QuestionTicket.student_id == ticket.student_id)
        .where(QuestionTicket.consumed_at.is_(None))
        .where(QuestionTicket.expires_at > datetime.now(timezone.utc))
    )
    if existing_count >= MAX_TICKETS_PER_STUDENT:
        oldest = self.db.execute(
            select(QuestionTicket.id)
            .where(QuestionTicket.student_id == ticket.student_id)
            .where(QuestionTicket.consumed_at.is_(None))
            .order_by(QuestionTicket.expires_at.asc())
            .limit(existing_count - MAX_TICKETS_PER_STUDENT + 1)
        ).scalars().all()
        for oid in oldest:
            self.db.delete(self.db.get(QuestionTicket, oid))
    
    # If idempotency key provided, attempt to claim it
    if ticket.idempotency_key:
        # Try to insert a placeholder row claiming this key
        try:
            placeholder = QuestionTicket(
                ticket_id=ticket_id,
                student_id=ticket.student_id,
                question_text="",  # Will be filled after Gemini call
                options=[],
                correct_answer="",
                explanation=None,
                topic_id=ticket.topic_id,
                topic_name=ticket.topic_name,
                difficulty=ticket.difficulty,
                expires_at=expires_at,
                idempotency_key=ticket.idempotency_key,
            )
            self.db.add(placeholder)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            # Another request already claimed this key. Wait for it to complete.
            return self._wait_for_idempotent_result(ticket.student_id, ticket.idempotency_key)
        
        # We claimed the key. Now call Gemini.
        try:
            # ... call Gemini, validate response ...
            # Update the placeholder with real data
            placeholder.question_text = parsed_question_text
            placeholder.options = parsed_options
            placeholder.correct_answer = parsed_correct_answer
            placeholder.explanation = parsed_explanation
            self.db.flush()
            return ticket_id
        except Exception:
            # On failure, delete the placeholder so key can be retried
            self.db.delete(placeholder)
            self.db.flush()
            raise
    
    # No idempotency key: normal single-use ticket
    db_ticket = QuestionTicket(
        ticket_id=ticket_id,
        student_id=ticket.student_id,
        question_text=ticket.question_text,
        options=ticket.options,
        correct_answer=ticket.correct_answer,
        explanation=ticket.explanation,
        topic_id=ticket.topic_id,
        topic_name=ticket.topic_name,
        difficulty=ticket.difficulty,
        expires_at=expires_at,
        idempotency_key=None,
    )
    self.db.add(db_ticket)
    self.db.flush()
    return ticket_id


def _wait_for_idempotent_result(self, student_id: int, idempotency_key: str) -> str:
    """Wait for concurrent request to complete and return its ticket_id."""
    # Poll for completion (with timeout)
    for _ in range(30):  # 30 seconds max wait
        existing = self.db.scalar(
            select(QuestionTicket.ticket_id)
            .where(QuestionTicket.student_id == student_id)
            .where(QuestionTicket.idempotency_key == idempotency_key)
            .where(QuestionTicket.question_text != "")
        )
        if existing:
            return existing
        time.sleep(1)  # Note: synchronous sleep in sync context
    raise ServiceUnavailableError("Idempotent request timed out")
```

### Interface Preservation
- `AIQuestionService.generate_question()` and `evaluate_answer()` call `question_ticket_store.issue()` and `.consume()` — no call site changes needed
- Only the `question_ticket_store` instance swap changes
- New `idempotency_key` parameter passed from route handler (optional header)

---

## 2. PostgreSQL-Backed Rate Limiter

### Current State
- **File**: `backend/app/core/rate_limit.py`
- **Class**: `SlidingWindowLimiter` (in-memory `defaultdict(deque)` with `threading.Lock`)
- **Instance**: `ai_limiter` (module-level singleton)
- **Window**: 60 seconds sliding
- **Limit**: `settings.AI_RATE_LIMIT_PER_MINUTE` (default 10)
- **Behavior**: Lost on restart, not shared across workers

### Design Comparison

| Aspect | Fixed Window | Sliding Window (Current) | Sliding Window Log + Advisory Lock (Proposed) |
|--------|-------------|-------------------------|----------------------------------------------|
| **Accuracy** | Allows burst at boundaries | Accurate | Most accurate |
| **DB queries** | 1 per request | N/A (in-memory) | 2-3 per request |
| **Storage** | 1 row/user/window | In-memory deque | 1 row/user/request |
| **Concurrency** | Simple upsert | In-memory lock | **PostgreSQL advisory lock** (`pg_advisory_xact_lock`) |
| **Cleanup** | TTL on window | Opportunistic | DELETE old rows |

### Recommendation: **Sliding Window Log with PostgreSQL Advisory Locks**

**Reasoning**:
- Maintains exact same sliding-window semantics as current in-memory implementation
- **Atomic concurrency control**: Advisory locks serialize rate-limit checks per user/window without row locks
- Works across multiple workers and processes (no in-memory state)
- Lightweight: `pg_advisory_xact_lock` is released automatically on commit/rollback
- Acceptable DB load: ~10 requests/min/user → at 1000 concurrent users = ~167 req/s, well within PostgreSQL capacity
- Uses existing connection pool (pool_size=20, max_overflow=10)
- Cleanup can be batched (DELETE WHERE created_at < now() - window)
- **No race conditions**: Unlike simple COUNT+INSERT, advisory lock guarantees limit is never exceeded

### Proposed Design
- **New model**: `AIRateLimit` in `backend/app/models/ai_rate_limit.py`
- **Table**: `ai_rate_limits`
- **Fields**:
  - `id` (BigInteger PK)
  - `user_id` (BigInteger FK → student_profiles.id, index)
  - `created_at` (DateTime, server_default=now, index)
- **Index**: Composite `(user_id, created_at)` for efficient window queries

### Service Changes
- **File**: `backend/app/core/rate_limit.py`
- **New class**: `DatabaseRateLimiter` (implements same interface as `SlidingWindowLimiter`)
- **Method**: `check(user_id: int) -> None`
  ```python
  def check(self, user_id: int) -> None:
      """
      Atomically check and record a rate limit hit using advisory lock.
      
      Transaction isolation: READ COMMITTED (PostgreSQL default)
      Advisory lock scope: transaction-level (released on commit/rollback)
      
      Steps:
      1. Acquire advisory lock for (user_id, current_window_hash)
      2. Count existing requests in sliding window
      3. If at limit, raise RateLimitExceededError
      4. Insert new request record
      5. Commit (releases lock)
      """
      window_start = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
      window_hash = int(window_start.timestamp())  # Coarse window hash for lock key
      
      with self.db.begin():
          # 1. Acquire advisory lock for this user's current window
          # This serializes concurrent rate-limit checks for the same user/window
          self.db.execute(
              text("SELECT pg_advisory_xact_lock(:user_id, :window_hash)"),
              {"user_id": user_id, "window_hash": window_hash}
          )
          
          # 2. Count requests in sliding window (inside the lock)
          count = self.db.scalar(
              select(func.count(AIRateLimit.id))
              .where(AIRateLimit.user_id == user_id)
              .where(AIRateLimit.created_at >= window_start)
          ) or 0
          
          # 3. Check limit
          if count >= self.max_requests:
              # Calculate retry-after based on oldest request in window
              oldest = self.db.scalar(
                  select(AIRateLimit.created_at)
                  .where(AIRateLimit.user_id == user_id)
                  .where(AIRateLimit.created_at >= window_start)
                  .order_by(AIRateLimit.created_at.asc())
              )
              if oldest:
                  retry_after = max(1, int(self.window_seconds - 
                      (datetime.now(timezone.utc) - oldest).total_seconds()))
              else:
                  retry_after = int(self.window_seconds)
              raise RateLimitExceededError(retry_after)
          
          # 4. Record this request
          self.db.add(AIRateLimit(user_id=user_id))
          # 5. Commit releases advisory lock automatically
  ```
- **Cleanup**: Periodic `DELETE FROM ai_rate_limits WHERE created_at < now() - window_seconds` (can run via cron or on-read with probability)
- **Failure behavior**: If DB unavailable → raise `ServiceUnavailableError` (503) — consistent with AI degradation

### Alternative Considered: Fixed-Window Atomic Upsert
```sql
-- Alternative: Fixed window with single-row upsert per user/window
CREATE TABLE ai_rate_limit_windows (
    user_id BIGINT NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, window_start)
);
```
**Why Advisory Lock + Sliding Window was chosen:**
1. Preserves exact sliding-window semantics (no boundary bursts)
2. Works with existing `AIRateLimit` append-only table design
3. Advisory locks are lightweight (no row locks, no deadlocks with other transactions)
4. Clean separation: rate limiting logic doesn't require schema change

### Interface Preservation
- `ai_limiter.check(user_id)` called from `_enforce_ai_rate_limit()` in `ai.py` routes — no call site changes
- Only the `ai_limiter` instance swap changes

---

## 3. Gemini Configuration

### Current State
- **File**: `backend/app/core/config.py`
- **Settings**: `GEMINI_API_KEY`, `AI_RATE_LIMIT_PER_MINUTE`
- **Hardcoded in `ai.py`**:
  - `_TIMEOUT_S = 15.0` (lines 26, 71, 233)
  - `model="gemini-2.0-flash"` (lines 60, 82, 222, 244)

### Proposed Settings
Add to `Settings` class in `config.py`:

```python
# AI
GEMINI_API_KEY: str = ""
AI_RATE_LIMIT_PER_MINUTE: int = 10
GEMINI_MODEL: str = "gemini-2.0-flash"      # NEW
AI_TIMEOUT_S: float = 15.0                   # NEW
```

### Service Changes
- **File**: `backend/app/services/ai.py`
- **Changes**:
  - Remove `_TIMEOUT_S` constant
  - Remove hardcoded model strings
  - Use `settings.GEMINI_MODEL` and `settings.AI_TIMEOUT_S`
  - Add validation in `Settings`:
    ```python
    @property
    def ai_timeout(self) -> float:
        return max(1.0, min(self.AI_TIMEOUT_S, 60.0))  # clamp 1-60s
    ```

### Safe Defaults
- `GEMINI_MODEL`: `"gemini-2.0-flash"` (current behavior)
- `AI_TIMEOUT_S`: `15.0` (current behavior)
- Invalid values: clamped to safe range, logged at WARNING

### No API Key Exposure
- `GEMINI_API_KEY` already never logged (only passed in `params={"key": ...}` to httpx)
- Model and timeout are non-sensitive

---

## 4. Retry and Provider Error Handling

### Current State
- **File**: `backend/app/services/ai.py`
- **Methods**: `_generate()`, `_generate_chat()`
- **Behavior**: Single attempt, ANY exception → 503
- **One retry**: Only in `AIQuestionService.generate_question()` for invalid JSON (attempt 2 adds "Return ONLY the JSON object.")

### Proposed Retry Strategy

| Error Type | Retry? | Max Retries | Backoff |
|------------|--------|-------------|---------|
| `httpx.TimeoutException` | Yes | 1 | 1s → 2s |
| `httpx.HTTPStatusError` 5xx | Yes | 1 | 1s → 2s |
| `httpx.HTTPStatusError` 429 | Yes | 1 | 2s → 4s (respect Retry-After if present) |
| `httpx.HTTPStatusError` 401/403 | **No** | 0 | — |
| `httpx.HTTPStatusError` 400 | **No** | 0 | — |
| JSON parse / KeyError / IndexError | **No** | 0 | — (malformed response = 503) |

### Implementation
- **File**: `backend/app/services/ai.py`
- **New helper**: `_generate_with_retry(prompt: str, chat: bool = False) -> str`
- **Logic**:
  ```python
  max_retries = 1
  base_delay = 1.0
  for attempt in range(max_retries + 1):
      try:
          return self._generate_once(prompt, chat)
      except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
          if attempt == max_retries:
              raise
          if isinstance(e, httpx.HTTPStatusError):
              if e.response.status_code < 500 and e.response.status_code != 429:
                  raise  # Don't retry 4xx except 429
              if e.response.status_code == 429:
                  delay = float(e.response.headers.get("Retry-After", base_delay * 2))
              else:
                  delay = base_delay * (2 ** attempt)
          else:  # TimeoutException
              delay = base_delay * (2 ** attempt)
          logger.warning("Gemini request failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
          time.sleep(delay)  # IMPORTANT: ai.py is synchronous — use time.sleep, NOT asyncio.sleep
  ```

### Idempotency for `/questions/generate`
- **Idempotency key**: Optional `Idempotency-Key` header on `POST /questions/generate`
- **Storage**: `question_tickets.idempotency_key` column with **composite unique index** `(student_id, idempotency_key) WHERE idempotency_key IS NOT NULL`
- **Behavior**: **Claim-then-generate pattern** — atomic INSERT ... ON CONFLICT claims key; concurrent duplicate waits for first request to complete and reuses its ticket (no duplicate Gemini call)
- **TTL**: Same as ticket (30 minutes)
- **Scope**: Only for `/questions/generate` (non-idempotent by nature); other endpoints don't need it

### Chat Retry
- **Do NOT retry** chat (`_generate_chat`) — conversations are not idempotent
- **Only retry** `_generate` (used by explain, hint, progressive_hint, interpret_performance, generate_question)

---

## 5. Circuit Breaker

### Evaluation

**Arguments FOR**:
- Prevents cascade failures when Gemini is down
- Reduces latency for clients (fail fast instead of waiting for timeout)
- Allows Gemini recovery time

**Arguments AGAINST**:
- Current: Single attempt → 503 already fails fast (15s timeout)
- Adds state management complexity
- In-memory breaker doesn't work across workers (would need DB-backed)
- Gemini outages are rare; 503 degradation already protects core platform
- 327 tests pass without it

### Recommendation: **DEFER CIRCUIT BREAKER**

**Rationale**: 
- Current fail-closed design (503 on any failure) already meets Phase 4 completion criteria
- Circuit breaker adds significant complexity (shared state, half-open logic, testing)
- Can be added in Phase 5 if production metrics show need
- Not a P0 blocker for reliability

**If implemented later**:
- State: In-memory per-process (acceptable for circuit breaker — false positive = brief 503, false negative = brief timeout)
- Failure threshold: 5 consecutive failures
- Recovery timeout: 60 seconds
- Half-open: Allow 1 request through; success → closed, failure → open

---

## 6. Token Usage Tracking

### Current State
- No token usage logging
- Gemini response includes `usageMetadata` with `promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`

### Proposed Logging
- **File**: `backend/app/services/ai.py`
- **Log location**: After successful response in `_generate()` and `_generate_chat()`
- **Log format** (structured JSON logging, no secrets):
  ```json
  {
    "timestamp": "2026-11-01T12:00:00Z",
    "level": "INFO",
    "logger": "skillsprint.ai",
    "message": "gemini_usage",
    "model": "gemini-2.0-flash",
    "operation": "explain",
    "prompt_tokens": 150,
    "completion_tokens": 80,
    "total_tokens": 230,
    "user_id": 42
  }
  ```
  Corresponding Python:
  ```python
  logger.info(
      "gemini_usage",
      extra={
          "model": model_name,
          "operation": operation_name,  # "explain", "hint", "chat", "generate_question"
          "prompt_tokens": usage.prompt_token_count,
          "completion_tokens": usage.candidates_token_count,
          "total_tokens": usage.total_token_count,
          "user_id": user_id,  # when available
      }
  )
  ```
- **Handling missing metadata**: Log `null` values for token counts; don't crash
- **Cost estimation**: NOT in this phase (Phase 5+ daily budget)
- **Privacy**: No prompt/response text logged; only counts

---

## 7. AI Request/Response Validation

### Current Validation
- **Generate**: `_parse_question_json()` validates structure (4 options, distinct, correct in options, non-empty)
- **Evaluate**: Deterministic string match; ticket validates ownership/expiry
- **Chat**: Pydantic schema validates history (max 10 turns, 2000 chars each)

### Gaps to Address
| Endpoint | Gap | Fix |
|----------|-----|-----|
| All | Empty Gemini response (`candidates` missing/empty) | Check `data.get("candidates")` exists and non-empty |
| All | Missing `content.parts[0].text` | Safe navigation with defaults |
| Generate | Invalid difficulty from client | Already validated by Pydantic schema |
| Generate | Malformed JSON retry already exists | Keep; add logging |
| Evaluate | `time_taken_seconds` out of range | Already validated by Pydantic (0-3600) |

### Implementation
- **File**: `backend/app/services/ai.py`
- **Changes**: Add defensive checks in `_generate()` and `_generate_chat()` for response structure
- **No contract changes**: All validation produces same 503 error

---

## 8. AI Contract and Regression Tests

### Current Coverage
- `test_ai.py`: 14 tests (endpoints, auth, 503 degradation)
- `test_ai_questions.py`: 20 tests (generation, evaluation, rate limit, RBAC)
- **Total**: 34 AI tests

### New Tests Required (40+ mocked tests)

| Category | Tests |
|----------|-------|
| **Retry logic** | 4 |
| **Token logging** | 2 |
| **Config validation** | 3 |
| **Ticket store (DB)** | 8 |
| **Rate limiter (DB)** | 6 |
| **Idempotency** | 3 |
| **Contract (all 7 endpoints)** | 10 |
| **PostgreSQL concurrency (integration)** | 4 |

### Test File
- **File**: `backend/tests/test_ai_reliability.py` (new)
- **Fixtures**: Reuse `client`, `db`, `student_token`, `mock_gemini` from `conftest.py`
- **Patterns**: Follow existing `test_ai.py` and `test_ai_questions.py` style

### PostgreSQL Concurrency Tests (New)
Since SQLite cannot test true concurrency behavior, dedicated PostgreSQL integration tests are required:

| Test | Description |
|------|-------------|
| `test_rate_limiter_concurrent_requests_atomic` | 20 concurrent requests for same user; verify exactly 10 pass (limit enforced atomically via advisory lock) |
| `test_idempotency_concurrent_generate` | 5 concurrent requests with same idempotency key; verify exactly 1 Gemini call, all return same ticket |
| `test_ticket_consume_concurrent` | 2 concurrent `consume` calls for same ticket; verify exactly 1 succeeds, other returns None |
| `test_rate_limiter_sliding_window_boundary` | Requests at window boundary; verify sliding window correctly enforced |

**Implementation notes**:
- Use `threading` or `asyncio` with real PostgreSQL test database
- Tests marked with `@pytest.mark.postgresql` to run only against PostgreSQL (not SQLite)
- Use fixed time manipulation (not `time.sleep`) for window boundary tests
- Each test runs in its own transaction (rolled back)

---

## 9. Frontend Compatibility

### Verification
- **Field**: `recorded_only_answer: boolean` in `AIQuestionEvaluateResult`
- **Location**: `frontend/src/types/index.ts:550`
- **Status**: ✅ Already present
- **Backend**: `ai_questions.py:353` returns `"recorded_only_answer": True`
- **Action**: No changes needed

### Contract Check
All frontend consumers of AI endpoints match backend response schemas:
- `/explain`, `/hint`, `/hints/progressive`, `/performance-interpretation` → `{text: string}`
- `/chat` → `{reply: string, model: string}`
- `/questions/generate` → `{question, options, ticket, topic_id, topic_name, company, difficulty, persisted}`
- `/questions/evaluate` → `AIQuestionEvaluateResult` (includes `recorded_only_answer`)

---

## 10. Service-Layer Dataclass Consistency

### Service-Layer `QuestionTicket` Dataclass (Updated)

The service-layer dataclass in `ai_tickets.py` must be updated to include all fields needed by the service architecture:

```python
# backend/app/services/ai_tickets.py (service-layer dataclass)
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class QuestionTicket:
    """Service-layer representation of an AI question ticket."""
    student_id: int
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: Optional[str]
    topic_id: Optional[int]
    topic_name: Optional[str]
    difficulty: str
    expires_at: float  # Unix timestamp
    
    # New fields for idempotency support
    idempotency_key: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
```

**Relationship Mapping:**
| SQLAlchemy Model | Service Dataclass | API Response |
|-----------------|------------------|--------------|
| `id` | `id` | Not exposed |
| `ticket_id` | (used as key) | `ticket` |
| `student_id` | `student_id` | Not exposed |
| `question_text` | `question_text` | `question` |
| `options` | `options` | `options` |
| `correct_answer` | `correct_answer` | Never exposed to student |
| `explanation` | `explanation` | `explanation` (on evaluate) |
| `topic_id` | `topic_id` | `topic_id` |
| `topic_name` | `topic_name` | `topic_name` |
| `difficulty` | `difficulty` | `difficulty` |
| `expires_at` | `expires_at` (timestamp) | Not exposed |
| `consumed_at` | (checked internally) | Not exposed |
| `idempotency_key` | `idempotency_key` | Not exposed |
| `created_at` | `created_at` | Not exposed |

**Critical Security Rule**: `correct_answer` and `explanation` are NEVER included in `/questions/generate` response. They are only revealed in `/questions/evaluate` after the student submits an answer.

---

## 11. Files Expected to Change

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/core/config.py` | Modify | Add `GEMINI_MODEL`, `AI_TIMEOUT_S` |
| `backend/app/services/ai.py` | Modify | Configurable timeout/model, retry logic (time.sleep), token logging (structured), response validation |
| `backend/app/models/__init__.py` | Modify | Import new models |
| `backend/app/models/question_ticket.py` | New | `QuestionTicket` model with `idempotency_key`, composite unique index |
| `backend/app/models/ai_rate_limit.py` | New | `AIRateLimit` model |
| `backend/app/services/ai_tickets.py` | Modify | Replace `TicketStore` with `DatabaseTicketStore`; update service-layer `QuestionTicket` dataclass |
| `backend/app/core/rate_limit.py` | Modify | Replace `SlidingWindowLimiter` with `DatabaseRateLimiter` (advisory lock) |
| `backend/app/services/ai_questions.py` | Modify | Add idempotency key support in `generate_question` |
| `backend/app/api/routes/ai.py` | Modify | Accept `Idempotency-Key` header on `/questions/generate` |
| `backend/alembic/versions/xxx_add_question_tickets.py` | New | Migration for tickets table (runs first) |
| `backend/alembic/versions/xxx_add_ai_rate_limits.py` | New | Migration for rate limits table (runs second, depends on tickets) |
| `backend/tests/test_ai_reliability.py` | New | 40+ new mocked tests + PostgreSQL concurrency tests |
| `backend/tests/conftest.py` | Modify | Add fixtures for new models |
| `backend/.env.example` | Modify | Document new env vars |

---

## Implementation Order

1. **Config & Models** (Day 1): Add settings, create models, generate migrations (question_tickets first, then ai_rate_limits)
2. **Database Ticket Store** (Day 1-2): Implement `DatabaseTicketStore` with claim-then-generate idempotency, swap instance
3. **Database Rate Limiter** (Day 2): Implement `DatabaseRateLimiter` with PostgreSQL advisory locks, swap instance
4. **Retry & Validation** (Day 2-3): Add retry logic (time.sleep), response validation, structured token logging
5. **Idempotency** (Day 3): Add idempotency key to generate endpoint (header → service → DB composite unique index)
6. **Tests** (Day 3-4): Write 40+ new tests including PostgreSQL concurrency tests, run full regression
7. **Documentation** (Day 4): Update `.env.example`, verify frontend build

---

## Deferred Features

| Feature | Reason |
|---------|--------|
| Circuit breaker | Current 503 degradation sufficient; adds complexity |
| Daily cost budget | Requires token logging first; Phase 5 |
| Per-user rate limit tiers | 10/min sufficient for study use |
| Model routing | Single model adequate |
| Real Gemini contract tests | Cost, flakiness; opt-in CI only |
| AI response caching | Low hit rate expected |
| Redis infrastructure | Not needed; DB-backed works |

---

## Rollback Procedure

See `PHASE_4_ROLLBACK_PLAN.md` for detailed steps.

**Summary**: 
1. Revert `question_ticket_store` to in-memory `TicketStore`
2. Revert `ai_limiter` to in-memory `SlidingWindowLimiter`
3. Revert `ai.py` to hardcoded timeout/model, no retry, no token logging
4. Run alembic downgrade for two new migrations
5. Verify 327 tests pass

---

## Confirmation

**No application code, tests, dependencies, or configuration were modified during planning.** This document is a plan only, awaiting approval.