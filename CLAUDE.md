# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

An AI-powered running training plan generator with Garmin Connect integration. Users describe their athletic profile and goals; Claude (Anthropic) generates a structured training plan (12 weeks by default) using Jack Daniels VDOT methodology. Plans can be pushed to Garmin Connect as scheduled workouts. Branded Metriq, live at run.fhettinga.nl.

## Repository Structure

```
/
├── backend/    # FastAPI async REST API (production runs Python 3.14)
├── frontend/   # Next.js 15 (React 19) TypeScript app
└── mobile/     # Flutter (Android) client
```

## Working Agreements

- Commit each finished unit of work directly on `main`, with a `[feat]`/`[fix]`/`[chore]`/`[docs]` prefix, and push it to GitHub right away. The server's `./update.sh` pulls `main` with `--ff-only`, so a feature branch never reaches production.
- The repository is **public**. Never commit a key or secret; the CARTO map key belongs only in `frontend/.env.local` on the server.
- Build artifacts that change on a build (`frontend/tsconfig.tsbuildinfo`, `frontend/public/sw.js`, `frontend/public/workbox-*.js`, `mobile/pubspec.lock` after `flutter pub get`) are reverted, not committed.
- User-facing text goes in both `frontend/messages/nl.json` and `en.json`. The app's strings are Dutch.
- Files have CRLF line endings in the Windows working copy; exact multi-line replacements have to allow for that.

## Commands

### Backend
```bash
cd backend
source .venv/bin/activate       # activate virtualenv
pip install -r requirements-dev.txt  # runtime deps + pytest
uvicorn app.main:app --reload   # dev server (port 8000)
pytest                          # run tests
alembic upgrade head            # run DB migrations
alembic revision --autogenerate -m "description"  # create migration
```
The pytest suite is pure functions with no database. Check dependency changes on Python 3.14, the production version.

### Mobile
```bash
cd mobile
flutter pub get
flutter analyze
flutter run
```
The Flutter SDK may not be installed locally. A push touching `mobile/**` builds the APK in GitHub Actions (`.github/workflows/android.yml`, Flutter 3.27.4) and publishes it as a GitHub release, so that build is the check for app code.

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
- **`models/`**: SQLAlchemy 2.0 async models — `User`, `Plan`, `WorkoutSession`, `GarminCredential`, `GarminActivity`, `Friendship`
- **`routers/`**: FastAPI routers — `auth`, `plans`, `sessions`, `garmin`, `friends`, `admin`
- **`services/`**: `claude_service.py` (plan generation, run feedback, weekly review text), `garmin_service.py` (Garmin Connect API, workout payloads), `follow_up.py` (follow-up plans, goal suggestions), `weekly_review.py` (weekly numbers and prompt), `auth_service.py` (PyJWT + passlib/bcrypt), `email_service.py`
- **`database.py`**: Async SQLAlchemy engine with `asyncpg`, connection pool (10/20), `get_db()` dependency

### Frontend (`frontend/src/`)
- **`app/[locale]/`**: Next.js App Router with locale prefix (`/nl/`, `/en/`) via `next-intl`
- **`(auth)/`** route group: login, register pages
- **`dashboard/`**, **`plans/`**, **`analyse/`**, **`friends/`**, **`settings/`**, **`admin/`**: Main app pages
- **`components/`**: `PlanCreatorForm` (multi-step wizard), `Calendar`, `WorkoutCard`, shadcn/ui primitives
- **`lib/api.ts`**: Axios instance with JWT auto-refresh interceptor; a 401, or a 403 with "Not authenticated", counts as a lost session
- **`AuthGuard`** wraps the app sections
- **Prerendered pages**: pages are prerendered per locale (`generateStaticParams`), so server-side `searchParams` is always empty. Read the query client-side with `useSearchParams` inside `<Suspense>`

### Database Schema
```
users (1) → (M) plans
users (1) → (1) garmin_credentials
users (1) → (M) garmin_activities
users (M) ↔ (M) users, through friendships (requester_id, addressee_id)
plans (1) → (M) workout_sessions
```
`WorkoutSession` fields include `week_number`, `day_number`, `workout_type`, `distance`, `paces` (JSON), `intervals` (JSON), and Garmin workout/calendar IDs.

