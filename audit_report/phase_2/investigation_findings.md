# Phase 2 Investigation Findings

## A1. Git and Project State

- **Branch**: `main` (ahead of origin/main by 2 commits)
- **Phase 1 Changes** (preserved):
  - `README.md` - Complete rewrite, fixed demo account documentation
  - `backend/app/seed_demo.py` - Fixed print statements
  - `backend/tests/test_teachers.py` - Updated test emails to match seed_demo.py
  - `backend/app/services/teacher.py` - Modified
- **Uncommitted files**: `audit_report/` directory

## A2. Backend Reset Implementation Analysis

### Current Implementation: `backend/app/services/student_reset.py`

**Strengths (Already Working)**:
1. ✅ **Password verification** - Uses `verify_password()` from security module
2. ✅ **Confirmation phrase** - Requires exact `RESET MY DATA` (case-sensitive)
3. ✅ **Rate limiting** - 3 attempts per 10 minutes per user (in-memory, thread-safe)
4. ✅ **RBAC** - Only students can call reset (via `require_student` dependency)
5. ✅ **Account preservation** - User account, email, password, role kept intact
6. ✅ **Atomic transaction** - All deletes in single transaction with rollback on failure
7. ✅ **Profile counters reset** - XP, level, streaks, readiness_score zeroed
8. ✅ **Activity trace** - Adds `DATA_RESET` event after wipe
8. ✅ **Preview endpoint** - Returns counts of what would be deleted
9. ✅ **No credential logging** - Passwords not logged

**Identified Issues / Missing Protections**:
1. ❌ **No audit trail persistence** - Reset operations not logged to audit table (only activity event which gets wiped)
2. ❌ **Deletion verification not explicit** - No before/after count verification returned to caller
3. ❌ **In-memory rate limiter** - Not shared across processes (acceptable for single-process dev, but documented limitation)
4. ❌ **Student ID from session** - Uses `user.student_profile` from dependency (good, not from frontend)
5. ❌ **No foreign key cascade verification** - Relies on SQLAlchemy cascades but no explicit verification

### API Routes: `backend/app/api/routes/account.py`

- ✅ `GET /account/reset/preview` - Returns preview counts
- ✅ `POST /account/reset` - Executes reset with password + confirmation
- ✅ Uses `require_student` dependency for auth
- ✅ Validates password and confirmation via Pydantic model

### Authentication & Authorization: `backend/app/api/deps.py`

- ✅ JWT-based authentication with `get_current_user`
- ✅ Role-based access: `require_student`, `require_teacher`, `require_admin`
- ✅ Token validation with expiry and subject checks
- ✅ 401 for missing/invalid/expired tokens
- ✅ 403 for role mismatch

## A3. Student Data Ownership Inventory

### Tables DELETED by reset (student-owned, CASCADE on student_profiles.id):

| Table | FK to student_profiles | Cascade | Notes |
|-------|------------------------|---------|-------|
| `practice_sessions` | student_id | CASCADE | Has PracticeAnswer children |
| `practice_answers` | session_id → practice_sessions | CASCADE | Child of practice_sessions |
| `attempts` | student_id | CASCADE | Has Answer children |
| `answers` | attempt_id → attempts | CASCADE | Child of attempts |
| `code_submissions` | student_id | - | Direct student ownership |
| `xp_transactions` | student_id | CASCADE | Auditable ledger |
| `student_badges` | student_id | CASCADE | Many-to-many link |
| `bookmarks` | student_id | CASCADE | Student's saved items |
| `student_missions` | student_id | CASCADE | Date-scoped daily missions |
| `roadmaps` | student_id | CASCADE | Has RoadmapItem children |
| `roadmap_items` | roadmap_id → roadmaps | CASCADE | Child of roadmaps |
| `recommendations` | student_id | - | Student-specific |
| `topic_performance` | student_id | CASCADE | Derived, recomputable |
| `performance_snapshots` | student_id | CASCADE | Historical snapshots |
| `ai_answer_logs` | student_id | CASCADE | AI quiz outcomes |
| `activity_events` | student_id | CASCADE | Activity feed (gets DATA_RESET added) |
| `leaderboard_entries` | student_id | CASCADE | Score entries |

### Tables PRESERVED (shared/system/other users):

| Table | Reason |
|-------|--------|
| `users` | Account itself preserved |
| `student_profiles` | Profile kept, counters reset |
| `teacher_profiles` | Other role's data |
| `teacher_students` | Teacher associations kept |
| `topics`, `companies`, `badges`, `missions`, `leaderboards` | Shared reference data |
| `questions`, `question_options`, `assessments`, `assessment_questions` | Shared content |
| `coding_problems`, `test_cases` | Shared content |
| Other users' data | Different student_id |

### Profile Counters Reset (in-transaction):
- `xp = 0`
- `level = 1`
- `current_streak = 0`
- `longest_streak = 0`
- `last_activity_date = NULL`
- `readiness_score = 0`

## A4. Frontend Investigation: `frontend/src/pages/student/AccountSettingsPage.tsx`

**Current Implementation**:
1. ✅ **Danger Zone warning** - Red-bordered section with clear messaging
2. ✅ **Preview of what will be deleted** - Grid showing all record counts
3. ✅ **Two-step confirmation modal**:
   - Step 1: "Are you absolutely sure?" with total record count
   - Step 2: Password input + exact phrase `RESET MY DATA`
