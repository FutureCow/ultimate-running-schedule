# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

An AI-powered running training plan generator with Garmin Connect integration. Users describe their athletic profile and goals; Claude (Anthropic) generates a structured 12-week training plan using Jack Daniels VDOT methodology. Plans can be pushed to Garmin Connect as scheduled workouts.

## Repository Structure

```
/
├── backend/    # FastAPI (Python 3.12) async REST API
└── frontend/   # Next.js 15 (React 19) TypeScript app
```

## Commands

### Backend
```bash
cd backend
source .venv/bin/activate       # activate virtualenv
uvicorn app.main:app --reload   # dev server (port 8000)
alembic upgrade head            # run DB migrations
alembic revision --autogenerate -m "description"  # create migration
```

### Frontend
```bash
cd frontend
npm run dev          # dev server (port 3000)
npm run build        # production build
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

## Architecture

### Backend (`backend/app/`)
- **`main.py`**: App entrypoint, startup hooks (`init_db` in dev, table creation)
- **`models/`**: SQLAlchemy 2.0 async models — `User`, `Plan`, `WorkoutSession`, `GarminCredential`
- **`routers/`**: FastAPI routers — `auth`, `plans`, `sessions`, `garmin`
- **`services/`**: `claude_service.py` (AI plan generation), `garmin_service.py` (Garmin Connect API), `auth_service.py` (JWT + bcrypt)
- **`database.py`**: Async SQLAlchemy engine with `asyncpg`, connection pool (10/20), `get_db()` dependency

### Frontend (`frontend/src/`)
- **`app/[locale]/`**: Next.js App Router with locale prefix (`/nl/`, `/en/`) via `next-intl`
- **`(auth)/`** route group: login, register pages
- **`dashboard/`**, **`plans/`**, **`settings/`**: Main app pages
- **`components/`**: `PlanCreatorForm` (multi-step wizard), `Calendar`, `WorkoutCard`, shadcn/ui primitives
- **`lib/api.ts`**: Axios instance with JWT auto-refresh interceptor

### Database Schema
```
users (1) → (M) plans
users (1) → (1) garmin_credentials
plans (1) → (M) workout_sessions
```
`WorkoutSession` fields include `week_number`, `day_number`, `workout_type`, `distance`, `paces` (JSON), `intervals` (JSON), and Garmin workout/calendar IDs.

### AI Plan Generation Flow
1. User submits athletic profile (age, weight, goal race, current fitness, preferences) via multi-step form
2. Backend calls Claude Opus 4.5 with a structured JSON schema prompt; optional Garmin activity summary is appended as context
3. Claude returns strict JSON (not markdown) parsed into `WorkoutSession` rows
4. Plan language (NL/EN) is configurable; the AI prompt instructs Claude to respond in the selected language

### Garmin Integration Flow
1. User saves Garmin credentials (Fernet-encrypted in DB)
2. Backend performs mobile SSO login → stores OAuth tokens (also encrypted)
3. `/garmin/sync` fetches 3 months of activities → summarized for Claude context
4. `/garmin/push-workouts` creates workout entries on Garmin Connect calendar

## Key Environment Variables

### Backend (`.env`)
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT signing key (≥32 chars, `openssl rand -hex 32`) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `ANTHROPIC_BASE_URL` | Optional proxy (e.g. CLIProxyAPI at `http://localhost:8317`) |
| `GARMIN_ENCRYPTION_KEY` | Fernet key for encrypting Garmin credentials |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `APP_ENV` | `development` or `production` |
| `REGISTRATION_OPEN` | `true`/`false` — gate new user signups |

### Frontend (`.env.local`)
| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL for client-side API calls |

## Notable Patterns

- **Async throughout**: FastAPI + `asyncpg`; use `selectin` loading in SQLAlchemy to avoid `MissingGreenlet` errors in async context
- **JWT auth**: Short-lived access tokens + long-lived refresh tokens; frontend intercepts 401s and silently refreshes via axios interceptor in `lib/api.ts`
- **i18n**: Locale is in the URL path; translations are in `frontend/messages/nl.json` and `en.json`; use `next-intl` hooks (`useTranslations`) in components
- **Garmin credentials**: Never stored or logged in plain text; always use Fernet encryption/decryption via `garmin_service.py`
- **Claude output**: Always instruct Claude to return strict JSON (schema defined in `claude_service.py`); do not rely on markdown parsing