### AI Plan Generation Flow
1. User submits athletic profile (age, weight, goal race, current fitness, preferences) via multi-step form
2. Backend calls Claude (`CLAUDE_PLAN_MODEL`, default `claude-opus-5`, streamed) with a structured JSON schema prompt; optional Garmin activity summary is appended as context
3. Claude returns strict JSON (not markdown) parsed into `WorkoutSession` rows
4. Plan language (NL/EN) is configurable; the AI prompt instructs Claude to respond in the selected language

### Garmin Integration Flow
1. User saves Garmin credentials (Fernet-encrypted in DB)
2. Backend performs mobile SSO login → stores OAuth tokens (also encrypted)
3. `/garmin/sync` fetches 3 months of activities → summarized for Claude context
4. `/garmin/push/sessions` and `/garmin/push/week` create workouts and schedule them on the Garmin calendar. Pushing a session again replaces its old workout
5. Sync matches activities to sessions by date and does not overwrite the planned distance or duration; actuals come from `garmin_activities` via `attach_actuals()`

### Garmin Workout Payload (`_build_workout_payload`)
The workout on the watch has to add up to the session's planned `distance_km`.
- Warm-up and cool-down length: `warmup_km`/`cooldown_km`, else the description ("2 km inlopen"), else what is left of the planned distance after the work and the jogs, split 60/40. The 1000 m / 500 m defaults apply only when too little is left
- One step per rep; a rep with only `duration_seconds` is a timed step, not a distance. Timed jogs are estimated at the slow end of the easy pace. An empty `rest_seconds` means the usual 90 s jog, 0 means none. Recovery is an active jog and is labelled so
- Strides come out of the planned distance
- A faster part inside an easy or long run belongs in `intervals` (reps 1, rest 0), with the easy part in `warmup_km`/`cooldown_km`. For an `easy_run`/`long_run` planned without that, whose warm-up pace is at least 30 s/km slower than its main pace, the finish length comes from the description ("de laatste 3 km"), else a fifth of the run in whole kilometres
- Workouts already on Garmin keep their old structure until they are pushed again

### Run Analysis
The prescribed pace is the verdict; heart rate is evidence. An estimated max HR is hedged, and a high HR at easy pace can be a trait rather than a problem. Work blocks are detected in the pace trace, because the average of an interval session says nothing (`_detect_work_blocks`: 15 s median, threshold halfway between work and easy pace, the planned rep count rejoins a split block). A pace/HR trace goes along every 30 s, or every 60 s past an hour. Target times come only from a race result, not from the efficiency trend.

### Follow-Up Plans
A finished or running plan can start a follow-up (`/plans/new?from=<id>`). `summarise_plan` is stored as `previous_summary` and is based on what was measured, not planned. A race time and distance can override it, and Riegel gives goal suggestions. Aerobic efficiency is distance per heartbeat on easy runs, early in the plan against late. For Base and Tempo users the follow-up replaces the old plan; Elite keeps every plan.

### Weekly Review
Generated in the background after auto-sync, once per plan per week (`review_due`). It is scheduled on every auto-sync call, not only after an actual sync, because the 1-hour sync throttle would otherwise skip it. Every tier gets the numbers; Elite also gets AI text in the plan's feedback tone. If that text fails nothing is stored, so the next sync retries. On the web and in the app the card is folded, except the first time a week's review is seen on that device; the app's expanded content scrolls within a capped height because the card sits outside the scroll view.

## Key Environment Variables

### Backend (`.env`)
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT signing key (≥32 chars, `openssl rand -hex 32`) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `ANTHROPIC_BASE_URL` | Optional API endpoint override (see Open Points) |
| `CLAUDE_MODEL` | Model for the short calls — feedback, pace zones, strength (default `claude-sonnet-4-6`) |
| `CLAUDE_PLAN_MODEL` | Model for full plan generation (default `claude-opus-5`) |
| `GARMIN_ENCRYPTION_KEY` | Fernet key for encrypting Garmin credentials |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `APP_ENV` | `production` on the server. `development` logs every SQL query and creates tables at startup; in production Alembic does that |
| `REGISTRATION_OPEN` | `true`/`false` — gate new user signups |

### Frontend (`.env.local`)
| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL for client-side API calls |
| `NEXT_PUBLIC_CARTO_API_KEY` | Dark map tiles (domain-restricted, sent as `?key=`); without it the map falls back to OSM |

