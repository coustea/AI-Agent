# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent personalized learning platform (多智能体个性化学习资源平台). Full-stack monorepo with two workspaces:
- `src/` — Vue 3 + TypeScript frontend
- `server/` — FastAPI + SQLModel backend

Two business flows stay deliberately separate even though they reuse some agent infrastructure:
- **Standalone resource generation** (`resource` domain)
- **Learning-path planning and node learning** (`path` domain)

Do not merge their records, detail pages, or persistence models back together.

## Common Commands

### Frontend (run from repo root)

```bash
npm install
npm run dev
npm run build          # runs vue-tsc -b && vite build — main frontend validation path
npm run preview
```

- No committed frontend linter; run `npm run build` (type check) and `npm run test:run` (Vitest).
- `vite.config.ts` proxies `/api` and `/static` to `http://127.0.0.1:9999` by default, overridable with `VITE_API_PROXY_TARGET`.

### Backend (run from `server/`)

```bash
uv sync
uv run fastapi dev app/main.py --port 9999
uv run python app/main.py
uv run pytest                                          # all tests
uv run pytest tests/chat/test_history.py -q            # single file
uv run pytest tests/chat/test_history.py -q -k summary # single test by keyword
uv run pytest -x                                       # stop on first failure
```

- Requires Python `>=3.13`.
- FastAPI docs at `/docs` on the configured backend port.
- `pytest` is the main backend verification path.

## High-Level Architecture

### Frontend shape

Organized by app shell + feature domains:
- `src/app/` — router, layouts, app-level wiring
- `src/features/` — `auth`, `chat`, `dashboard`, `learning-path`, `profile`, `question-bank`, `resource`
- `src/shared/` — `api`, `auth`, `content`, `markdown`, `model`, `styles`, `ui`

Routing lives in `src/app/router/routes.ts`. Authenticated pages render inside `src/app/layouts/MainLayout.vue`.

Path aliases in `vite.config.ts`:
- `@` → `./src`

### Backend shape

Modular by feature area under `server/app/`. Most domains follow the same pattern:
- `api.py` — FastAPI routes
- `service.py` — business logic / orchestration
- `schemas.py`, `request.py`, or `response.py` — DTOs

Key domains:
- `auth` — registration, login, token validation, current-user resolution
- `chat` — SSE tutor conversation, uploads, chat history, profile/school endpoints, memory integration
  - `chat/agent.py` — `run_tutor_agent` pure loop (model stream → tool dispatch → append messages)
  - `chat/hooks.py` — `ChatRunHooks` snapshot container + 1-slot notification queue
  - `chat/memory.py` — compression, long-term memory, token accounting
  - `chat/context.py`, `chat/tools.py`, `chat/files.py`, `chat/service.py`
- `resource` — standalone resource generation and event streaming
  - `resource/agent.py` — `run_resource_lead_agent` loop (mirrors `chat/agent.py`)
  - `resource/hooks.py` — `ResourceRunHooks` snapshot container
  - `resource/tools.py` — the 7 sub-agent tools invoked by the lead agent
  - `resource/agents/__init__.py` — stateless adapter used by the `path` domain
- `path` — learning-path planning, node workspace, quizzes, auxiliary node resources, path evaluation
  - `path/workflows.py` — LangGraph learn workflow
  - `path/service.py` — `PathService.run_generation()`, `PathPlannerAgent`
- `profile` — learner profile inference and retrieval
- `evaluation` — learning events and summaries
- `dashboard` — homepage aggregation and recommendations
- `quiz` — question bank and wrong-question APIs
- `shared/` — cross-domain modules: `tools/` (Tool/registry/sandbox/skills + builtin workspace tools), `ppt/`, `cartoon/`
- `infra` — database, models, logging, LLM singleton, UtcDateTime, JSON utils, seed data

Application startup is centered on `server/app/main.py`:
- `create_app()` configures CORS, exception handlers, and route installation
- `lifespan()` warms prompt templates, initializes the database, and runs health checks
- `server/app/routes.py` mounts all HTTP and WebSocket routers

