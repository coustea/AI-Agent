# AGENTS.md

Vue 3 + TypeScript frontend (`src/`) + FastAPI + SQLModel backend (`server/`).

**Critical constraint**: `resource` (standalone resource generation) and `path` (learning-path planning) share agent infrastructure but **do not** merge their records, detail pages, or persistence models.

## Commands

### Frontend (repo root)
```bash
npm run build    # vue-tsc -b && vite build — the only frontend check (no linter)
npm run dev      # Vite dev server on :5173
```

### Backend (`server/`)
```bash
uv sync                                  # install Python deps (requires Python >=3.13)
uv run fastapi dev app/main.py --port 9999
uv run pytest                            # all tests
uv run pytest -x                         # stop on first failure
uv run pytest tests/chat/ -q             # single module
```

## Ports & Proxy

| Service | Port |
|---------|------|
| Vite dev server | 5173 |
| FastAPI backend | 9999 |

`vite.config.ts` proxies `/api` → `http://127.0.0.1:9999` and `/ws` → `ws://127.0.0.1:9999`. Configurable via `VITE_API_PROXY_TARGET`. Proxy mismatch → 500s.

## Testing

Backend: `pytest` + `pytest-asyncio`. Tests in `server/tests/` mirror `server/app/`. `conftest.py` adds `server/` to `sys.path`.

Pre-existing failures (do not debug):
- `tests/chat/test_agent_single_module_refactor.py`
- `tests/chat/test_onboarding_api.py`
- `tests/chat/test_reasoning_agent.py`

Frontend has no tests.

## Coding Style

- Frontend: TypeScript, Vue SFCs `<script setup lang="ts">` + `<style scoped>`, 2-space indent, no semicolons. Components `PascalCase.vue`, composables `useXxx.ts`.
- Backend: 4-space indent, type hints, snake_case modules.
- No linter config is committed — validate with `npm run build` / `uv run pytest`.

## Architecture

### Startup & Routing
`server/app/main.py` (create_app → lifespan → install_routes). No `app_factory.py` or `lifecycle.py`.

API prefixes (from `server/app/routes.py`):
- `/api/v1/users` — auth
- `/api/v1/ai/*` — chat, resource, path, dashboard, evaluation, quiz/quiz-bank/wrong-questions, avatar
- `/ws/avatar` — WebSocket (from `ws.py`)

All responses use `HttpResponse` envelope: `{code, message, data}` (see `app/infra/response.py`).

### Auth
JWT + `ActiveToken` whitelist. `get_current_user` / `get_current_user_flexible` in `app/auth/security.py` inject the request-scoped `AsyncSession` directly — **never** use `session_scope()` inside auth deps (causes detached-User greenlet errors).

### Database
PostgreSQL via `asyncpg`. Dual source of truth:
- `server/init_schema.sql` — bootstrap SQL
- `server/app/infra/models.py` — SQLModel definitions

Startup does **not** reconcile drift. New tables must be added to `REGISTERED_MODELS` tuple at the bottom of `models.py`.

Session patterns:
- `get_session()` — FastAPI DI, `expire_on_commit=False`, no auto-commit
- `session_scope()` — context manager, auto-commit, for background tasks

### Configuration
`server/config.yaml` only (no `.env`). Loaded by `app/config.py`. Key groups: `app`, `database`, `jwt`, `models`, `spark`, `avatar`, `search`, `paths`, `knowledge`, `memory`, `chat`.

### Backend module pattern
Each domain under `server/app/` follows `api.py` → `service.py` → schemas. The `infra/` module holds shared infrastructure: `database.py`, `models.py`, `llm.py`, `response.py`, `prompts/`, `logging.py`, `context.py`.

## Commit Convention
Short conventional prefixes: `feat:`, `fix:`, `refactor:`. Chinese or English summaries. Keep commits focused.
