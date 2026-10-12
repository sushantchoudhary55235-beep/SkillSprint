# README.md

# SkillSprint

**Gamified, AI‑powered placement‑readiness and personalized learning platform.**

> **Core loop:** `ASSESS → ANALYZE → PERSONALIZE → PRACTICE → REWARD → IMPROVE → REASSESS`

Two primary value propositions:
1. **Personalized learning** — performance analysis drives recommendations, adaptive difficulty, a personalized roadmap, and coaching‑style daily plans.
2. **Gamification that is tied to learning** — XP, levels, streaks, missions, badges, and leaderboards are awarded for real learning activity, not cosmetics.

## What it does

SkillSprint is a student‑facing learning app with teacher and admin workflows on top. Students practice aptitude questions, take mock assessments, solve coding problems, and get a personalized plan. Teachers monitor only the students they explicitly associate. Admins manage users, content, analytics, and platform configuration.

### Student features

- **Auth:** register/login; session persisted via JWT in `localStorage`.
- **Dashboard:** daily plan, recommended next action, placement‑readiness score, weakest topics, recent badges, roadmap progress, quick‑action cards.
- **Aptitude practice:** topic quizzes, daily quiz, practice history.
- **Assessments:** list/start/submit attempts, attempt history, attempt results.
- **Coding practice:** problem list, problem detail with sample test cases, submissions, submission history, personal coding performance.
- **Company preparation:** company list and per‑company preparation profile.
- **Personalization:** roadmap (view, generate, update item status), recommendations (list, generate, complete), skill‑gap analysis, revision feed, revision practice.
- **AI features:** AI‑generated quiz questions and evaluation, chatbot, progressive hints.
- **Gamification:** XP/level summary, missions, badges, activity feed, leaderboard.
- **Coaching extras:** coaching dashboard, daily plan, skill gap, trends, revision, bookmarks, interview preparation.
- **Account:** account settings and a self‑service data‑reset (“danger zone”) with a reset preview.

### Teacher features

- **Teacher dashboard:** class overview with total students, average accuracy, average assessment score, students needing attention, class‑wide weak topics.
- **Student management:** associate students by public Student ID, list associated students with headline metrics, view one associated student in detail, remove an association.
- **Teacher navigation** is role‑aware and only exposes teacher routes and the teacher layout/header link to the teacher dashboard.

### Admin features

- **Admin layout:** sidebar + mobile nav for admin functions.
- **Admin dashboard, users, topics, companies, analytics** (students / questions / submissions / popular topics), and **gamification configuration**, including badge status management.

## Tech stack

| Layer    | Technology |
|----------|------------|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router |
| Backend  | Python, FastAPI, Pydantic, SQLAlchemy, Alembic, JWT |
| Database | PostgreSQL in production; SQLite is used for lightweight local dev/testing |
| AI       | Google Gemini API — accessed only through the backend, never exposed to the frontend |

## Repository structure

```
SkillSprint/
├── frontend/            React + TypeScript + Vite app
│   ├── src/
│   │   ├── context/     auth context
│   │   ├── layouts/     MainLayout (student/teacher shell)
│   │   ├── pages/       pages by role: admin/, student/, teacher/
│   │   ├── services/    API clients
│   │   ├── types/       shared frontend types
│   │   └── App.tsx      route tree + role protection
├── backend/             FastAPI app
│   ├── app/
│   │   ├── api/routes/  HTTP routers
│   │   ├── core/        configuration, security, exceptions, rate limiting
│   │   ├── db/          session / engine
│   │   ├── models/      SQLAlchemy models
│   │   ├── repositories/ data access
│   │   ├── schemas/     Pydantic request/response schemas
│   │   ├── services/    business logic
│   │   └── utils/       helpers
│   ├── alembic/         migrations
│   ├── tests/           pytest suite using isolated in‑memory SQLite fixtures
│   └── .env.example     environment variable template
├── docs/                PRD, SRS, API spec, DB design, phases, UX, deployment notes
└── README.md
```

## Local setup prerequisites

- Node.js with npm (frontend)
- Python 3 + pip (backend)
- Git

Do **not** commit `.env`, local databases, `node_modules/`, `__pycache__/`, or test artifacts.

## Frontend startup

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173` — Vite proxies `/api` to the backend.

Available frontend scripts:
- `npm run dev` — start Vite dev server
- `npm run build` — type‑check then build for production
- `npm run lint` — run ESLint
- `npm run preview` — preview production build locally

## Backend startup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows
# source .venv/Scripts/activate   # bash
pip install -r requirements.txt
cp .env.example .env              # edit .env before use
python -m app.main
```

If you are using the provided virtualenv already present in the repo, activate it instead of creating a new one.

Backend entrypoint: `python -m app.main` (FastAPI app lives in `backend/app/main.py`).

API docs: `http://localhost:8000/docs` when the server is running in non‑production mode.

Health endpoint: `http://localhost:8000/api/health`

## Environment variables

Copy `backend/.env.example` to `backend/.env` and adjust the values. The example already contains placeholders. Key variables:

