# Phase 4 Test Plan

**Generated**: 2026-11-01  
**Based on**: PHASE_4_IMPLEMENTATION_PLAN.md, PHASE_4_DATABASE_DESIGN.md, PHASE_4_API_CONTRACT_PLAN.md, PHASE_4_VALIDATION_CHECKLIST.md  
**Status**: PLANNING PHASE — Awaiting approval  
**Last Updated**: 2026-11-01 (corrected for atomic rate limiting, student-scoped idempotency, claim-then-generate, PostgreSQL concurrency tests)

---

## Overview

This plan defines the test strategy for Phase 4 reliability and contract improvements. Tests are split into two categories:

1. **SQLite-compatible mocked tests** (`test_ai_reliability.py`) — run in standard CI with SQLite
2. **PostgreSQL-specific concurrency tests** (`test_ai_reliability_pg.py`) — require dedicated PostgreSQL test database

**Target**: 40+ new mocked tests + 8 PostgreSQL concurrency tests added to existing 34 AI tests.

### Current Test Baseline
- `test_ai.py`: 14 tests (endpoints, auth, 503 degradation)
- `test_ai_questions.py`: 20 tests (generation, evaluation, rate limit, RBAC)
- **Total**: 34 AI tests
- **Full suite**: 327 tests pass

### Test Philosophy
- **No network calls**: All Gemini responses mocked via `httpx` mock transport
- **Database-backed tests**: Use existing `db` fixture (transactional rollback)
- **Isolated**: Each test independent; no shared state
- **Fast**: Unit tests <100ms each; integration tests <500ms
- **PostgreSQL tests**: Explicitly marked, never silently fall back to SQLite

---

## Test Files

### 1. `backend/tests/test_ai_reliability.py` (SQLite-compatible)

**Structure**:
```python
"""
Phase 4 reliability tests: retry, config, token logging, DB-backed stores.
All Gemini calls mocked — no network.
SQLite-compatible: uses existing `db` fixture with transactional rollback.
"""
import pytest
from unittest.mock import AsyncMock, patch

# Fixtures reused from conftest.py:
# - client: TestClient
# - db: Session
# - student_token, teacher_token, admin_token
# - mock_gemini: httpx mock transport
```

### 2. `backend/tests/test_ai_reliability_pg.py` (PostgreSQL-only)

**Structure**:
```python
"""
Phase 4 PostgreSQL concurrency tests: atomic rate limiting, idempotency, ticket consumption.
Requires dedicated PostgreSQL test database.
NEVER falls back to SQLite — marked with @pytest.mark.postgresql
"""
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Fixtures:
# - pg_db: Session bound to PostgreSQL test database (not SQLite)
# - pg_student_token: authenticated student for PG tests
# - mock_gemini: httpx mock transport
```

**Prerequisites**:
- Dedicated PostgreSQL test database (e.g., `skillsprint_test_pg`)
- `DATABASE_URL` or `TEST_DATABASE_URL` points to PostgreSQL
- Run with: `pytest -m postgresql backend/tests/test_ai_reliability_pg.py`

## Test Categories

### A. Configuration Tests (3 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_custom_model_used` | `GEMINI_MODEL=gemini-1.5-flash` → request uses that model |
| `test_custom_timeout_used` | `AI_TIMEOUT_S=30` → httpx timeout = 30s |
| `test_invalid_timeout_clamped` | `AI_TIMEOUT_S=0` → clamped to 1.0; `AI_TIMEOUT_S=100` → clamped to 60.0; invalid values logged at WARNING |

### B. Gemini Retry Logic Tests (6 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_retry_on_timeout_then_success` | First call timeout, second succeeds → returns text |
| `test_retry_on_5xx_then_success` | First call 500, second succeeds → returns text |
| `test_retry_on_429_then_success` | First call 429 with `Retry-After`, second succeeds → returns text, respects `Retry-After` header |
| `test_no_retry_on_400` | 400 Bad Request → immediate 503, no retry |
| `test_no_retry_on_401_403` | 401/403 → immediate 503, no retry |
| `test_malformed_json_no_retry` | Malformed JSON response (missing candidates/parts/text) → immediate 503, no retry |
| `test_max_retries_exhausted_returns_503` | Two consecutive timeouts → 503 |
| `test_retry_uses_time_sleep` | Retry delay uses `time.sleep` (synchronous), NOT `asyncio.sleep` |

