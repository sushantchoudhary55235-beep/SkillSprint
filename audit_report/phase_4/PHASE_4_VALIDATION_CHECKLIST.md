# Phase 4 Validation Checklist

**Generated**: 2026-11-01  
**Scope**: Read-only validation of Phase 4 investigation findings  
**Status**: All validation checks completed  
**Last Updated**: 2026-11-01 (corrected for atomic rate limiting, claim-then-generate idempotency, PostgreSQL concurrency tests)

---

## Validation Summary

| Check | Status | Details |
|-------|--------|---------|
| 1. Config Validation (AI_TIMEOUT_S, GEMINI_MODEL, AI_COST_BUDGET_DAILY missing) | ✅ CONFIRMED | None present in config.py |
| 2. Reliability Gap (no retry, circuit breaker, token logging) | ✅ CONFIRMED | ai.py has none |
| 3. State Gap (in-memory only, Redis in docs only) | ✅ CONFIRMED | ai_tickets.py, rate_limit.py in-memory |
| 4. Contract Gap (recorded_only_answer in frontend types) | ⚠️ ALREADY FIXED | Present in AIQuestionEvaluateResult |
| 5. Test Coverage Delta (AI test count) | ✅ VERIFIED | 34 AI tests (14 test_ai.py + 20 test_ai_questions.py) |
| 6. No Redis Runtime (requirements, Docker, code) | ✅ CONFIRMED | No Redis in requirements.txt, no Docker files |
| 7. Frontend Build Success | ✅ PASS | npm run build: 407KB JS, 109KB gzipped |
| 8. Frontend TypeScript Check | ✅ PASS | npx tsc --noEmit: No errors |
| 9. Full Backend Regression | ✅ PASS | 327/327 tests pass |

---

## 1. Config Validation

**File checked**: `backend/app/core/config.py`

**Settings currently present**:
- `GEMINI_API_KEY` (line 36)
- `AI_RATE_LIMIT_PER_MINUTE` (line 42)

**Settings NOT present (confirmed missing)**:
- ❌ `AI_TIMEOUT_S` — timeout is hardcoded as `_TIMEOUT_S = 15.0` in `ai.py:26`
- ❌ `GEMINI_MODEL` — model is hardcoded as `"gemini-2.0-flash"` in `ai.py:60,222`
- ❌ `AI_COST_BUDGET_DAILY` — no cost budget tracking exists

**Evidence**:
```bash
$ grep -n "AI_TIMEOUT_S\|GEMINI_MODEL\|AI_COST_BUDGET_DAILY" backend/app/core/config.py
# No output (exit code 1)

$ grep -n "_TIMEOUT_S\|gemini-2.0-flash" backend/app/services/ai.py
backend/app/services/ai.py:26:_TIMEOUT_S = 15.0
backend/app/services/ai.py:60:        url = _GEMINI_URL.format(model="gemini-2.0-flash")
backend/app/services/ai.py:71:                timeout=_TIMEOUT_S,
backend/app/services/ai.py:82:            logger.warning("Gemini request failed for model gemini-2.0-flash")
backend/app/services/ai.py:222:        url = _GEMINI_URL.format(model="gemini-2.0-flash")
backend/app/services/ai.py:233:                timeout=_TIMEOUT_S,
backend/app/services/ai.py:244:            logger.warning("Gemini chat request failed for model gemini-2.0-flash")
```

---

## 2. Reliability Gap Confirmation

**File checked**: `backend/app/services/ai.py`

**Missing reliability features** (confirmed absent):
- ❌ **Retry logic** — No `retry`, `Retry`, `backoff`, `exponential` references
- ❌ **Circuit breaker** — No `circuit`, `Circuit`, `breaker`, `Breaker` references
- ❌ **Token usage logging** — No `usageMetadata`, `usage_metadata`, `token.*usage` references

**Evidence**:
```bash
$ grep -n "retry\|Retry\|circuit\|Circuit\|breaker\|Breaker\|usageMetadata\|usage_metadata\|token.*usage" backend/app/services/ai.py
# No output (exit code 1)
```

**Current behavior**: Single attempt with hardcoded 15s timeout; ANY failure → 503 ServiceUnavailableError

---

## 3. State Gap Confirmation

