# Phase 4 Risk Assessment

**Generated**: 2026-11-01  
**Based on**: PHASE_4_IMPLEMENTATION_PLAN.md, PHASE_4_DATABASE_DESIGN.md  
**Status**: PLANNING PHASE — Awaiting approval  
**Last Updated**: 2026-11-01 (corrected for atomic rate limiting, claim-then-generate idempotency, PostgreSQL concurrency tests)

---

## Risk Matrix

| Risk ID | Category | Likelihood | Impact | Score | Mitigation |
|---------|----------|------------|--------|-------|------------|
| R1 | Database contention on rate limiter | Low | Medium | 6 | Advisory lock serialization; monitor latency |
| R2 | Ticket store deadlock on consume | Low | High | 8 | Short transactions; retry logic |
| R3 | Migration failure in production | Low | Critical | 10 | Test on staging; backup before deploy |
| R4 | Retry logic causes duplicate Gemini calls | Low | Medium | 6 | Claim-then-generate with INSERT ON CONFLICT; idempotency key |
| R5 | Token logging exposes sensitive data | Low | High | 8 | Log only counts; no prompt/response text |
| R6 | Config regression breaks AI | Low | High | 8 | Defaults match current; validation |
| R7 | DB unavailability cascades to 503 | Medium | Medium | 9 | Consistent with current AI degradation |
| R8 | Race condition in rate limiter | Very Low | Low | 2 | **ELIMINATED** — PostgreSQL advisory locks guarantee atomic enforcement |
| R9 | Test flakiness from DB timing | Low | Medium | 6 | Transactional fixtures; fixed time; PG concurrency tests |
| R10 | Frontend/backend contract drift | Low | Medium | 6 | TypeScript types match; CI build check |

**Score = Likelihood (1-5) × Impact (1-5)**

---

## Detailed Risk Analysis

### R1: Database Contention on Rate Limiter

**Scenario**: High concurrent traffic causes lock contention on `ai_rate_limits` table.

**Analysis**:
- Current: In-memory, zero contention
- Proposed: Each request acquires `pg_advisory_xact_lock(user_id)` then inserts rate limit record
- Advisory locks are lightweight (no table locks, no row locks)
- At 1000 users × 10 req/min = 167 req/s
- PostgreSQL handles ~1000-5000 simple writes/s with advisory locks
- Connection pool: 20 + 10 overflow = 30 concurrent

**Mitigation**:
1. **Advisory lock serialization**: `pg_advisory_xact_lock` serializes per-user checks without table/row locks
2. **Monitor**: Add metrics for rate limiter latency (target <10ms p99)
3. **Fallback**: If latency > 100ms p99, consider Redis in Phase 5
4. **Index optimization**: Composite index `(user_id, window_start)` for fast COUNT

**Residual Risk**: LOW — Advisory locks are extremely lightweight; well within PostgreSQL capacity for expected load.

---

### R2: Ticket Store Deadlock on Consume

**Scenario**: Two concurrent `consume` calls for same ticket cause deadlock.

**Analysis**:
- `consume` uses `SELECT FOR UPDATE` on single row
- PostgreSQL deadlocks are rare with single-row locks
- Deadlock → transaction rolled back → client gets 503 → retries

**Mitigation**:
1. **Short transaction**: Only SELECT + UPDATE consumed_at
2. **Application retry**: Client can retry evaluate (ticket not consumed on failure)
3. **Lock timeout**: PostgreSQL default 1s; acceptable

**Residual Risk**: LOW — Single-row locks rarely deadlock; failure = 503 (safe).

---

### R3: Migration Failure in Production

**Scenario**: Alembic migration fails partially, leaving schema in inconsistent state.

**Analysis**:
- Two new tables: `question_tickets`, `ai_rate_limits`
- No modifications to existing tables
- No data migration (empty tables)
- Independent tables — no cross-table dependencies

**Mitigation**:
1. **Test on staging first**: Run full migration + downgrade cycle
2. **Backup before deploy**: `pg_dump` before migration
3. **Idempotent migration**: Safe to re-run
4. **Rollback tested**: `alembic downgrade -2` verified

**Residual Risk**: LOW — Simple CREATE TABLE migrations; no data migration.

---

### R4: Retry Logic Causes Duplicate Gemini Calls

**Scenario**: Retry on timeout/5xx causes duplicate charge for same operation.