- `DATABASE_URL` — e.g. `sqlite:///./skillsprint.db` for local dev, or a PostgreSQL URL for production
- `JWT_SECRET_KEY` — **must be changed** from the placeholder in any real environment
- `JWT_ALGORITHM` — default `HS256`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` — default `60`
- `BCRYPT_ROUNDS` — password hashing cost; production default `12`
- `CORS_ORIGINS` — comma‑separated allowed origins; default `http://localhost:5173`
- `GEMINI_API_KEY` — Gemini API key; leave empty only if you do not need AI features
- `AI_RATE_LIMIT_PER_MINUTE` — AI request budget per user per minute; default `10`
- `CODE_EXECUTOR_URL` — in production, URL of an isolated code‑execution sidecar; unset means the local development executor
- `ADMIN_SEED_EMAIL` / `ADMIN_SEED_PASSWORD` — admin seed defaults; change immediately after first run in any non‑local environment
- `ENVIRONMENT` — e.g. `development` or `production`
- `LOG_LEVEL` — e.g. `INFO`

### Important security defaults

- `JWT_SECRET_KEY` defaults to `change-me-to-a-long-random-secret` and **must be overridden** outside local development.
- `CORS_ORIGINS` defaults to localhost origins only; a wildcard is not the default.
- `GEMINI_API_KEY` defaults to empty; AI endpoints can return `503` when it is missing.
- `CODE_EXECUTOR_URL` defaults to empty, which falls back to the local development executor.

## Database and migrations

The backend uses SQLAlchemy with Alembic for schema migrations.

Development/test default: SQLite at `backend/skillsprint.db` via `DATABASE_URL=sqlite:///./skillsprint.db`.

Production target: PostgreSQL.

To apply migrations:

```bash
cd backend
alembic upgrade head
```

This repository contains migration files under `backend/alembic/versions/`. Migrations are **not** executed automatically by this README; run them manually when appropriate for your environment.

Do not run migrations against a database you cannot recreate. The local default database file is gitignored.

## Demo / seed data

The backend includes seed scripts:
- `backend/app/seed.py`
- `backend/app/seed_demo.py`

These are available for local demonstration and testing. They are **not** run automatically by this README. Review them before using them against any database that is not disposable.

## Testing

### Frontend

```bash
cd frontend
npm run build        # also runs tsc -b
npm run lint
```

TypeScript type‑checking can also be run directly:

```bash
cd frontend
npx tsc --noEmit
```

### Backend

The backend test suite uses isolated in‑memory SQLite fixtures and does not depend on a persistent database.

#### Focused runs

```bash
cd backend
python -m pytest -q tests/test_auth.py tests/test_feature_groups.py tests/test_teachers.py tests/test_config_guard.py tests/test_practice.py
```

This project’s verified test subset in the current working tree:
- `tests/test_auth.py`
- `tests/test_feature_groups.py`
- `tests/test_teachers.py`
- `tests/test_config_guard.py`
- `tests/test_practice.py`

#### Full suite

A full backend run is practical here because the suite uses in‑memory fixtures:

```bash
cd backend
python -m pytest -q
```

If any test cannot run because dependencies or environment are missing, report that instead of faking a pass.

Test files present in the current backend tree:
- `tests/test_account_reset.py`
- `tests/test_admin_dashboard.py`
- `tests/test_ai.py`
- `tests/test_ai_questions.py`
- `tests/test_assessments.py`
- `tests/test_auth.py`
- `tests/test_coding.py`
- `tests/test_config_guard.py`
- `tests/test_content_api.py`
- `tests/test_feature_groups.py`
- `tests/test_gamification.py`
- `tests/test_health.py`
- `tests/test_integration_phase15.py`
- `tests/test_migrations.py`
- `tests/test_models.py`
- `tests/test_performance.py`
- `tests/test_practice.py`
- `tests/test_recommendations.py`
- `tests/test_roadmap.py`
- `tests/test_security.py`
- `tests/test_teachers.py`

## API documentation

Backend API docs are available at runtime at `/docs` when the server is running in non‑production mode.

Design‑time API documentation lives in `docs/API_Specification.md` (when present).

Other design docs:
- `docs/PRD.md`
- `docs/Database_design_docs.md`
- `docs/Phases.md`
- `docs/UX_UserFlow.md`
- `docs/DEPLOYMENT.md`
- `docs/System_Overview.md`

## Current limitations

- **AI features depend on external API access.** Gemini features require `GEMINI_API_KEY`. Without it, relevant endpoints can return `503`.
- **The default code executor is for development only.** With `CODE_EXECUTOR_URL` unset, the backend uses a local subprocess executor. That is **not** a secure sandbox and must not be used for untrusted code in production. Production execution requires an isolated sidecar referenced by `CODE_EXECUTOR_URL`.
- **Rate limiting is in‑memory.** The AI rate limiter is correct for a single‑process deployment. Horizontal scaling would need a shared backend such as Redis.
- **This is not a production‑hardened deployment guide.** Secrets, CORS, JWT secret, code execution, and database choice must all be reviewed before any production use.

## Security and deployment checklist

Before any production deployment:
- Set a real `JWT_SECRET_KEY`.
- Set `ENVIRONMENT=production`.
- Configure explicit `CORS_ORIGINS` (no wildcard).
- Point `CODE_EXECUTOR_URL` at an isolated execution service; do not rely on the local executor.
- Use PostgreSQL, not the SQLite development default.
- Run migrations against the production database.
- Rotate `ADMIN_SEED_EMAIL` / `ADMIN_SEED_PASSWORD` immediately after first seed.
- Disable OpenAPI/docs exposure in production if desired (the app already hides `/docs` and `/openapi.json` when `ENVIRONMENT=production`).
- Ensure `.env` is never committed.

## Status of this repository

This README reflects the current project as found in the repository. It does not claim the application is production‑ready. Several backend tests exist and pass in isolated fixtures; live runtime behavior against a real database and real external services is a separate verification step.
