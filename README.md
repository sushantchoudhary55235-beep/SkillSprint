# SkillSprint

Gamified AI-powered placement-readiness and personalized learning platform.

## Core Product Loop

> **ASSESS → ANALYZE → PERSONALIZE → PRACTICE → REWARD → IMPROVE → REASSESS**

Two primary USPs:
1. **Personalized Learning** — performance analysis drives recommendations and an adaptive roadmap.
2. **Gamification** — XP, levels, streaks, missions, badges, and leaderboards are integrated with learning, not cosmetic.

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router |
| Backend  | Python, FastAPI, Pydantic, SQLAlchemy, Alembic, JWT |
| Database | PostgreSQL (SQLite permitted for lightweight local dev) |
| AI       | Google Gemini API — accessed only through the backend |

## Project Structure

```
SkillSprint/
├── frontend/          React + TypeScript + Vite app
├── backend/           FastAPI app
│   ├── app/
│   │   ├── core/        configuration & security
│   │   ├── api/routes/  HTTP routers
│   │   ├── models/      SQLAlchemy models
│   │   ├── schemas/     Pydantic schemas
│   │   ├── services/    business logic
│   │   ├── repositories/ data access
│   │   ├── db/          database session/engine
│   │   └── utils/       helpers
│   ├── alembic/         migrations
│   └── tests/           pytest suite
├── docs/              PRD, SRS, API spec, DB design, phases
└── scripts/           helper scripts
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (bash: source .venv/Scripts/activate)
pip install -r requirements.txt
copy .env.example .env          # bash: cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs — Health: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (proxies `/api` to the backend).

### Migrations

```bash
cd backend
alembic upgrade head
```

## Documentation

See `docs/` — `PRD.md`, `Software_requirements_specifications.md`, `API_Specification.md`, `Database_design_docs.md`, `Phases.md`, `UX_UserFlow.md`.

## Development Phases

Development follows `docs/Phases.md`. Current status is tracked in that document; Phase 1 (project foundation) is in progress.