### 3.1 Ticket Store (`backend/app/services/ai_tickets.py`)

**Implementation**: In-memory `dict` with `threading.Lock`
- `question_ticket_store = TicketStore()` at module level (line 107)
- TTL: 30 minutes (constant `TTL_SECONDS = 30 * 60`)
- Per-student limit: 20 tickets (`_MAX_TICKETS_PER_STUDENT = 20`)
- Global limit: 10,000 tickets (`_MAX_TICKETS_TOTAL = 10_000`)

**Redis references**: NONE in code (only in audit docs)

### 3.2 Rate Limiter (`backend/app/core/rate_limit.py`)

**Implementation**: In-memory `defaultdict(deque)` with `threading.Lock`
- `ai_limiter = SlidingWindowLimiter(max_requests=settings.AI_RATE_LIMIT_PER_MINUTE)` (line 61)
- Sliding window: 60 seconds
- Default limit: 10 requests/minute

**Redis reference**: Line 9 — **comment only**: "interface can be backed by Redis without touching call sites"

**Evidence**:
```bash
$ grep -n "redis\|Redis\|REDIS" backend/app/services/ai_tickets.py backend/app/core/rate_limit.py
backend/app/core/rate_limit.py:9:interface can be backed by Redis without touching call sites.
```

---

## 4. Contract Gap Confirmation

**File checked**: `frontend/src/types/index.ts`

**Finding**: `recorded_only_answer: boolean` is **ALREADY PRESENT** in `AIQuestionEvaluateResult` interface (line 550)

**Type definition**:
```typescript
export interface AIQuestionEvaluateResult {
  is_correct: boolean
  correct_answer: string
  student_answer: string
  explanation: string | null
  hint: string | null
  xp_earned: number
  xp_total: number
  level: number
  level_up: {
    progress_percent: number
    xp_to_next_level: number
    current_level_floor: number
    next_level_xp: number
  }
  current_streak: number
  topic_accuracy: number | null
  overall_accuracy: number | null
  readiness_score: number
  recorded_only_answer: boolean  // ✅ PRESENT
}
```

**Status**: This contract gap was already addressed prior to Phase 4 validation. No action needed.

---

## 5. Test Coverage Delta

**Test files**: `backend/tests/test_ai.py` (14 tests) + `backend/tests/test_ai_questions.py` (20 tests)

**Total AI-related tests**: **34 tests**

### Test Breakdown

**test_ai.py** (Phase 14 - AI integration):
| Class | Tests |
|-------|-------|
| TestEndpoints | 5 |
| TestGracefulDegradation | 9 |
| **Subtotal** | **14** |

**test_ai_questions.py** (Phase 15C - AI question generation & evaluation):
| Class | Tests |
|-------|-------|
| TestGeneration | 11 |
| TestEvaluation | 7 |
| TestAIRateLimit | 2 |
| **Subtotal** | **20** |

**Note**: `test_integration_phase15.py` also contains AI-related tests but they are integration tests covering the full flow.

**Full backend suite**: 327 tests pass (verified)

---

## 6. No Redis Runtime Confirmation

### 6.1 Requirements Check

**File**: `backend/requirements.txt`