## API boundaries that matter

Current route grouping (trust `server/app/routes.py` and each domain `api.py` over older docs):
- `/api/v1/users/*` — auth/user endpoints
- `/api/v1/ai/chat/*` — tutor chat run creation, sessions, history, uploads, SSE
- `/api/v1/ai/resource/*` — standalone resource generation, run snapshot, cancel, bundles, SSE
- `/api/v1/ai/resources` — standalone resource list
- `/api/v1/ai/path-plan*` — learning-path generation, latest/history, node workspace, node quizzes/resources, path events/evaluation
- `/api/v1/ai/dashboard/*` — homepage aggregation (recommendation, profile-radar, continue-learning, quick-actions, recent-resources)
- `/api/v1/ai/profile*`, `/api/v1/ai/schools/*`, `/api/v1/ai/evaluation/*`, `/api/v1/ai/quiz*`, `/api/v1/ai/wrong*` — supporting domains
- Cartoon/PPT are not separate HTTP surfaces: they are agent tools invoked from chat and resource

## Critical Runtime Flows

### Tutor chat flow

`server/app/chat/api.py` exposes `POST /api/v1/ai/chat/messages`, which returns a `run_id`; the client then opens `GET /api/v1/ai/chat/runs/{run_id}/events` via `EventSource`.
The runtime is orchestrated by `server/app/chat/service.py`:
- create a `ChatRun` and persist the user message plus attachments
- build context via `chat/context.py` and delegate answering to `run_tutor_agent` in `chat/agent.py`
- stream `run.state` snapshots back to the client through `ChatRunHooks`
- persist the final assistant reply
- run post-turn compression / long-term-memory checks

Chat context is assembled from multiple layers spanning chat, profile, and memory code:
- raw chat history
- compressed summary blocks (`ChatSessionSummaryBlock`)
- long-term memory (`ChatLongTermMemory`)
- learner profile (`GlobalProfile`, `CourseProfile`)
- optional web-search sources

This is the main personalization pipeline in the repo.

### Standalone resource generation flow

`server/app/resource/api.py` exposes the entrypoint at `POST /api/v1/ai/resource/generate`.

The runtime flow:
1. `prepare_resource_run()` persists a `GeneratedResource` record with status `pending`
2. the request is scheduled as a FastAPI background task
3. `execute_resource_run()` builds `ResourceRunHooks` and runs `run_resource_lead_agent`
4. the lead agent calls the sub-agent tools in `resource/tools.py` (lecture, mindmap, quiz, code, reading, PPT, cartoon)
5. artifacts are persisted as `GeneratedResourceItem` rows and the record reaches a terminal status
6. progress streams as full `RunState` snapshots over SSE from `/api/v1/ai/resource/runs/{run_id}/events`

The current architecture streams one `run.state` snapshot per change rather than per-event records; `ResourceRunHooks` owns the in-memory snapshot and a single-slot notification queue.

### Learning-path flow

The `path` domain is not just another view over standalone resources.
It owns its own API surface, background generation flow, and persistence models.
Typical flow:
1. `POST /api/v1/ai/path-plan` creates a path-generation task
2. background generation in `PathService.run_generation()` and `PathPlannerAgent` builds stages and nodes
3. `GET /api/v1/ai/path-plan/nodes/{node_id}/workspace` drives the node workspace
4. node learning uses the LangGraph learn workflow exposed by `server/app/path/workflows.py`
5. node resources are generated and stored as `PathNodeResource`
6. path learning events feed profile/evaluation updates

Path-node resources are stored and queried separately from standalone resource records. Preserve that boundary.

### Cartoon (teaching video) flow

One pipeline, invoked as the `generate_teaching_video` agent tool:

`shared/cartoon/tool.py` → `shared/cartoon/agent.py` → `node_modules/.bin/hyperframes`

