# Phase 2 Implementation Plan

## File-by-File Plan

### 1. NEW: `backend/app/models/audit.py`
**Current Issue**: No audit trail model exists for reset operations
**Proposed Modification**: Create new model file with `ResetAuditLog` class
**Why**: Need persistent audit trail that survives reset (activity_events are wiped)
**Expected Result**: New table `reset_audit_logs` created via migration
**Tests**: Audit trail tests in test_account_reset.py

### 2. MODIFY: `backend/app/services/student_reset.py`
**Current Issue**: No audit logging, no before/after verification returned
**Proposed Modification**:
- Import `ResetAuditLog` model
- In `reset_all()`: After successful commit, create SUCCESS audit record
- In exception handler: Create FAILED audit record before re-raising
- Return enhanced response with `before_counts` and `after_counts` (after should be 0 for deleted tables)
- Use separate session/transaction for audit to ensure it persists even if main tx rolls back
**Why**: Audit must accurately represent final outcome; before/after verification for caller
**Expected Result**: Reset operations permanently logged; caller gets verification data
**Tests**: Audit success/failure tests, verification count tests

### 3. MODIFY: `backend/app/models/__init__.py`
**Current Issue**: New model not registered
**Proposed Modification**: Import and export `ResetAuditLog`
**Why**: Alembic autogenerate needs to see the model
**Expected Result**: Migration can be generated
**Tests**: Alembic revision generation

### 4. NEW: `backend/alembic/versions/xxx_add_reset_audit_log.py`
**Current Issue**: No audit table in database
**Proposed Modification**: Create migration for `reset_audit_logs` table
**Why**: Persist audit trail
**Expected Result**: Table created in database
**Tests**: Migration apply/rollback, test runs with new table

### 5. EXTEND: `backend/tests/test_account_reset.py`
**Current Issue**: Missing security test coverage
**Proposed Modification**: Add test methods:
1. `test_unauthenticated_reset_rejected` - 401 without token
2. `test_admin_cannot_reset` - 403 for admin
3. `test_data_isolation_two_students` - Student A reset doesn't affect Student B
4. `test_reset_rollback_on_failure` - Simulated DB failure causes rollback
5. `test_audit_success_recorded` - SUCCESS audit created
6. `test_audit_failure_recorded` - FAILED audit created on error
7. `test_audit_no_credentials` - Audit contains no passwords/tokens
8. `test_preview_accuracy` - Preview counts match actual deletable records
**Why**: Comprehensive security validation
**Expected Result**: All new tests pass, existing tests still pass
**Tests**: These new tests + existing 7 tests = 15 total

### 6. VERIFY: `frontend/src/pages/student/AccountSettingsPage.tsx`
**Current Issue**: None found - implementation is solid
**Proposed Modification**: No changes needed
**Why**: Frontend already implements all required UX:
- Danger Zone warning
- Preview with record counts
- Two-step confirmation
- Password + exact phrase
- Loading state
- Duplicate submission protection
- Success/error messages
**Expected Result**: No frontend changes
**Tests**: Manual verification, existing functionality preserved

### 7. VERIFY: `backend/app/api/routes/account.py`
**Current Issue**: None found - endpoints correct
**Proposed Modification**: No functional changes
**Why**: API already validates password, confirmation, auth, RBAC
**Expected Result**: No changes
**Tests**: Existing tests cover endpoints

### 8. VERIFY: `backend/app/api/deps.py`
**Current Issue**: None found
**Proposed Modification**: No changes
**Why**: Auth and RBAC working correctly
**Expected Result**: No changes

### 9. VERIFY: `backend/app/core/security.py`
**Current Issue**: None found
**Proposed Modification**: No changes
**Why**: `verify_password` working correctly with bcrypt
**Expected Result**: No changes

---

## Migration Plan

1. Create audit model in `backend/app/models/audit.py`
2. Update `backend/app/models/__init__.py` to export it
3. Generate migration: `cd backend && alembic revision --autogenerate -m "add reset audit log"`
4. Review migration, apply: `alembic upgrade head`
5. Implement audit logging in `student_reset.py`
6. Extend tests
7. Run full test suite
8. Verify frontend build

---

## Database Changes

**New Table: `reset_audit_logs`**
```sql
CREATE TABLE reset_audit_logs (
    id BIGINT PRIMARY KEY,
    student_id BIGINT REFERENCES student_profiles(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL,  -- 'SUCCESS' or 'FAILED'
    rows_deleted JSONB NOT NULL,   -- or JSON for SQLite
    failure_reason TEXT,
    request_id VARCHAR(100)
);
CREATE INDEX ix_reset_audit_logs_student_id ON reset_audit_logs(student_id);
CREATE INDEX ix_reset_audit_logs_timestamp ON reset_audit_logs(timestamp);
```

---

## API Behavior Changes

**POST /account/reset response enhanced**:
```json
{
  "success": true,
  "message": "All learning data has been reset",
  "data": {
    "reset": true,
    "rows_deleted": { ... },
    "before_counts": { ... },
    "after_counts": { ... }
  }
}
```

**Audit log created** (not in API response, but in DB):
- SUCCESS record with row counts
- FAILED record with error reason

---

## Test Execution Plan

```bash
# 1. Run new migration
cd backend && alembic upgrade head

# 2. Run all tests
python -m pytest -q

# 3. Specifically run reset tests
python -m pytest tests/test_account_reset.py -v

# 4. Frontend checks
cd frontend && npx tsc --noEmit && npm run build
```

---

## Expected Outcomes

| Metric | Phase 1 Baseline | Phase 2 Target |
|--------|-----------------|----------------|
| Backend tests | 314 passed | 314+ passed (new tests added) |
| Frontend TypeScript | Pass | Pass |
| Frontend build | Pass | Pass |
| Reset audit trail | None | Complete |
| Security test coverage | 7 tests | 15+ tests |
| Data isolation verified | Partial | Complete |
| Transaction safety | Implicit | Explicit + tested |