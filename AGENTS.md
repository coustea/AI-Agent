# Repository Guidelines

## Project Structure

Vue 3 + TypeScript frontend (`src/`) + FastAPI + SQLModel backend (`server/`). Two distinct business domains reuse agent infrastructure but must stay separate:
- **Standalone resource generation** (`resource` domain)
- **Learning-path planning** (`path` domain)

Do not merge their records, detail pages, or persistence models.

### Frontend (`src/`)
- `src/app/` — router, layouts, guards, providers
- `src/features/` — domain features: `auth`, `chat`, `dashboard`, `learning`, `profile`, `resource`
- `src/shared/` — API clients (`src/shared/api/`), auth helpers, UI components, types

### Backend (`server/app/`)
Each domain follows `api.py` → `service.py` → schemas pattern:
- `auth` — registration, login, JWT, user info
- `chat` — streaming tutor, uploads, history, diagram generation
- `resource` — multi-agent resource generation
- `path` — learning-path planning, node workspace, evaluation
- `profile` — learner profile inference and storage
- `evaluation`, `dashboard`, `quiz`, `avatar`, `infra`, `ws_routes`

Startup wiring: `app_factory.py` → `lifecycle.py` → `routes.py`

## Commands

### Frontend (from repo root)
```bash
npm run build    # vue-tsc + vite build — use this as the automated check (no ESLint/Prettier)
npm run dev      # Vite dev server
```

### Backend (from `server/`)
```bash
uv sync                                          # install Python deps
uv run fastapi dev app/main.py --port 9999       # dev server with reload
uv run pytest                                    # run all tests
uv run pytest tests/chat/test_history.py -q      # run single test file
uv run pytest -x                                 # stop on first failure
```

## Port Configuration

Backend runs on port **9999** (set in `server/config.yaml`). The Vite proxy in `vite.config.ts` must match:
- `/api` → `http://127.0.0.1:9999`
- `/ws` → `ws://127.0.0.1:9999`

If these get out of sync, API calls from the frontend will 500.

## Coding Style

- Frontend: TypeScript, Vue SFCs, 2-space indent, no semicolons. Components `PascalCase.vue`, composables `useXxx.ts`.
- Backend: 4-space indent, type hints, snake_case modules.
- Vue files must use `<script setup lang="ts">` and `<style scoped>`. See `docs/vue-code-style.md`.

No linter configs are committed. Validate with `npm run build` (frontend) and `uv run pytest` (backend).

## Testing

Backend: `pytest` + `pytest-asyncio`. Tests in `server/tests/` mirror `server/app/` paths. Name files `test_*.py`.

Known pre-existing test failures (do not waste time debugging):
- `tests/chat/test_agent_single_module_refactor.py` — stale assertion on `_decide` function
- `tests/chat/test_onboarding_api.py` — missing `background_tasks` arg in direct asyncio.run call
- `tests/chat/test_reasoning_agent.py` — `FakeLlm` missing `astream` attribute

Frontend has no automated tests.

## Architecture Notes

### API Routes (`server/app/routes.py`)
Actual mounted prefixes:
- `/api/v1/users` — auth/user endpoints
- `/api/v1/ai/*` — chat, resources, path-plan, dashboard, evaluation, quiz, avatar, wrong-questions

### Auth
JWT-based with `ActiveToken` whitelist table. `get_current_user` and `get_current_user_flexible` in `app/auth/security.py` inject the request-scoped `AsyncSession` directly — do **not** use a separate `session_scope()` in auth dependencies, or the returned `User` becomes detached and triggers greenlet errors.

### Database
PostgreSQL via `asyncpg`. Schema lives in `server/init_schema.sql`; SQLModel definitions in `server/app/infra/models.py`. Keep them in sync — startup does not reconcile schema drift.

Two session patterns:
- `get_session()` — FastAPI DI, `expire_on_commit=False`, no auto-commit
- `session_scope()` — explicit context manager, auto-commit, for background tasks outside DI

### Configuration
All runtime config in `server/config.yaml`, loaded by `server/app/config.py`. Not `.env`. Key families: `app`, `database`, `jwt`, `models`, `spark`, `avatar`, `search`, `paths`, `knowledge`, `memory`, `chat`.

### Commit Convention
Short conventional prefixes: `feat:`, `fix:`, `refactor:`. Chinese or English summaries both used. Keep commits focused.
