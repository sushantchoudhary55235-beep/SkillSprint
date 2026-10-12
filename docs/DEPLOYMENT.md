# SkillSprint — Phase 16 Deployment Guide

## Architecture

```
Vercel (frontend)  --HTTPS-->  Railway/Render (FastAPI)  -->  Managed PostgreSQL
                                    |
                                    +--> Gemini API (key server-side only)
                                    +--> Sandbox code-executor sidecar (CODE_EXECUTOR_URL)
```

## 1. Environment variables

Copy `.env.example` → `backend/.env` locally, or set them in the hosting
dashboard. Required variables:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Managed PostgreSQL (Railway/Neon/Supabase/RDS). Never SQLite in production. |
| `JWT_SECRET_KEY` | Long random string (`openssl rand -hex 32`). |
| `GEMINI_API_KEY` | Server-side only. Never exposed in API responses or logs. |
| `CORS_ORIGINS` | Exact frontend origin(s), comma-separated. `*` is **refused at startup** in production. |
| `ENVIRONMENT` | `production` — disables `/docs` and enforces CORS validation. |
| `CODE_EXECUTOR_URL` | Production sandbox runner URL (local subprocess executor is dev-only). |

The real `.env` is git-ignored.

## 2. Backend (Railway or Render)

1. Create a service from the repo, root directory `backend/`.
2. Start command: `python start.sh` (runs `alembic upgrade head`, then uvicorn).
   - Railway: a `Procfile` is included (`release:` runs migrations, `web:` starts the app).
3. Add all env vars above in the dashboard.
4. Provision managed PostgreSQL and link `DATABASE_URL`.
5. Verify: `GET https://<backend-url>/api/health` returns `200`.
6. HTTPS is automatic on both platforms — never serve production over plain HTTP.

## 3. Database

- Run migrations: `alembic upgrade head` (automatic with the start script/Procfile).
- Seed required data (topics, companies, badges, missions, admin):
  ```bash
  python -m app.seed
  ```
  Idempotent — safe to run on every deploy. Set `ADMIN_SEED_EMAIL` /
  `ADMIN_SEED_PASSWORD` first for the admin account.

## 4. Frontend (Vercel)

1. Import the repo, root directory `frontend/`.
2. Environment variable: `NEXT_PUBLIC_API_URL` is not needed for same-origin
   setups; for split deployments set the Vite proxy replacement by pointing
   the API base URL at the backend domain (see `frontend/src/services/api.ts`).
3. Deploy, then set the deployed frontend URL in the backend's `CORS_ORIGINS`.
4. Verify login, a quiz attempt, and a code submission against the live backend.

## 5. Post-deployment checks

- [ ] Login as Student, Teacher, and Admin from the live site.
- [ ] AI question generation works (needs a real `GEMINI_API_KEY`).
- [ ] Code submission runs against test cases.
- [ ] Deactivating a user in Admin → their next request gets 401.
- [ ] Browser network tab shows **no** API keys or secrets in any response.
- [ ] AI rate limit returns 429 after 10 rapid generations.