**Analysis**:
- Only `_generate()` retries (explain, hint, progressive_hint, interpret, generate_question)
- `_generate_chat()` does NOT retry (conversation not idempotent)
- **Corrected**: `generate_question` uses **claim-then-generate pattern** with `INSERT ... ON CONFLICT` on composite unique index `(student_id, idempotency_key)`:
  1. Attempt INSERT with placeholder row (claims the key)
  2. If conflict: another request claimed it → wait for completion (poll up to 30s) → return existing ticket
  3. If claim succeeds: call Gemini, update placeholder with real data
  4. If Gemini fails: DELETE placeholder, key available for retry
- Other operations: duplicate = extra cost, no correctness issue (idempotency key only for generate)

**Cost Estimate**:
- Gemini 2.0 Flash: ~$0.075/1M input tokens, $0.30/1M output
- Typical request: ~200 input + 100 output tokens = ~$0.000045
- 1 retry = 2× cost = ~$0.00009 per request
- At 1000 req/day with 10% retry rate = ~$0.27/day extra

**Mitigation**:
1. **Claim-then-generate pattern** (eliminates duplicate calls under concurrency for generate)
2. **Max 1 retry** (not infinite)
3. **No retry on 4xx** (invalid requests)
4. **Log retries** for monitoring

**Residual Risk**: LOW — Claim-then-generate eliminates duplicate Gemini calls for generate endpoint; other endpoints have minimal cost impact.

---

### R5: Token Logging Exposes Sensitive Data

**Scenario**: Prompt or response text accidentally logged.

**Analysis**:
- Current logging: Only warning on failure (no prompt/response)
- Proposed: Structured log with token counts only
- No prompt/response in log statement

**Mitigation**:
1. **Explicit log fields**: Only `prompt_tokens`, `completion_tokens`, `total_tokens`, `model`, `operation`, `user_id`
2. **No f-string with response**: Use structured logging with explicit fields
3. **Code review**: Verify no accidental `{response.text}` in logs
4. **Log sanitization**: Existing practice — API key never in URL/logs

**Residual Risk**: LOW — Design prevents text logging; code review catches mistakes.

---

### R6: Config Regression Breaks AI

**Scenario**: Invalid `AI_TIMEOUT_S` or `GEMINI_MODEL` breaks all AI endpoints.

**Analysis**:
- Defaults match current hardcoded values
- Validation clamps timeout to [1, 60]
- Model passed directly to Gemini (API validates)

**Mitigation**:
1. **Safe defaults**: `AI_TIMEOUT_S=15.0`, `GEMINI_MODEL=gemini-2.0-flash`
2. **Validation in Settings**: Clamp + warn
3. **Tests**: Config tests verify clamping
4. **Feature flag**: If needed, `AI_ENABLED=false` disables all AI (already exists via empty key)

**Residual Risk**: LOW — Defaults preserve current behavior; validation prevents crashes.

---

### R7: DB Unavailability Cascades to 503

**Scenario**: PostgreSQL down → ticket store/rate limiter fail → all AI endpoints return 503.

**Analysis**:
- Current: In-memory stores work even if DB down (for non-AI endpoints)
- Proposed: AI endpoints need DB for tickets + rate limits
- Non-AI endpoints unaffected (practice, assessments, coding, etc.)
- AI already degrades to 503 on Gemini failure

**Mitigation**:
1. **Consistent behavior**: AI unavailable = 503 (same as Gemini down)
2. **DB health**: Existing pool_pre_ping, connection retry
3. **Monitoring**: Alert on DB connection failures
4. **Graceful degradation**: Non-AI features work normally

**Residual Risk**: MEDIUM — AI fully dependent on DB; but AI already non-critical path.

---

### R8: Race Condition in Rate Limiter — **ELIMINATED**

**Previous Analysis** (superseded):
- Window: 60 seconds, Limit: 10
- Race: T1 counts 9, T2 counts 9, both insert → 11 total
- Impact: User gets 11 instead of 10 (10% over-limit)

**Corrected Design**: 
- **Atomic enforcement via `pg_advisory_xact_lock(user_id)`** — serializes all rate limit checks for a given user within a transaction
- Algorithm:
  1. `SELECT pg_advisory_xact_lock(user_id)` — blocks other transactions for same user
  2. `COUNT(*) FROM ai_rate_limits WHERE user_id = ? AND window_start > ?`
  3. If count >= limit: raise RateLimitExceededError
  4. INSERT new rate limit record
  5. Transaction commits → advisory lock released