**Implementation Pattern**:
```python
def test_retry_on_timeout_then_success(mock_gemini, student_token):
    # First response: timeout exception
    # Second response: valid Gemini response
    mock_gemini.side_effect = [
        httpx.TimeoutException("timeout"),
        httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
    ]
    
    response = client.post("/ai/explain", json={...}, headers=auth_header(student_token))
    assert response.status_code == 200
    assert mock_gemini.call_count == 2
```

```python
def test_retry_on_429_respects_retry_after(mock_gemini, student_token):
    mock_gemini.side_effect = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
    ]
    
    with patch("time.sleep") as mock_sleep:
        response = client.post("/ai/explain", json={...}, headers=auth_header(student_token))
        assert response.status_code == 200
        # Verify sleep was called with ~2 seconds (Retry-After value)
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] >= 1.5 and mock_sleep.call_args[0][0] <= 2.5
```

### C. Token Usage Logging Tests (3 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_token_usage_logged_on_success` | Structured JSON log contains model, operation, prompt_tokens, completion_tokens, total_tokens, user_id |
| `test_missing_usage_metadata_handled` | No `usageMetadata` in response → logs null for token counts, no crash |
| `test_logging_failure_does_not_break_response` | Logger exception during token logging → AI response still returns successfully |

**Implementation**:
```python
def test_token_usage_logged_on_success(mock_gemini, student_token, caplog):
    mock_gemini.return_value = httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": "OK"}]}}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50, "totalTokenCount": 150}
    })
    
    with caplog.at_level(logging.INFO, logger="skillsprint.ai"):
        client.post("/ai/explain", ...)
    
    log_record = [r for r in caplog.records if r.message == "gemini_usage"][0]
    assert log_record.prompt_tokens == 100
    assert log_record.completion_tokens == 50
    assert log_record.total_tokens == 150
    assert log_record.operation == "explain"
    assert log_record.model == "gemini-2.0-flash"
    assert log_record.user_id is not None
```

```python
def test_logging_failure_does_not_break_response(mock_gemini, student_token, caplog):
    """If logger raises exception, AI response should still succeed."""
    mock_gemini.return_value = httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": "OK"}]}}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50, "totalTokenCount": 150}
    })
    
    with patch("app.services.ai.logger.info", side_effect=Exception("Logger failed")):
        response = client.post("/ai/explain", json={...}, headers=auth_header(student_token))
        assert response.status_code == 200
```

### D. PostgreSQL Ticket Store Tests (8 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_ticket_persisted_across_restart` | Issue ticket, simulate new process (new session), consume → works |
| `test_ticket_expiry_enforced` | Ticket created with past `expires_at` → consume returns None |
| `test_ticket_single_use` | Consume twice → second returns None |
| `test_ticket_user_isolation` | Student A's ticket consumed by Student B → None |
| `test_ticket_consumed_at_set` | After consume, `consumed_at` populated |
| `test_ticket_cleanup_removes_expired` | Prune removes expired tickets |
| `test_ticket_per_student_limit_enforced` | 21st ticket for same student evicts oldest unconsumed |
| `test_ticket_idempotency_key_deduplication` | Same student + same idempotency key → returns existing ticket |

**Fixtures**:
```python
@pytest.fixture
def ticket_store(db):
    return DatabaseTicketStore(db)
```

### E. Atomic Rate Limiter Tests (6 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_rate_limit_allows_under_limit` | 9 requests → all pass |
| `test_rate_limit_blocks_at_limit` | 10th request → 429 |
| `test_rate_limit_window_sliding` | 10 requests, wait 61s → 11th passes |
| `test_rate_limit_per_user_isolation` | User A at limit, User B → passes |
| `test_rate_limit_db_failure_returns_503` | DB error → 503 (not 429) |
| `test_rate_limit_concurrent_requests` | 20 concurrent requests, limit 10 → exactly 10 accepted (no race condition) |

**Concurrency Test Pattern** (SQLite-compatible, uses threading):
```python
import threading

def test_rate_limit_concurrent_requests(limiter):
    results = []
    errors = []
    def make_request():
        try:
            limiter.check(1)
            results.append("ok")
        except RateLimitExceededError:
            results.append("limited")
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=make_request) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert len(errors) == 0, f"Unexpected errors: {errors}"
    assert results.count("ok") == 10, f"Expected exactly 10 ok, got {results.count('ok')}"
```

