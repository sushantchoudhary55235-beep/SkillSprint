# Phase 2 Rollback Plan

**Document Version**: 1.0  
**Created**: 2026-11-01  
**Status**: Reference procedure — **do not execute without explicit approval**

---

## Purpose

This document defines the procedure to safely revert Phase 2 changes ("Danger Zone Security & Data Integrity") while preserving Phase 1 changes and protecting student data. It covers application code, database migration, audit data, and student data safety.

**This is a rollback procedure, not an instruction to execute rollback.**

---

## 1. Application Code Rollback

### 1.1 Phase 2 Modified Files (Identified from `git status`)

| File | Type | Phase | Action to Revert |
|------|------|-------|------------------|
| `backend/app/models/audit.py` | NEW | 2 | Delete file |
| `backend/alembic/versions/1381cf99df52_add_reset_audit_log.py` | NEW | 2 | Delete file |
| `backend/app/models/__init__.py` | MODIFIED | 2 | Remove `ResetAuditLog` import/export |
| `backend/app/services/student_reset.py` | MODIFIED | 2 | Restore pre-Phase 2 version |
| `backend/tests/test_account_reset.py` | MODIFIED | 2 | Restore pre-Phase 2 version (7 tests) |

### 1.2 Phase 1 Modified Files (Must Preserve)

| File | Phase | Status |
|------|-------|--------|
| `README.md` | 1 | **Preserve** |
| `backend/app/seed_demo.py` | 1 | **Preserve** |
| `backend/app/services/teacher.py` | 1 | **Preserve** |
| `backend/tests/test_teachers.py` | 1 | **Preserve** |

### 1.3 Unrelated Pre-Existing Changes (Must Preserve)

| File | Origin | Status |
|------|--------|--------|
| `AUDIT_REPORT.md` (deleted) | Pre-existing | **Preserve deletion** |

### 1.4 Safe Application Rollback Procedure

**Prerequisites:**
- Working directory clean except for Phase 2 changes
- Branch: `main`
- Remote: `origin/main` (2 commits behind)

**Step 1: Backup current state**
```bash
cd C:/Users/s8001/Favorites/BE-Project
git stash push -m "phase2-backup-$(date +%Y%m%d-%H%M%S)" -- backend/app/models/audit.py backend/alembic/versions/1381cf99df52_add_reset_audit_log.py backend/app/models/__init__.py backend/app/services/student_reset.py backend/tests/test_account_reset.py
```

**Step 2: Restore Phase 2 modified files to pre-Phase 2 state**

*Option A: Using git restore (recommended for tracked files)*
```bash
# Restore tracked files to HEAD (pre-Phase 2)
git restore -- backend/app/models/__init__.py backend/app/services/student_reset.py backend/tests/test_account_reset.py

# Delete new files
rm -f backend/app/models/audit.py
rm -f backend/alembic/versions/1381cf99df52_add_reset_audit_log.py
```

*Option B: Manual edit (if git restore not available)*
- `backend/app/models/__init__.py`: Remove `from app.models.audit import ResetAuditLog` and `"ResetAuditLog"` from `__all__`
- `backend/app/services/student_reset.py`: Revert to pre-Phase 2 version (see Section 1.5 for key differences)
- `backend/tests/test_account_reset.py`: Remove 8 new test methods, restore original 7-test version

**Step 3: Verify Phase 1 files unchanged**
```bash
git diff -- README.md backend/app/seed_demo.py backend/app/services/teacher.py backend/tests/test_teachers.py
# Should show NO differences from current working tree (Phase 1 changes preserved)
```

**Step 4: Verify application tests pass**
```bash
cd backend
python -m pytest tests/test_account_reset.py -v   # Should show 7 tests (original)
python -m pytest -q                              # Should pass all Phase 1 tests
```

### 1.5 Key Code Differences (Phase 2 → Pre-Phase 2)