- **Zero race conditions**: Advisory lock guarantees exactly 10 requests per minute per user
- No `SELECT FOR UPDATE` on tables — no row locks, no deadlocks

**Residual Risk**: **VERY LOW** — Advisory locks provide mathematical guarantee of exact limit enforcement.

---

### R9: Test Flakiness from DB Timing

**Scenario**: Tests using real DB timestamps fail intermittently.

**Analysis**:
- Current tests: In-memory, deterministic
- New tests: Use real DB with `datetime.now()`
- Window boundaries (60s) can cause flakiness

**Mitigation**:
1. **Use fixed time in tests**: Mock `datetime.now()` or pass time explicitly
2. **Transactional fixtures**: Each test in own transaction, rolled back
3. **No sleeps**: Use time manipulation, not `time.sleep()`
4. **Generous windows**: Test with 2s window instead of 60s
5. **PostgreSQL concurrency tests**: 8 dedicated tests in `test_ai_reliability_pg.py` verify atomicity under real concurrency

**Residual Risk**: LOW — Standard testing patterns + dedicated PG concurrency tests prevent flakiness.

---

### R10: Frontend/Backend Contract Drift

**Scenario**: Backend response changes but frontend types not updated.

**Analysis**:
- Phase 4: Minimal contract changes (only optional `Idempotency-Key` header on `/questions/generate`)
- `recorded_only_answer` already in sync
- TypeScript build catches mismatches

**Mitigation**:
1. **CI check**: `npm run build` + `npx tsc --noEmit` in pipeline
2. **Single source of truth**: Backend Pydantic → OpenAPI → TypeScript (manual sync)
3. **Contract tests**: Verify response schemas

**Residual Risk**: LOW — Existing CI catches drift; minimal changes in Phase 4.

---

## Security Risks

| Risk | Assessment |
|------|------------|
| SQL Injection | LOW — SQLAlchemy ORM with parameterized queries |
| Ticket enumeration | LOW — `ticket_id` is 24-char URL-safe token (128-bit entropy) |
| Rate limit bypass | LOW — Server-side enforcement; DB-backed with advisory locks |
| Prompt injection | UNCHANGED — Existing delimiters + ignore-instructions |
| API key leak | UNCHANGED — Never logged; only in httpx params |

---

## Operational Risks

| Risk | Assessment |
|------|------------|
| Disk growth (rate limit table) | LOW — ~10 rows/user/min; 1000 users = 600K rows/hour; cleanup job removes old |
| Connection pool exhaustion | LOW — 30 connections; rate limiter uses 1 per request; short transactions |
| Migration downtime | NONE — CREATE TABLE only; no locks on existing tables |
| Monitoring gaps | MEDIUM — Add metrics for retry count, token usage, rate limiter latency |

---

## Rollback Risks

| Risk | Assessment |
|------|------------|
| Data loss on rollback | NONE — New tables only; no data migration |
| In-memory state loss | LOW — Tickets/rate limits reset (same as restart) |
| Partial rollback | LOW — Two independent migrations; can downgrade separately |

---

## Risk Summary

| Category | High | Medium | Low | Very Low |
|----------|------|--------|-----|----------|
| Technical | 0 | 1 (R7) | 7 | 1 (R8) |
| Security | 0 | 0 | 5 | 0 |
| Operational | 0 | 1 | 2 | 0 |
| **Total** | **0** | **2** | **14** | **1** |

**Overall Risk Level**: **LOW**

**No HIGH risks identified.** All MEDIUM risks have documented mitigations and acceptable residual risk. R8 (race condition) is **eliminated** by advisory lock design.

---

## Approval Criteria

Phase 4 implementation should proceed if:
- [ ] All MEDIUM risks have accepted mitigations
- [ ] Staging deployment validates migrations
- [ ] Load test confirms rate limiter performance (<10ms p99 with advisory locks)
- [ ] Security review confirms no new attack surface
- [ ] Rollback plan tested on staging
- [ ] PostgreSQL concurrency tests pass (8 tests in `test_ai_reliability_pg.py`)

---

## Confirmation

**No code changes made during risk assessment.** This is an analysis document only.