## Notable Patterns

- **Async throughout**: FastAPI + `asyncpg`; use `selectin` loading in SQLAlchemy to avoid `MissingGreenlet` errors in async context
- **JWT auth**: Short-lived access tokens + long-lived refresh tokens; frontend intercepts 401s and silently refreshes via axios interceptor in `lib/api.ts`
- **i18n**: Locale is in the URL path; translations are in `frontend/messages/nl.json` and `en.json`; use `next-intl` hooks (`useTranslations`) in components
- **Garmin credentials**: Never stored or logged in plain text; always use Fernet encryption/decryption via `garmin_service.py`
- **Claude output**: Always instruct Claude to return strict JSON (schema defined in `claude_service.py`); do not rely on markdown parsing
- **Reading a response**: never index `message.content[0]` — thinking models put a thinking block first, and a refusal returns no content at all. Use `_response_text()` in `claude_service.py`
- **Pydantic and old rows**: `from_attributes` falls back to field defaults, so a new response field needs a sensible default for existing data
- **Dependencies are pinned on purpose**: `update.sh` runs `pip install` only when `requirements.txt` changes. Before bumping, compare the calls the app makes and run `pip-audit`. Keep `bcrypt` at 4.0.1 because `passlib` 1.7.4 breaks on 4.1+, and stay on the SQLAlchemy 2.0 series. Since FastAPI 0.132 a JSON body needs an `application/json` content type

## Production

Alpine Linux LXC on Proxmox with OpenRC, app in `/opt/ultimate-running-schedule` (`DEPLOYMENT.md` still shows `/home/runapp/app`), PostgreSQL 18 from `apk`. Services: `runai-backend`, `runai-frontend`, `postgresql`, `nginx`.
- Deploy with `./update.sh` (or `--backend`, `--frontend`, `--both`). It rebuilds only what changed and runs Alembic only when a migration changed
- The frontend has `need runai-backend`: stopping the backend stops the frontend too, and starting the backend does not bring it back. Use `restart`, or start both
- The backend virtualenv is tied to the system Python. An Alpine upgrade that changes the Python minor version breaks it (`failed to exec .venv/bin/uvicorn: No such file or directory`), and it has to be rebuilt. `update.sh` does not detect this. Before such an upgrade, check that the pins have wheels for the new Python
- The PostgreSQL major upgrade procedure is in `DEPLOYMENT.md`

## Open Points

Code:
- `update_plan` and `recalculate-dates` can still leave orphaned workouts on Garmin when a plan is regenerated through an edit
- Max HR priority: the 220−age estimate overrides a measured value (`claude_service.py`). Showing the highest measured HR in settings was also suggested
- `update.sh` could rebuild a virtualenv that belongs to an old Python
- `save_credentials` does not store tokens after a login without MFA, because `return_on_mfa=True` returns before they are written, so the next call logs in again. A wrong MFA code ends the pending session, although garminconnect now allows a retry
- `garminconnect` 0.3.20 is confirmed on production for pushing and removing workouts

Dependencies:
- Maintenance round not done yet: `uvicorn`, `alembic`, `pydantic`, `pydantic-settings`, `asyncpg`, `psycopg2-binary`, `tenacity`, `slowapi`
- `anthropic` 1.2 → 2.x is a major version and needs its own review
- `passlib` is unmaintained; replacing it with `bcrypt` directly would remove the version pin
- Dependabot with a test workflow was proposed, not set up. CI currently only builds the APK

Decisions still to make:
- `ANTHROPIC_BASE_URL` exists for CLIProxyAPI. Running this multi-user app on a personal Claude subscription through a proxy conflicts with Anthropic's terms as understood in October 2026 (check the current terms) and risks the account. The recommended route is an API key with a spending limit, with Batch API, prompt caching and smaller models to reduce cost. No decision or cost estimate yet
- The default models in `config.py` (`claude-sonnet-4-6`, `claude-opus-5`) are not the latest

To check on the server:
- Whether the daily database backup runs (`/var/backups/runai`). The script in `DEPLOYMENT.md` needs the Alpine variant
- The backend listened on `0.0.0.0:8000` instead of `127.0.0.1` (`/etc/init.d/runai-backend`)
- Whether the Proxmox snapshots from the October 2026 upgrades (`voor-pg18`, `voor-alpine-3.24`) have been removed