**`student_reset.py` — Pre-Phase 2 behavior:**
- No audit logging
- Password/phrase/rate limit checks outside try block (raise immediately, no audit)
- `request_id` generated inside try block
- No `before_counts` / `after_counts` in response
- No `_record_audit` method
- Exception handler only covers DB errors during deletion

**`test_account_reset.py` — Pre-Phase 2 tests (7):**
- `TestResetPreview.test_preview_counts_real_data`
- `TestResetPreview.test_teacher_cannot_preview`
- `TestResetExecution.test_wrong_phrase_rejected`
- `TestResetExecution.test_wrong_password_rejected`
- `TestResetExecution.test_reset_wipes_everything_and_keeps_account`
- `TestResetExecution.test_reset_is_rate_limited`
- `TestResetExecution.test_teacher_cannot_reset`

---

## 2. Database Migration Rollback

### 2.1 Migration Identification
- **Revision**: `1381cf99df52`
- **File**: `backend/alembic/versions/1381cf99df52_add_reset_audit_log.py`
- **Description**: "add reset audit log"
- **Creates**: Table `reset_audit_logs` with indexes on `student_id`, `timestamp`, `request_id`

### 2.2 Inspect Current Revision
```bash
cd C:/Users/s8001/Favorites/BE-Project/backend
python -m alembic current
# Expected output: 1381cf99df52 (head)
```

### 2.3 Safe Downgrade Procedure

**Prerequisites:**
- Application code already rolled back (Section 1) OR application compatible with schema without audit table
- No active reset operations in progress
- Audit data backed up if needed (Section 3)

**Step 1: Verify current state**
```bash
python -m alembic current
# Confirm: 1381cf99df52 (head)

python -m alembic history --verbose | head -20
# Confirm revision chain: ... -> d5e91b7f3a44 -> 1381cf99df52 (head)
```

**Step 2: Execute downgrade**
```bash
python -m alembic downgrade d5e91b7f3a44
# Expected: Drops reset_audit_logs table and its 3 indexes
```

**Step 3: Verify downgrade**
```bash
python -m alembic current
# Expected: d5e91b7f3a44 (or earlier)

python -c "
from app.db.session import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
try:
    insp = inspect(db.bind)
    tables = insp.get_table_names()
    print('reset_audit_logs' in tables)  # Should be False
finally:
    db.close()
"
```

### 2.4 Dependencies and Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Active audit records exist | Data loss | Backup audit table first (Section 3) |
| Application code expects `ResetAuditLog` | Runtime errors | Rollback application code FIRST (Section 1) |
| Foreign key: `student_profiles` → `reset_audit_logs` | ON DELETE SET NULL handles gracefully | No action needed — FK is SET NULL |
| Other migrations depend on this | None — this is head | No dependent migrations |

**Critical**: Never run `alembic downgrade` while Phase 2 application code is deployed. The service will fail on `from app.models.audit import ResetAuditLog`.

### 2.5 Downgrade Safety Checklist
- [ ] Application code reverted to pre-Phase 2 (Section 1 complete)
- [ ] Audit data backed up if required (Section 3)
- [ ] No in-flight reset operations
- [ ] Team notified of schema change
- [ ] Rollback tested in staging first (if available)

---

## 3. Audit Data Preservation

### 3.1 Why Preserve Audit Data
- Regulatory/compliance requirements (audit trail for destructive operations)
- Incident investigation (who reset what, when)
- Debugging production issues

### 3.2 Backup Procedure (Before Any Rollback)
```bash
# SQLite (development/test)
sqlite3 backend/skillsprint.db ".dump reset_audit_logs" > audit_backup_$(date +%Y%m%d).sql

# PostgreSQL (production)
pg_dump -t reset_audit_logs -d skillsprint > audit_backup_$(date +%Y%m%d).sql
```

### 3.3 Restoration (If Migration Re-applied)
```bash
# SQLite
sqlite3 backend/skillsprint.db < audit_backup_20261101.sql

# PostgreSQL
psql -d skillsprint -f audit_backup_20261101.sql
```