- `CartoonAgent` is itself a tool-loop agent: it loads the `hyperframes` / `hyperframes-cli` / `media-use` skills on demand and drives the local HyperFrames CLI to render HTML scenes into `video.mp4`
- `shared/cartoon/tts.py` handles narration audio
- `shared/cartoon/schemas.py` defines the artifact contract (`CartoonArtifact`)
- Both `chat` and `resource` reach it through `build_cartoon_tool()`

PPT generation follows the same shape: `shared/ppt/tool.py` → `shared/ppt/agent.py` → `node deck.cjs` (PptxGenJS living in the project's `node_modules`).

### Profile and memory flow

The learner model is spread across chat, profile, and evaluation domains:
- chat turns/messages are persisted in `ChatSession`, `ChatTurn`, and `ChatMessage`
- compressed history is stored in `ChatSessionSummaryBlock`
- reusable long-term facts are stored in `ChatLongTermMemory`
- learner profiles live in `GlobalProfile` and `CourseProfile`
- learning events and learning sessions feed back into profile/evaluation updates

When changing personalization behavior, inspect `chat`, `profile`, and `evaluation` together rather than treating them as isolated modules.

## Persistence, Config, and Conventions

### Configuration

Backend runtime configuration comes from `server/config.yaml`, not `.env`.
Important groups: `app`, `database`, `jwt`, `models` (incl. `models.vision`), `search`, `paths`, `knowledge`, `memory`, `chat`, `evaluation`, `paths_config`, `resource`, `quiz`, `video`.

### Database and schema source of truth

The backend uses MySQL via `aiomysql`.

`server/app/infra/models.py` is the single source of truth for schema. `init_db()` runs
`SQLModel.metadata.create_all` at startup, which creates missing tables but **never alters
existing ones** — after changing a column type or length, drop and recreate the database.

MySQL-specific conventions:
- Time columns use `UtcDateTime` (`server/app/infra/types.py`): stored as UTC `DATETIME(6)`,
  read back as aware UTC, so Python-side arithmetic and comparisons keep working.
- JSON columns use `sqlalchemy.JSON` and are not indexed — MySQL only indexes JSON through
  generated columns on a JSON path.
- UUID primary keys are `String(36)` holding the standard hyphenated uuid string.
- `pool_pre_ping` is intentionally off: SQLAlchemy 2.0.49's pymysql dialect calls `ping()`
  without arguments on PyMySQL >= 1.1, while aiomysql's async adapter requires the
  `reconnect` argument. `pool_recycle` handles stale connections instead.

### Session and auth conventions

Database session usage is intentionally split:
- `get_session()` — FastAPI dependency injection for request handlers
- `session_scope()` — background tasks / manual async context manager with commit/rollback handling

Auth resolution does no DB I/O: `JWTMiddleware` decodes the JWT and stores `UserClaims` in `current_user_ctx`; `get_current_user()` reads that ContextVar. SSE endpoints accept `?token=` because `EventSource` cannot set headers.

### Shared backend conventions

- API responses use the `HttpResponse` envelope: `{code, message, data}`.
- Auth is JWT-based and additionally checked against the `ActiveToken` whitelist table.
- Prompt loading is centralized and warmed during app startup.
- LLM access through `get_llm()` singleton in `server/app/infra/llm.py`, uses OpenAI-compatible API.
- Chat uploads and generated working files live under paths derived from `server/config.yaml`.
- Python code: 4-space indent, type hints, snake_case modules, Google Python Style Guide.
- Frontend `.vue` files: `<script setup lang="ts">` only, no Options API.

### Frontend conventions

- Vue SFCs use `<script setup lang="ts">`.
- Components and views are split by feature domain instead of a global component hierarchy.
- Follow the existing local patterns in nearby files.

## Files worth reading first

1. `README.md`
2. `server/README.md`
3. `src/app/router/routes.ts`
4. `server/app/main.py`
5. `server/app/routes.py`
6. `server/app/chat/service.py`
7. `server/app/resource/api.py`
8. `server/app/resource/agent.py`
9. `server/app/path/api.py`
10. `server/app/path/service.py`
11. `server/app/infra/models.py`
12. `server/app/infra/types.py`
