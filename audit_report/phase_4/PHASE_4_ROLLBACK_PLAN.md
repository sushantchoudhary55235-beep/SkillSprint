# Phase 4 Rollback Plan

**Generated**: 2026-11-01  
**Based on**: PHASE_4_IMPLEMENTATION_PLAN.md, PHASE_4_DATABASE_DESIGN.md  
**Status**: PLANNING PHASE — Awaiting approval  
**Last Updated**: 2026-11-01 (corrected for atomic rate limiting, claim-then-generate idempotency, advisory locks)

---

## Rollback Strategy

**Principle**: Full reversibility within 10 minutes. All changes are additive (new tables, new code paths) with feature flags or instance swaps to revert.

### Rollback Trigger Conditions
- Critical bug in production affecting non-AI features
- Performance degradation > 2x baseline on AI endpoints
- Data corruption or loss
- Failed deployment with partial migration

---

## Rollback Procedures

### Level 1: Code-Only Rollback (No DB Changes)
**Time**: ~2 minutes  
**When**: Bug in new logic (retry, token logging, config, advisory lock rate limiting, claim-then-generate idempotency) but migrations not applied or safe to keep

#### Steps:

1. **Revert `ai.py` to pre-Phase 4 version**
   ```bash
   git checkout HEAD -- backend/app/services/ai.py
   ```
   - Restores hardcoded `_TIMEOUT_S = 15.0`
   - Restores hardcoded `model="gemini-2.0-flash"`
   - Removes retry logic with exponential backoff
   - Removes token usage logging
   - Removes response validation hardening
   - Removes `Idempotency-Key` header handling

2. **Revert `ai_tickets.py` to in-memory store**
   ```bash
   git checkout HEAD -- backend/app/services/ai_tickets.py
   ```
   - Restores `TicketStore` class (in-memory dict with threading.Lock)
   - Restores `question_ticket_store = TicketStore()`
   - Removes `DatabaseTicketStore` class
   - Removes `QuestionTicket` dataclass with `idempotency_key`, `id`, `created_at` fields

3. **Revert `rate_limit.py` to in-memory limiter**
   ```bash
   git checkout HEAD -- backend/app/core/rate_limit.py
   ```
   - Restores `SlidingWindowLimiter` class (in-memory defaultdict with threading.Lock)
   - Restores `ai_limiter = SlidingWindowLimiter(...)`
   - Removes `DatabaseRateLimiter` class with `pg_advisory_xact_lock` advisory lock logic

4. **Revert `ai_questions.py` idempotency changes**
   ```bash
   git checkout HEAD -- backend/app/services/ai_questions.py
   ```
   - Removes claim-then-generate pattern with `INSERT ... ON CONFLICT`
   - Removes idempotency key handling
   - Removes placeholder row logic (claim, wait, complete, or delete on failure)

5. **Revert `ai.py` routes idempotency header and rate limit dependency**
   ```bash
   git checkout HEAD -- backend/app/api/routes/ai.py
   ```
   - Removes `Idempotency-Key` header parameter from `/questions/generate`
   - Restores simple rate limit dependency (in-memory)

6. **Revert config changes**
   ```bash
   git checkout HEAD -- backend/app/core/config.py
   ```
   - Removes `AI_TIMEOUT_S`, `GEMINI_MODEL` settings

7. **Restart backend**
   ```bash
   # In production: systemctl restart skillsprint-api
   # In dev: Ctrl+C and re-run uvicorn
   ```

8. **Verify**
   ```bash
   cd backend && python -m pytest -q
   # Target: 327 tests pass
   ```

**Result**: System behaves exactly as pre-Phase 4. New DB tables exist but unused.

---

### Level 2: Full Rollback with Database Migration Downgrade
**Time**: ~5 minutes  
**When**: Migrations applied and need to remove new tables

#### Prerequisites:
- Level 1 code rollback completed
- Database accessible
- Alembic environment configured

#### Steps:

1. **Verify current migration head**
   ```bash
   cd backend
   alembic current
   # Should show two new revisions:
   # xxx_add_ai_rate_limits (head)
   # xxx_add_question_tickets
   ```

2. **Downgrade rate limits table**
   ```bash
   alembic downgrade -1
   # Drops ai_rate_limits table and advisory lock function (if any)
   ```

3. **Downgrade question tickets table**
   ```bash
   alembic downgrade -1
   # Drops question_tickets table with composite unique index on (student_id, idempotency_key)
   ```

4. **Verify schema**
   ```bash
   alembic current
   # Should show previous head: 1381cf99df52_add_reset_audit_log
   ```

5. **Verify tables dropped**
   ```sql
   -- In psql or DB client
   \dt question_tickets ai_rate_limits
   -- Should return "No relations found"
   ```

6. **Restart backend** (if not already)
   ```bash
   # Ensure code matches pre-Phase 4
   systemctl restart skillsprint-api
   ```

7. **Full regression test**
   ```bash
   cd backend && python -m pytest -q
   # Target: 327 tests pass
   ```

**Result**: Complete reversal to pre-Phase 4 state. No new tables, no new code.

---

### Level 3: Emergency Hotfix (Production Incident)
**Time**: ~1 minute  
**When**: Critical issue requiring immediate mitigation

#### Quick Toggle: Disable AI Entirely
```bash
# Set in environment / .env
GEMINI_API_KEY=""  # Empty key disables all AI endpoints → 503
# Restart backend
systemctl restart skillsprint-api
```

**Effect**: All 7 AI endpoints return 503 immediately. Core platform (practice, assessments, coding, auth) unaffected.