4. ✅ **Password input** - Required, masked
5. ✅ **Confirmation phrase** - Must match exactly, submit button disabled until match
6. ✅ **Loading state** - "Resetting..." with disabled buttons
6. ✅ **Error handling** - Shows API error messages
7. ✅ **Success state** - Green banner with "Go to dashboard" link
8. ✅ **Duplicate submission protection** - Submit disabled while busy
9. ✅ **Accessible markup** - aria labels, roles

**Frontend API**: `frontend/src/services/api.ts`
- `accountApi.resetPreview()` - GET /account/reset/preview
- `accountApi.reset({password, confirmation})` - POST /account/reset

## A5. Existing Test Coverage: `backend/tests/test_account_reset.py`

**Tests Present**:
1. ✅ `TestResetPreview.test_preview_counts_real_data` - Preview shows real data
2. ✅ `TestResetPreview.test_teacher_cannot_preview` - 403 for teachers
3. ✅ `TestResetExecution.test_wrong_phrase_rejected` - 422 for wrong phrase
4. ✅ `TestResetExecution.test_wrong_password_rejected` - 401 for wrong password
5. ✅ `TestResetExecution.test_reset_wipes_everything_and_keeps_account` - Full reset verification
6. ✅ `TestResetExecution.test_reset_is_rate_limited` - 429 after 3 attempts
7. ✅ `TestResetExecution.test_teacher_cannot_reset` - 403 for teachers

**Gaps in Test Coverage**:
1. ❌ Unauthenticated request test (401)
2. ❌ Data isolation test (2 students, verify only one reset)
3. ❌ Transaction rollback test (simulated failure)
4. ❌ Audit trail test (verify audit records)
5. ❌ Foreign key integrity test
6. ❌ Preview accuracy test (counts match actual)
7. ❌ Admin access test (should be 403)

## A6. Investigation Summary

### Confirmed Problems
1. **No audit trail** - Reset operations not persisted (activity events are wiped by the reset itself)
2. **No explicit deletion verification** - Caller receives counts but no before/after comparison
3. **In-memory rate limiter** - Not shared across processes (documented limitation)
4. **Missing security tests** - Several test scenarios not covered

### Existing Protections That Work
1. ✅ Password verification with bcrypt
2. ✅ Exact confirmation phrase `RESET MY DATA`
3. ✅ Rate limiting (3 attempts / 10 min)
4. ✅ RBAC (student-only endpoints)
5. ✅ Atomic transaction with rollback
5. ✅ Account preservation (user, email, password, role intact)
6. ✅ Data isolation (student_id derived from auth token)
7. ✅ Profile counters zeroed
8. ✅ Frontend two-step confirmation with disabled submit until phrase matches

### Missing Protections
1. ❌ Persistent audit log for reset operations
2. ❌ Before/after deletion count verification
3. ❌ Comprehensive security test coverage

### Relevant Files
- `backend/app/services/student_reset.py` - Core reset logic
- `backend/app/api/routes/account.py` - API endpoints
- `backend/app/api/deps.py` - Auth dependencies
- `backend/app/core/security.py` - Password verification
- `backend/app/core/exceptions.py` - Exception classes
- `frontend/src/pages/student/AccountSettingsPage.tsx` - Danger Zone UI
- `frontend/src/services/api.ts` - API client
- `backend/tests/test_account_reset.py` - Existing tests

### Database Tables Affected (17 tables deleted + profile reset)
See A3 inventory above.

### Security Risks
1. **Audit trail loss** - No permanent record of when/who reset data
2. **No cross-process rate limiting** - Could be bypassed in scaled deployment
3. **Missing test coverage** - Some attack vectors untested

### Proposed Changes

#### 1. Add Audit Log Model & Migration (NEW)
Create minimal audit model for reset operations:
- `reset_audit_log` table: id, student_id, timestamp, status, rows_deleted_json, failure_reason, request_id

#### 2. Enhance StudentResetService
- Add audit logging after successful commit
- Add before/after count verification in response
- Record failure audit on rollback

#### 3. Add Comprehensive Security Tests
- Unauthenticated access
- Data isolation (2 students)
- Transaction rollback simulation
- Audit trail verification
- Admin access rejection

#### 4. Frontend (Minor)
- No major changes needed - UI already solid
- Could add "preview" refresh after reset for UX

#### 5. Migration
- Single new table: `reset_audit_log`

## A7. Proposed Changes Detail

### File: `backend/app/models/audit.py` (NEW)
```python
class ResetAuditLog(Base):
    __tablename__ = "reset_audit_logs"
    id: BIGINT_PK
    student_id: FK to student_profiles
    timestamp: DateTime
    status: String (SUCCESS/FAILED)
    rows_deleted: JSON
    failure_reason: Text (nullable)
    request_id: String (nullable)
```

### File: `backend/app/services/student_reset.py` (MODIFY)
- Import ResetAuditLog
- After successful commit, create audit record in NEW transaction (or same if safe)
- On exception, create FAILED audit record
- Return before/after counts in response

### File: `backend/app/api/routes/account.py` (MODIFY)
- No functional changes needed, just ensure audit data flows through

### File: `backend/tests/test_account_reset.py` (EXTEND)
- Add 7 new test methods for missing scenarios

### File: `backend/alembic/versions/xxx_add_reset_audit_log.py` (NEW)
- Migration for reset_audit_logs table