### F. Idempotency Tests (9 tests) — `test_ai_reliability.py` + `test_ai_reliability_pg.py`

**SQLite-compatible tests** (`test_ai_reliability.py`):
| Test | Description |
|------|-------------|
| `test_idempotent_generate_returns_same_ticket` | Same student + same key → same ticket_id |
| `test_idempotent_generate_no_duplicate_gemini_call` | Mock Gemini called once for duplicate key |
| `test_idempotency_expired_allows_new` | Key expired (past `expires_at`) → new ticket generated |
| `test_idempotency_different_students_same_key` | Student A and Student B use same key → different tickets |
| `test_idempotency_different_keys_same_student` | Same student uses different keys → different tickets |
| `test_idempotency_null_key` | NULL/missing key → normal behavior (new ticket every time) |

**PostgreSQL-specific tests** (`test_ai_reliability_pg.py`):
| Test | Description |
|------|-------------|
| `test_idempotency_concurrent_duplicate_requests` | 5 concurrent requests with same student+key → exactly 1 Gemini call, all return same ticket |
| `test_idempotency_gemini_failure_releases_claim` | Concurrent request claims key, Gemini fails → placeholder deleted, key available for retry |
| `test_idempotency_stale_claim_recovery` | Placeholder row exists but stuck (no completion) → poll timeout → 503, key available for retry |

### G. Concurrent Ticket Consumption Tests (1 test) — `test_ai_reliability_pg.py`

| Test | Description |
|------|-------------|
| `test_concurrent_consume_single_ticket` | 10 concurrent consume attempts on one ticket → exactly 1 succeeds, 9 return None |

### H. Contract Tests for All 7 Endpoints (10 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_missing_api_key_returns_503_all_endpoints` | Unset `GEMINI_API_KEY` → 503 on all 7 |
| `test_successful_response_all_endpoints` | Each endpoint returns expected schema |
| `test_timeout_returns_503_all_endpoints` | Mock timeout → 503 |
| `test_provider_5xx_returns_503_all_endpoints` | Mock 500 → 503 |
| `test_provider_429_returns_503_all_endpoints` | Mock 429 → 503 (not 429 to client) |
| `test_malformed_response_returns_503` | Missing candidates → 503 |
| `test_empty_response_returns_503` | Empty candidates array → 503 |
| `test_rate_limit_headers_present` | `X-RateLimit-Limit`, `Remaining`, `Reset` in response |
| `test_student_only_all_endpoints` | Teacher/admin → 403 |
| `test_auth_required_all_endpoints` | No token → 401 |

### I. Integration Tests (4 tests) — `test_ai_reliability.py`

| Test | Description |
|------|-------------|
| `test_ai_question_flow_generate_evaluate_correct` | Full flow: generate → evaluate correct → XP awarded |
| `test_ai_question_flow_generate_evaluate_wrong` | Wrong answer → hint generated, no XP |
| `test_ai_question_never_persisted_to_db` | No `Question` row created |
| `test_ai_answer_log_created` | `AIAnswerLog` row with correct fields |

### J. PostgreSQL Concurrency Tests (8 tests) — `test_ai_reliability_pg.py`

**Requirements**: Dedicated PostgreSQL test database, `@pytest.mark.postgresql`, independent sessions, mock Gemini, cleanup test-created data only.

| Test | Description |
|------|-------------|
| `test_rate_limiter_concurrent_requests_atomic` | 20 concurrent requests for same user; verify exactly 10 pass (atomic via advisory lock) |
| `test_idempotency_concurrent_generate` | 5 concurrent requests with same student+key; verify exactly 1 Gemini call, all return same ticket |
| `test_ticket_consume_concurrent` | 10 concurrent consume calls for same ticket; verify exactly 1 succeeds, 9 return None |
| `test_rate_limiter_sliding_window_boundary` | Requests at window boundary; verify sliding window correctly enforced |
| `test_rate_limiter_multiple_sessions` | Multiple independent DB sessions for same user; verify limit enforced across sessions |
| `test_rate_limiter_repeated_execution` | Repeat 20-concurrent test 10 times; verify exactly 10 pass every iteration (no flakiness) |
| `test_idempotency_gemini_failure_placeholder_cleanup` | Concurrent duplicate: first fails after claim → placeholder deleted → retry succeeds |
| `test_ticket_per_student_limit_concurrent` | 15 concurrent ticket issues for same student, limit 10 → exactly 10 tickets created |