**Recovery**: Set valid `GEMINI_API_KEY` and restart.

---

## Rollback Verification Checklist

After any rollback, verify:

| Check | Command | Expected |
|-------|---------|----------|
| Backend starts | `uvicorn app.main:app` | No errors |
| AI endpoints return 503 (no key) | `curl -X POST /ai/explain` | 503 Service Unavailable |
| Non-AI endpoints work | `curl /api/health` | 200 OK |
| Full test suite passes | `python -m pytest -q` | 327 passed |
| Frontend builds | `cd frontend && npm run build` | Success |
| No new tables (Level 2) | `\dt question_tickets` | Not found |

---

## Data Preservation

### What is Preserved on Rollback
- **All existing data**: No modifications to existing tables
- **User accounts, progress, XP, streaks**: Unaffected
- **AI answer logs**: `ai_answer_logs` table unchanged
- **Questions, topics, assessments**: Unaffected

### What is Lost on Rollback
- **Outstanding tickets**: In-memory or DB tickets not yet consumed
  - Impact: Students with generated but unanswered questions must regenerate
  - Acceptable: Tickets expire in 30 min anyway
- **Rate limit counters**: Current window counts reset
  - Impact: Users get fresh 10/min budget
  - Acceptable: Beneficial to users
- **Idempotency keys**: Any placeholder rows in `question_tickets` (deleted on rollback)
  - Impact: Duplicate protection lost for in-flight requests
  - Acceptable: Keys are per-request anyway

### What is NOT Affected
- No data migration performed
- No existing columns modified
- No foreign keys to new tables from existing tables

---

## Migration-Specific Rollback Details

### Migration 1: `xxx_add_question_tickets.py`

**Upgrade**: Creates `question_tickets` table with:
- Columns: `id`, `student_id`, `ticket_id`, `payload` (JSONB), `expires_at`, `consumed_at`, `idempotency_key`, `created_at`
- Composite unique index: `ix_question_tickets_idempotency ON question_tickets(student_id, idempotency_key) WHERE idempotency_key IS NOT NULL`
- Index on `(student_id, expires_at)` for cleanup
- Index on `(student_id, consumed_at)` for per-student limit enforcement

**Downgrade**: `op.drop_table("question_tickets")` — drops table and all indexes

**Data at risk**: Any tickets issued after migration (including placeholder rows from claim-then-generate)

**Recovery**: None needed (tickets are ephemeral, 30-min TTL)

---

### Migration 2: `xxx_add_ai_rate_limits.py`

**Upgrade**: Creates `ai_rate_limits` table with:
- Columns: `id`, `user_id`, `window_start`, `created_at`
- Composite index: `(user_id, window_start)` for fast window queries
- Index on `created_at` for cleanup

**Downgrade**: `op.drop_table("ai_rate_limits")` — drops table and all indexes

**Data at risk**: Rate limit records from current window

**Recovery**: None needed (counters reset on rollback)

---

## Deployment Rollback (If Using CI/CD)

### Git Revert Strategy
```bash
# Revert the Phase 4 merge commit
git revert <merge-commit-sha> -m 1

# Or revert individual commits
git revert <commit-sha-1> <commit-sha-2> ...

# Push and deploy
git push origin main
# CI/CD runs: tests → build → deploy
```

### Database Rollback in CI/CD
```yaml
# In deployment pipeline, on failure:
- name: Rollback migrations
  if: failure()
  run: |
    alembic downgrade -2
    # Verify
    alembic current
```

---

## Rollback Decision Tree

```
INCIDENT DETECTED
       │
       ▼
Is AI the only affected component?
       │
       ├─ YES ──► Level 1: Code rollback (2 min)
       │
       └─ NO ──► Is DB schema the issue?
                    │
                    ├─ YES ──► Level 2: Full rollback with downgrade (5 min)
                    │
                    └─ NO ──► Level 3: Disable AI via GEMINI_API_KEY="" (1 min)
```

---

## Post-Rollback Actions

1. **Incident documentation**: Record what failed, root cause, rollback level used
2. **Root cause analysis**: Why did the issue pass testing?
3. **Fix and re-test**: Address root cause in new branch
4. **Re-deploy**: After fix validated on staging

---

## Communication Plan

| Audience | Channel | Timing |
|----------|---------|--------|
| Engineering team | Slack #incidents | Immediate |
| Product/Stakeholders | Email/Slack | Within 15 min |
| Users (if visible) | Status page | If > 5 min downtime |

**Template**:
> **Incident**: Phase 4 AI Integration Rollback
> **Time**: [timestamp]
> **Level**: [1/2/3]
> **Impact**: AI endpoints returning 503 / degraded
> **Core platform**: Unaffected
> **ETA for fix**: [estimate]

---

## Testing the Rollback Plan

**Before Phase 4 merge, validate on staging:**

1. **Deploy Phase 4 to staging**
2. **Run smoke tests**: AI endpoints work, non-AI works
3. **Execute Level 1 rollback**: Verify 327 tests pass
4. **Execute Level 2 rollback**: Verify tables dropped, 327 tests pass
5. **Execute Level 3 rollback**: Verify AI disabled, core works
6. **Re-deploy Phase 4**: Verify forward deployment works

**Rollback plan is only approved after staging validation.**

---

## Rollback Contact

- **Primary**: Backend engineer on-call
- **Secondary**: DevOps engineer
- **Escalation**: Tech lead

---

## Confirmation

**No rollback executed during planning.** This document defines procedures for implementation-time readiness.