# Phase 1 Documentation Changes

## Summary of Changes

### README.md — Complete Rewrite

**Before**: 418 lines with extensive duplicate sections
**After**: ~220 lines, single authoritative sections, corrected demo docs

#### Duplicate Sections Removed

| Section | Occurrences Before | Occurrences After |
|---------|-------------------|-------------------|
| Local setup prerequisites (SETUP) | 2 | 1 |
| Frontend startup (FRONTEND) | 3 | 1 |
| Backend startup (BACKEND) | 3 | 1 |
| Environment variables (ENVIRONMENT) | 2 | 1 |
| Database and migrations (MIGRATIONS) | 2 | 1 |
| Demo / seed data (DEMO SEEDING) | 2 | 1 |
| Testing (TESTS) — Frontend | 2 | 1 |
| Testing (TESTS) — Backend | 2 | 1 |

#### Demo Account Documentation Fixed

**Before (Incorrect)**:
```
Demo accounts (password: Demo#Pass123):
- admin@skillsprint.com (admin; also created by seed.py + ADMIN_SEED_* env)
- teacher@skillsprint.com (teacher) — login: teacher@skillsprint.com / Demo#Pass123
- demo.aarav@demo.skillsprint.dev, demo.meera@demo.skillsprint.dev, demo.rohan@demo.skillsprint.dev (students, 3 seeded links)
```

**After (Correct)**:
```
### Production seed (seed.py)
Creates admin user (from ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD env, defaults to admin@skillsprint.com / ChangeMe!123), core topics, companies, badges, and missions.

### Development-only demo seed (seed_demo.py)
Demo accounts (password: Demo#Pass123 — public placeholder, never reuse):
- demo.admin@demo.skillsprint.dev (admin)
- demo.teacher@demo.skillsprint.dev (teacher)
- demo.aarav@demo.skillsprint.dev, demo.meera@demo.skillsprint.dev, demo.rohan@demo.skillsprint.dev (students, 3 seeded teacher-student links)
```

#### Structural Improvements

1. **Clear separation** between production seed (`seed.py`) and demo seed (`seed_demo.py`)
2. **Single source of truth** for each setup step
3. **Corrected email domains**: All demo users now consistently use `@demo.skillsprint.dev`
4. **Removed redundant pipe characters** (`|`) that were artifacts from previous edits
5. **Consistent formatting** for code blocks and command examples

---

### seed_demo.py — Print Statement Fix

**File**: `backend/app/seed_demo.py` (lines 281-283)

**Before**:
```python
print("  + demo admin:      admin" + DEMO_DOMAIN)
print("  + demo teacher:    teacher" + DEMO_DOMAIN)
print("  + demo students:   aarav/meera/rohan" + DEMO_DOMAIN)
```

**After**:
```python
print("  + demo admin:      demo.admin" + DEMO_DOMAIN)
print("  + demo teacher:    demo.teacher" + DEMO_DOMAIN)
print("  + demo students:   demo.aarav/demo.meera/demo.rohan" + DEMO_DOMAIN)
```

**Reason**: The `_user()` function creates emails as `name.lower().replace(" ", ".") + DEMO_DOMAIN`, so:
- "Demo Admin" → `demo.admin@demo.skillsprint.dev`
- "Demo Teacher" → `demo.teacher@demo.skillsprint.dev`
- "Demo Aarav" → `demo.aarav@demo.skillsprint.dev`

The old print statements showed the wrong emails, causing confusion.

---

### test_teachers.py — Test Email Alignment

**File**: `backend/tests/test_teachers.py` (TestRoleBootstrapDEMO class)

**Changes**: Updated 5 test methods to use `demo.teacher@demo.skillsprint.dev` instead of `teacher@skillsprint.com`

| Method | Line | Old Email | New Email |
|--------|------|-----------|-----------|
| test_demo_teacher_login | ~190 | teacher@skillsprint.com | demo.teacher@demo.skillsprint.dev |
| test_demo_teacher_sees_only_associated_students | ~200 | teacher@skillsprint.com | demo.teacher@demo.skillsprint.dev |
| test_demo_student_profile_accessible_to_student_only | ~218 | teacher@skillsprint.com | demo.teacher@demo.skillsprint.dev |
| test_demo_teacher_has_no_admin_access | ~237 | teacher@skillsprint.com | demo.teacher@demo.skillsprint.dev |
| test_demo_student_login_blocked_for_teacher_with_student_route | ~247 | teacher@skillsprint.com | demo.teacher@demo.skillsprint.dev |

**Fixture** (`_demo_teachers`): Also updated teacher creation email to match.

**Reason**: Align test with the official demo seed script (`seed_demo.py`) so documentation, seed, and tests all agree on the demo account emails.

---

### Files Not Modified (Already Consistent)

- `backend/app/seed.py` — Creates `admin@skillsprint.com` from `ADMIN_SEED_EMAIL` env var (documented correctly in README)
- `backend/.env.example` — Documents `ADMIN_SEED_EMAIL=admin@skillsprint.com` (consistent with seed.py)
- `docs/Phases.md` — No references to demo accounts, no changes needed