---

## Test File Summary

| File | Tests | Database | Purpose |
|------|-------|----------|---------|
| `test_ai_reliability.py` | ~35 | SQLite (transactional) | Config, retry, token logging, ticket store, rate limiter (basic), idempotency (basic), contracts, integration |
| `test_ai_reliability_pg.py` | 8 | PostgreSQL only | Atomic rate limiting, idempotency concurrency, ticket consume concurrency, repeated execution for race detection |

**Total new tests**: ~43 (35 SQLite-compatible + 8 PostgreSQL-only)

## Fixtures Required

### `conftest.py` Additions (Shared)

```python
# Mock Gemini transport
@pytest.fixture
def mock_gemini():
    with patch("httpx.AsyncClient") as mock_client:
        yield mock_client.return_value

# Database ticket store (SQLite-compatible)
@pytest.fixture
def db_ticket_store(db):
    from app.services.ai_tickets import DatabaseTicketStore
    return DatabaseTicketStore(db)

# Database rate limiter (SQLite-compatible)
@pytest.fixture
def db_rate_limiter(db):
    from app.core.rate_limit import DatabaseRateLimiter
    return DatabaseRateLimiter(db, max_requests=10, window_seconds=60.0)

# Settings override for config tests
@pytest.fixture
def custom_settings():
    from app.core.config import Settings
    original = Settings()
    # Use monkeypatch or override
    with patch("app.services.ai.settings", Settings(GEMINI_MODEL="gemini-test", AI_TIMEOUT_S=5.0)):
        yield
```

### `conftest.py` Additions (PostgreSQL-specific)

```python
# PostgreSQL test database session
# Requires TEST_DATABASE_URL pointing to PostgreSQL (not SQLite)
@pytest.fixture(scope="session")
def pg_engine():
    """Create PostgreSQL engine for concurrency tests."""
    from sqlalchemy import create_engine
    from app.core.config import settings
    
    # Use TEST_DATABASE_URL or construct from settings
    db_url = getattr(settings, "TEST_DATABASE_URL", None) or settings.DATABASE_URL
    if "sqlite" in db_url:
        pytest.skip("PostgreSQL required for concurrency tests")
    
    engine = create_engine(db_url, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture
def pg_db(pg_engine):
    """PostgreSQL session with transactional rollback."""
    from sqlalchemy.orm import Session
    connection = pg_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

# PostgreSQL ticket store (for concurrency tests)
@pytest.fixture
def pg_ticket_store(pg_db):
    from app.services.ai_tickets import DatabaseTicketStore
    return DatabaseTicketStore(pg_db)

# PostgreSQL rate limiter (for concurrency tests)
@pytest.fixture
def pg_rate_limiter(pg_db):
    from app.core.rate_limit import DatabaseRateLimiter
    return DatabaseRateLimiter(pg_db, max_requests=10, window_seconds=60.0)

# PostgreSQL student token
@pytest.fixture
def pg_student_token(pg_db, client):
    """Create and authenticate a test student in PostgreSQL."""
    from tests.conftest import create_test_student, auth_header
    student = create_test_student(pg_db)
    return auth_header(student.token)
```

### Pytest Markers

```python
# In conftest.py or pytest.ini
pytestmark = [
    pytest.mark.postgresql,  # Applied to test_ai_reliability_pg.py
]

# In test_ai_reliability_pg.py:
# import pytest
# pytestmark = pytest.mark.postgresql
```

---

## Test Execution Commands

### Backend Tests (SQLite-based — Standard CI)

```bash
# Run all backend tests (existing + new SQLite-compatible)
cd backend
python -m pytest -q
# Target: 327 + 43 = 370 tests pass

# Run only new reliability tests (SQLite-compatible)
cd backend
python -m pytest tests/test_ai_reliability.py -v

# Run all AI-related tests (existing + new)
cd backend
python -m pytest tests/test_ai.py tests/test_ai_questions.py tests/test_ai_reliability.py -v

# Run with coverage
cd backend
python -m pytest --cov=app --cov-report=term-missing
```

### PostgreSQL Concurrency Tests (Dedicated PostgreSQL Required)