**Contents** (no Redis):
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
alembic==1.14.0
pydantic==2.10.4
pydantic-settings==2.7.0
email-validator==2.2.0
python-jose[cryptography]==3.3.0
bcrypt==4.2.1
python-multipart==0.0.20
psycopg[binary]==3.2.3
pytest==8.3.4
httpx==0.28.1
```

### 6.2 Docker/Compose Check

**Search result**: No Dockerfile, docker-compose.yml, or .dockerfile files in project root (excluding node_modules and .venv)

```bash
$ find . -name "Dockerfile*" -o -name "docker-compose*" -o -name "*.dockerfile" 2>/dev/null | grep -v ".venv" | grep -v "node_modules"
# No output
```

### 6.3 Redis Connection Code Check

**Search result**: No Redis connection code in backend Python files (excluding .venv and audit_report)

```bash
$ grep -r "redis\|Redis\|REDIS" --include="*.py" backend/ 2>/dev/null | grep -v ".venv" | grep -v "audit_report"
backend/app/core/rate_limit.py:9:interface can be backed by Redis without touching call sites.
```

**Only match**: Comment in rate_limit.py — no actual Redis client code.

---

## 7. Frontend Build Verification

**Command**: `npm run build` (in `frontend/`)

**Result**: ✅ **PASS**
```
> tsc -b && vite build
vite v6.4.3 building for production...
✓ 127 modules transformed.
dist/index.html                  0.40 kB │ gzip:   0.27 kB
dist/assets/index--aiPK68C.css  28.07 kB │ gzip:   5.31 kB
dist/assets/index-DsjAGugs.js  407.07 kB │ gzip: 109.53 kB
✓ built in 6.44s
```

---

## 8. Frontend TypeScript Check

**Command**: `npx tsc --noEmit` (in `frontend/`)

**Result**: ✅ **PASS**
```
TypeScript: No errors found
```

---

## 9. Full Backend Regression Test

**Command**: `python -m pytest -q` (in `backend/`)

**Result**: ✅ **PASS** — 327 tests passed, 1 warning (pydantic deprecation)
```
327 passed, 1 warning in 66.38s
```

---

## 10. Updated "No Redis" Argument — PostgreSQL-Backed State

Based on validation evidence, the case for **database-backed (PostgreSQL/SQLAlchemy) over Redis** is now empirically supported:

### Why DB-Backed is Correct for Current State

| Factor | Evidence | Conclusion |
|--------|----------|------------|
| **Existing infrastructure** | PostgreSQL + SQLAlchemy already in requirements.txt and used by all services | Zero new dependencies |
| **No Redis anywhere** | Not in requirements.txt, no Docker files, no connection code | Adding Redis = net new operational burden |
| **Single-worker default** | Project runs as single process (uvicorn); in-memory works for dev | DB-backed works for both single and multi-worker |
| **Survives restarts** | In-memory tickets/rate limits lost on restart | DB persists across deployments |
| **Horizontal scaling ready** | Same PostgreSQL used by all workers | No Redis cluster needed |
| **Ticket TTL** | Can use DB index + periodic cleanup or TTL column | Simpler than Redis EXPIRE |
| **Rate limit sliding window** | Can use timestamp column + window query | Standard SQL pattern |

### When Redis Would Be Appropriate (Future)
- Proven need for sub-millisecond latency on rate limit checks
- Millions of active users requiring distributed locking
- Existing Redis infrastructure already operated by team
- **None of these apply today**

### Recommended Implementation (Phase 4) — Corrected Design

1. **Ticket Store**: New `question_tickets` table with:
   - Columns: `id`, `student_id`, `ticket_id`, `payload` (JSONB), `expires_at`, `consumed_at`, `idempotency_key`, `created_at`
   - Composite unique index: `(student_id, idempotency_key) WHERE idempotency_key IS NOT NULL` for student-scoped idempotency
   - Index on `(student_id, expires_at)` for cleanup
   - Index on `(student_id, consumed_at)` for per-student limit enforcement
   - Service-layer `QuestionTicket` dataclass with `idempotency_key`, `id`, `created_at` fields

2. **Rate Limiter**: New `ai_rate_limits` table with:
   - Columns: `id`, `user_id`, `window_start`, `created_at`
   - **Atomic enforcement via `pg_advisory_xact_lock(user_id)`** — serializes per-user checks without table/row locks
   - Composite index: `(user_id, window_start)` for fast window queries
   - Index on `created_at` for cleanup

3. **Idempotency for `/questions/generate`**: **Claim-then-generate pattern**
   - `INSERT ... ON CONFLICT` on composite unique index `(student_id, idempotency_key)`
   - Placeholder row claims the key
   - If conflict: wait for completion (poll up to 30s), return existing ticket
   - If claim succeeds: call Gemini, update placeholder
   - If Gemini fails: DELETE placeholder, key available for retry

4. **Both**: Reuse existing SQLAlchemy session/engine — no new connection pools

---

## 11. Verification Commands for Reviewer

```bash
# 1. Config validation
grep -n "AI_TIMEOUT_S\|GEMINI_MODEL\|AI_COST_BUDGET_DAILY" backend/app/core/config.py
# Expected: no output

# 2. Reliability gaps
grep -n "retry\|circuit\|breaker\|usageMetadata" backend/app/services/ai.py
# Expected: no output

