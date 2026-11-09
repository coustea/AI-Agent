# AGENTS.md

Vue 3 + TypeScript frontend (`src/`) + FastAPI + SQLModel backend (`server/`).

**Critical constraint**: `resource` (standalone resource generation) and `path` (learning-path planning) share agent infrastructure but **do not** merge their records, detail pages, or persistence models.

## Commands

### Frontend (repo root)
```bash
npm run build     # vue-tsc -b && vite build — type check + production build
npm run dev       # Vite dev server on :5173
npm run test:run  # Vitest suite
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

`vite.config.ts` proxies `/api` and `/static` → `http://127.0.0.1:9999`. Configurable via `VITE_API_PROXY_TARGET`. Proxy mismatch → 500s.

## Testing

Backend: `pytest` + `pytest-asyncio`. Tests in `server/tests/` mirror `server/app/`. `conftest.py` adds `server/` to `sys.path`.

Use `with TestClient(app)` (not bare `TestClient(app)`) when a test needs the app lifespan — a bare client never runs startup, so startup-time breakage goes undetected.

Frontend: `npm run test:run` (Vitest + jsdom). Tests live next to the code as `*.test.ts`.

## Coding Style

- Frontend: TypeScript, Vue SFCs `<script setup lang="ts">` + `<style scoped>`, 2-space indent, no semicolons. Components `PascalCase.vue`, composables `useXxx.ts`.
- Backend: 4-space indent, type hints, snake_case modules.
- **Function Contract & Docstrings**: 每个函数/方法（包括异步函数、内部辅助函数及闭包）**必须**具备完整的参数与返回值类型注解，并第一行提供精炼准确的中文 docstring 说明，格式规范如下：
  ```python
  async def build_messages(ctx: TutorInput) -> list[Message]:
      """构建完整的本轮消息列表（System + 历史 + 本轮 User）。"""
  ```
- No linter config is committed — validate with `npm run build` / `uv run pytest`.

## Architecture

### Startup & Routing
`server/app/main.py` (create_app → lifespan → install_routes). No `app_factory.py` or `lifecycle.py`.

API prefixes (from `server/app/routes.py`):
- `/api/v1/users` — auth
- `/api/v1/ai/*` — chat, resource, path, dashboard, evaluation, quiz/quiz-bank/wrong-questions

All responses use `HttpResponse` envelope: `{code, message, data}` (see `app/response.py`).

### Auth
JWT + `ActiveToken` whitelist. `JWTMiddleware` (`app/middleware/jwt.py`) decodes the token and stores `UserClaims` in the `current_user_ctx` ContextVar; `get_current_user()` in `app/auth/security.py` is a **zero-argument** helper that reads that ContextVar (no DB I/O). SSE endpoints pass the token as `?token=` because `EventSource` cannot set headers.

### Database
MySQL via `aiomysql`. Single source of truth:
- `server/app/infra/models.py` — SQLModel definitions

`init_db()` runs `SQLModel.metadata.create_all` at startup, which creates missing tables but **never alters existing ones**. After changing a column type or length, drop and recreate the database.

MySQL-specific conventions:
- Time columns use `UtcDateTime` (`app/infra/types.py`) — stored as UTC `DATETIME(6)`, read back as aware UTC
- JSON columns use `sqlalchemy.JSON`; they are **not indexed** (MySQL only indexes JSON via generated columns + JSON path)
- UUID primary keys are `String(36)` holding the standard hyphenated uuid string
- `pool_pre_ping` is intentionally disabled (SQLAlchemy 2.0.49 + aiomysql signature mismatch); `pool_recycle` covers stale connections

Session patterns:
- `get_session()` — FastAPI DI, `expire_on_commit=False`, no auto-commit
- `session_scope()` — context manager, auto-commit, for background tasks

### Configuration
`server/config.yaml` only (no `.env`). Loaded by `app/config.py`. Key groups: `app`, `database`, `jwt`, `models`, `search`, `paths`, `knowledge`, `memory`, `chat`, `resource`, `quiz`, `video`.

### Backend module pattern
Each domain under `server/app/` follows `api.py` → `service.py` → schemas. The `infra/` module holds shared infrastructure: `database.py`, `models.py`, `llm.py`, `types.py`, `utils.py`, `seed.py`, `logging.py`. The response envelope lives at `app/response.py`.

## Commit Convention
Short conventional prefixes: `feat:`, `fix:`, `refactor:`. Chinese or English summaries. Keep commits focused.
