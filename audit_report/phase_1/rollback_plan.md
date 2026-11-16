# Phase 1 Rollback Plan

## Overview

This document provides the rollback procedure if any issues are discovered after Phase 1 deployment. All changes are backward-compatible and low-risk, but a rollback plan is provided for completeness.

## Changes Summary (Reversible)

| File | Change Type | Risk Level |
|------|-------------|------------|
| `backend/app/seed_demo.py` | Print statements only | None |
| `backend/tests/test_teachers.py` | Test email strings | None |
| `README.md` | Content rewrite | Low (documentation only) |

## Rollback Procedure

### Option 1: Git Revert (Recommended)

```bash
# Revert all Phase 1 changes in one commit
git revert <phase1-commit-hash>

# Or revert specific files
git checkout HEAD~1 -- backend/app/seed_demo.py
git checkout HEAD~1 -- backend/tests/test_teachers.py
git checkout HEAD~1 -- README.md
```

### Option 2: Manual Rollback

#### backend/app/seed_demo.py
```python
# Lines 281-283 - Revert to old print statements
print("  + demo admin:      admin" + DEMO_DOMAIN)
print("  + demo teacher:    teacher" + DEMO_DOMAIN)
print("  + demo students:   aarav/meera/rohan" + DEMO_DOMAIN)
```

#### backend/tests/test_teachers.py
Update all 5 test methods back to use `teacher@skillsprint.com`:
- test_demo_teacher_login
- test_demo_teacher_sees_only_associated_students
- test_demo_student_profile_accessible_to_student_only
- test_demo_teacher_has_no_admin_access
- test_demo_student_login_blocked_for_teacher_with_student_route

Also update the `_demo_teachers` fixture.

#### README.md
Restore from git history:
```bash
git show HEAD~1:README.md > README.md
```

## Verification After Rollback

Run the test suite to confirm rollback works:
```bash
cd backend
python -m pytest tests/test_teachers.py::TestRoleBootstrapDEMO -v
# Should pass with 7 tests using teacher@skillsprint.com
```

## Impact Assessment

| Aspect | Impact of Rollback |
|--------|-------------------|
| Production code | None (only test and docs changed) |
| Database schema | None |
| API contracts | None |
| Demo seed behavior | None (print statements only) |
| Test behavior | Tests revert to using `teacher@skillsprint.com` |
| Documentation | Reverts to duplicate sections and incorrect demo emails |

## No-Rollback-Needed Scenarios

The following scenarios do NOT require rollback:
- Tests pass (current state: 314/314 passing)
- Frontend builds successfully
- TypeScript compiles without errors
- Demo bootstrap verified working with corrected emails

## Contact

If issues arise that require rollback, the changes are minimal and easily reversible via git. All functional code remains unchanged.