# 3. State gaps (Redis only in comment)
grep -n "redis\|Redis" backend/app/services/ai_tickets.py backend/app/core/rate_limit.py
# Expected: only comment line in rate_limit.py

# 4. Contract (already fixed)
grep -n "recorded_only_answer" frontend/src/types/index.ts
# Expected: line 550 in AIQuestionEvaluateResult

# 5. Test count
python -m pytest backend/tests/test_ai.py backend/tests/test_ai_questions.py --collect-only -q
# Expected: 34 tests collected

# 6. No Redis runtime
grep "redis" backend/requirements.txt
find . -name "Dockerfile*" -o -name "docker-compose*" | grep -v node_modules | grep -v .venv
# Expected: no output for both

# 7. Frontend build
cd frontend && npm run build
# Expected: success, ~407KB JS

# 8. TypeScript check
cd frontend && npx tsc --noEmit
# Expected: "TypeScript: No errors found"

# 9. Full regression
cd backend && python -m pytest -q
# Expected: 327 passed
```

---

## 12. Design Review Corrections Summary

Based on the final design review, the following corrections were applied to all Phase 4 planning documents:

| Correction | Applied To |
|------------|------------|
| **Atomic rate limiting**: PostgreSQL advisory locks (`pg_advisory_xact_lock`) replace COUNT+INSERT race-prone approach | RISK_ASSESSMENT (R1, R8), IMPLEMENTATION_PLAN, DATABASE_DESIGN, API_CONTRACT_PLAN, TEST_PLAN, ROLLBACK_PLAN |
| **Student-scoped idempotency**: Composite unique index `(student_id, idempotency_key) WHERE idempotency_key IS NOT NULL` — not global | API_CONTRACT_PLAN, DATABASE_DESIGN, IMPLEMENTATION_PLAN, TEST_PLAN, ROLLBACK_PLAN |
| **Claim-then-generate pattern**: `INSERT ... ON CONFLICT` with placeholder row, wait-for-completion, delete-on-failure | RISK_ASSESSMENT (R4), IMPLEMENTATION_PLAN, DATABASE_DESIGN, API_CONTRACT_PLAN, TEST_PLAN, ROLLBACK_PLAN |
| **Service-layer dataclass**: `QuestionTicket` with `idempotency_key`, `id`, `created_at` fields | DATABASE_DESIGN, IMPLEMENTATION_PLAN, ROLLBACK_PLAN |
| **PostgreSQL concurrency tests**: 8 dedicated tests in `test_ai_reliability_pg.py` (atomic rate limiting, idempotency concurrency, ticket consume concurrency, repeated execution) | TEST_PLAN, RISK_ASSESSMENT (R9), IMPLEMENTATION_PLAN |
| **Circuit breaker deferred**: Explicitly moved to Phase 5 | IMPLEMENTATION_PLAN, API_CONTRACT_PLAN, RISK_ASSESSMENT, ROLLBACK_PLAN |
| **Synchronous `time.sleep` in retry**: Not `asyncio.sleep` (threaded context) | IMPLEMENTATION_PLAN, TEST_PLAN |
| **Structured token logging**: Only counts (prompt/completion/total), model, operation, user_id — no text | RISK_ASSESSMENT (R5), IMPLEMENTATION_PLAN, TEST_PLAN |

---

## Sign-off

**All Phase 4 validation checks completed successfully.**

**Date**: 2026-11-01  
**Validated by**: Automated read-only checks + test execution  

**Key finding**: The `recorded_only_answer` contract field is already present in frontend types. The remaining Phase 4 work focuses on:
1. Adding configurable timeout, model, and cost budget to config
2. Implementing retry logic with exponential backoff (sync `time.sleep`)
3. **Circuit breaker deferred to Phase 5**
4. Logging token usage from `usageMetadata` (counts only, no text)
5. Migrating ticket store and rate limiter to database-backed implementations:
   - **Advisory lock rate limiting** (atomic, no race conditions)
   - **Claim-then-generate idempotency** (student-scoped, prevents duplicate Gemini calls)
6. Adding ~43 new tests (35 SQLite-compatible + 8 PostgreSQL concurrency tests)

The investigation conclusions stand: **Database-backed state is the correct architectural choice**; Redis introduces unnecessary complexity for the current scale and infrastructure.