```bash
# Set PostgreSQL test database URL (one-time setup)
export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/skillsprint_test_pg"

# Run PostgreSQL-only concurrency tests
cd backend
python -m pytest tests/test_ai_reliability_pg.py -v -m postgresql

# Run with explicit database URL override
cd backend
TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/skillsprint_test_pg" \
python -m pytest tests/test_ai_reliability_pg.py -v
```

### Frontend Tests

```bash
# TypeScript type checking (no emit)
cd frontend
npx tsc --noEmit

# Production build
cd frontend
npm run build

# Lint (if configured)
cd frontend
npm run lint
```

### Combined Verification (Pre-merge Checklist)

```bash
# Backend full test suite
cd backend && python -m pytest -q

# PostgreSQL concurrency tests (if PG available)
cd backend && TEST_DATABASE_URL="postgresql://..." python -m pytest tests/test_ai_reliability_pg.py -v -m postgresql

# Frontend TypeScript check
cd frontend && npx tsc --noEmit

# Frontend production build
cd frontend && npm run build

# All must pass before merge
```

---

## Test Coverage Goals

| Area | Before | After | Target |
|------|--------|-------|--------|
| Configuration | 0 | 3 | 3 |
| Retry logic | 0 | 6 | 6 |
| Token logging | 0 | 3 | 3 |
| DB ticket store | 0 | 8 | 8 |
| DB rate limiter | 0 | 6 | 6 |
| Idempotency (SQLite) | 0 | 6 | 6 |
| Idempotency (PG concurrency) | 0 | 3 | 3 |
| Contract (7 endpoints) | Partial | 10 | 10 |
| Integration flows | 2 | 4 | 4 |
| Concurrent ticket consumption | 0 | 1 | 1 |
| PG rate limiter atomicity | 0 | 4 | 4 |
| PG repeated execution | 0 | 1 | 1 |
| **Total new (SQLite)** | **34** | **73** | **~39 new** |
| **Total new (PG only)** | **0** | **8** | **8 PG-only** |

---

## Regression Testing

### Backend Regression
- All existing 327 tests must pass
- All 34 existing AI tests (`test_ai.py`, `test_ai_questions.py`) must pass
- New SQLite-compatible tests (`test_ai_reliability.py`) must pass
- No new test dependencies or external services required

### PostgreSQL Concurrency Regression
- All 8 PostgreSQL-specific tests must pass against real PostgreSQL
- Tests must be re-runnable without manual cleanup (transactional rollback)
- Repeated execution test validates no race conditions over 10 iterations

### Frontend Regression
- **TypeScript compilation**: `npx tsc --noEmit` — zero errors
- **Production build**: `npm run build` — succeeds
- **API contract compatibility**: All existing frontend API calls work unchanged
- **No new frontend dependencies** required for Phase 4

### API Contract Compatibility
- All 7 existing AI endpoints return identical response schemas
- Error envelopes unchanged (`success`, `error.code`, `error.message`, `data`)
- HTTP status codes unchanged (503, 429, 401, 403, 422, 404)
- Optional `Idempotency-Key` header on `/questions/generate` only
- Optional rate limit headers (`X-RateLimit-*`) on all AI responses

---

## Mocking Strategy

### Gemini Response Mocker

```python
# conftest.py helper
def mock_gemini_response(text: str, usage: dict | None = None, status: int = 200):
    response_data = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    if usage:
        response_data["usageMetadata"] = usage
    return httpx.Response(status, json=response_data)

def mock_gemini_error(status: int, text: str = "Error"):
    return httpx.Response(status, text=text)
```

### Usage in Tests

```python
def test_explain_success(mock_gemini, student_token):
    mock_gemini.post.return_value = mock_gemini_response("Step by step...")
    
    response = client.post("/ai/explain", json={...}, headers=auth_header(student_token))
    
    assert response.status_code == 200
    assert response.json()["data"]["text"] == "Step by step..."
    mock_gemini.post.assert_called_once()
```

---

## Performance Benchmarks (Non-Functional)

| Metric | Target |
|--------|--------|
| Single test duration | < 100ms |
| Full AI test suite | < 10s |
| Full backend suite | < 120s |
| DB ticket store ops | < 5ms p99 |
| DB rate limiter check | < 10ms p99 |

---

## CI Integration

- No new CI steps — tests run in existing `pytest` job
- No secrets required — all mocked
- No external dependencies

---

## Confirmation

**No tests were written or modified during planning.** This is a test plan only.