### 3.4 Implications of Removing Audit Table
- **Permanent loss** of all reset audit records (SUCCESS and FAILED)
- **No audit trail** for past or future resets until migration re-applied
- **Compliance gap** if audit retention policy requires history
- **Student data NOT affected** — student learning data is in separate tables

### 3.5 Data Retention Policy Reference
Per `risk_assessment.md` (Risk R8): No formal retention policy defined. Default: retain indefinitely. If retention policy implemented, apply before rollback.

---

## 4. Student Data Safety

### 4.1 What Rollback Does NOT Do
| Action | Effect on Student Data |
|--------|------------------------|
| Revert application code | **No effect** — student data unchanged |
| Downgrade migration (drop audit table) | **No effect** — student data in separate tables |
| `git restore` on service files | **No effect** — no DELETE/UPDATE on student tables |

**Rolling back code or schema does NOT restore deleted student records.**

### 4.2 Student Data Deletion is Irreversible
The reset operation (`POST /api/account/reset`) executes irreversible `DELETE` statements on 17 student-owned tables:
- `practice_sessions`, `practice_answers`
- `attempts`, `answers`
- `code_submissions`
- `xp_transactions`, `student_badges`
- `bookmarks`, `student_missions`
- `roadmaps`, `roadmap_items`, `recommendations`
- `topic_performance`, `performance_snapshots`
- `ai_answer_logs`, `activity_events`
- `leaderboard_entries`
- Plus: profile counters zeroed (`xp=0`, `level=1`, streaks=0)

**No application-level undo exists.** Recovery requires database backup restoration.

### 4.3 Recovery Requirements (If Unintended Data Deleted)
1. **Immediate**: Stop all write traffic to affected student's account
2. **Assess**: Identify which tables/records lost (use audit `rows_deleted` if available)
3. **Restore**: From most recent database backup (point-in-time recovery if PostgreSQL)
4. **Verify**: Run `test_account_reset.py::TestResetExecution::test_reset_wipes_everything_and_keeps_account` logic manually
5. **Audit**: Create incident record with root cause

### 4.4 Prevention (Current Safeguards)
- Password + exact phrase `RESET MY DATA` required
- Rate limit: 3 attempts / 10 min
- Student-only RBAC (teachers/admins blocked)
- Atomic transaction with rollback on failure
- Audit trail for all attempts

---

## 5. Recovery Verification

After any rollback (application code, migration, or both), execute:

### 5.1 Backend Test Execution
```bash
cd backend
python -m pytest tests/test_account_reset.py -v
# Expected: 7 tests pass (Phase 1 baseline) OR 15 tests pass (if migration not rolled back)

python -m pytest -q
# Expected: 314+ tests pass (Phase 1 baseline count)
```

### 5.2 Migration Revision Verification
```bash
python -m alembic current
# Expected: d5e91b7f3a44 (if migration rolled back) OR 1381cf99df52 (if migration kept)
```

### 5.3 Audit Table Verification
```bash
python -c "
from app.db.session import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
try:
    insp = inspect(db.bind)
    has_table = 'reset_audit_logs' in insp.get_table_names()
    print(f'Audit table exists: {has_table}')
    if has_table:
        from app.models.audit import ResetAuditLog
        count = db.query(ResetAuditLog).count()
        print(f'Audit records: {count}')
finally:
    db.close()
"
```

### 5.4 Authentication & Reset Endpoint Smoke Tests
```bash
# Start server
uvicorn app.main:app --port 8000 &

# Test unauthenticated reset rejected (401)
curl -X POST http://localhost:8000/api/account/reset -H "Content-Type: application/json" -d '{"password":"x","confirmation":"RESET MY DATA"}'
# Expected: 401

# Test student reset works (requires valid student token)
# ... run via test suite instead

# Kill server
kill %1
```

### 5.5 Frontend Verification
```bash
cd frontend
npx tsc --noEmit          # Expected: No errors
npm run build             # Expected: Build succeeds
```

---

## 6. Rollback Decision Checklist

### 6.1 Conditions Requiring APPLICATION Code Rollback Only
| Condition | Action |
|-----------|--------|
| Audit logging bugs (wrong counts, missing fields) | Revert `student_reset.py`, keep migration |
| Test failures in new security tests | Fix tests or revert test file |
| Performance regression in reset path | Profile first; revert service if critical |
| Frontend integration issues | Revert API response format changes only |

**Keep migration** — audit table can remain unused.

### 6.2 Conditions Requiring DATABASE Migration Rollback
| Condition | Action |
|-----------|--------|
| Migration breaks production deployment | Rollback migration after app rollback |
| Audit table causes performance issues | Investigate indexes first; rollback as last resort |
| Schema conflict with other migrations | Resolve conflict; rollback if unresolvable |
| Compliance requires removing audit table | Rollback after data preservation (Section 3) |

**Must rollback application code first** (Section 1) to avoid import errors.

### 6.3 Conditions Where Rollback Must Be Avoided
| Condition | Reason |
|-----------|--------|
| Active reset operations in progress | Would leave partial state; wait for completion |
| Unbacked audit data with regulatory requirement | Must preserve audit records first |
| Student data already deleted (unintended) | Rollback doesn't restore data; need DB backup restore |
| Production incident without runbook approval | Follow incident response process instead |

### 6.4 Required Backups Before Any Rollback

| Backup | When Required | Method |
|--------|---------------|--------|
| Application code (git stash) | Always | `git stash push` |
| Audit table data | If migration rollback | `pg_dump` / `sqlite3 .dump` |
| Full database | If student data recovery needed | `pg_dump` / `pg_basebackup` / snapshot |
| Migration file | If may re-apply later | Copy to safe location |

### 6.5 Required Approvals

| Rollback Type | Approvals Required |
|---------------|-------------------|
| Application code only | Team lead + 1 developer |
| Database migration (with data backup) | Team lead + DBA + Product Owner |
| Full rollback (code + migration + data) | Engineering Manager + Product Owner + Security |

---

## Appendix: Quick Reference Commands

### Full Rollback (Code + Migration + Preserve Audit)
```bash
cd C:/Users/s8001/Favorites/BE-Project

# 1. Backup audit data
sqlite3 backend/skillsprint.db ".dump reset_audit_logs" > audit_backup_$(date +%Y%m%d).sql

# 2. Rollback application code
git stash push -m "phase2-rollback-$(date +%Y%m%d)" -- backend/app/models/audit.py backend/alembic/versions/1381cf99df52_add_reset_audit_log.py backend/app/models/__init__.py backend/app/services/student_reset.py backend/tests/test_account_reset.py
git restore -- backend/app/models/__init__.py backend/app/services/student_reset.py backend/tests/test_account_reset.py
rm -f backend/app/models/audit.py backend/alembic/versions/1381cf99df52_add_reset_audit_log.py

# 3. Rollback migration
cd backend
python -m alembic downgrade d5e91b7f3a44

# 4. Verify
python -m alembic current
python -m pytest tests/test_account_reset.py -v
python -m pytest -q
```

### Partial Rollback (Code Only, Keep Audit Table)
```bash
cd C:/Users/s8001/Favorites/BE-Project
git stash push -m "phase2-code-rollback-$(date +%Y%m%d)" -- backend/app/models/__init__.py backend/app/services/student_reset.py backend/tests/test_account_reset.py
git restore -- backend/app/models/__init__.py backend/app/services/student_reset.py backend/tests/test_account_reset.py
# Keep: backend/app/models/audit.py and migration file
```

### Restore from Backup (If Rollback Was Mistake)
```bash
cd C:/Users/s8001/Favorites/BE-Project
git stash list
git stash pop  # Restores the Phase 2 changes

cd backend
python -m alembic upgrade head  # Re-applies migration
```

---

## Document Control

| Field | Value |
|-------|-------|
| Author | Phase 2 Implementation |
| Reviewers | Engineering Lead, DBA, Product Owner |
| Classification | Internal — Operational Procedure |
| Next Review | Phase 3 Planning |

**End of Rollback Plan**