# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent personalized learning platform (多智能体个性化学习资源平台). Full-stack monorepo with three workspaces:
- `src/` — Vue 3 + TypeScript frontend
- `server/` — FastAPI + SQLModel backend
- `video-render/` — Remotion 4.0 video rendering project (Node.js, must `npm install` separately)

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

- No committed frontend lint or test script.
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
- Known pre-existing failure: `tests/chat/test_reasoning_agent.py` — `FakeLlm` lacks `astream`. Don't waste time debugging.

### Video render (run from `video-render/`)

```bash
npm install
npx remotion --version   # verify Remotion 4.0.478
```

## High-Level Architecture

### Frontend shape

Organized by app shell + feature domains:
- `src/app/` — router, layouts, app-level wiring
- `src/features/` — `auth`, `chat`, `dashboard`, `learning-path`, `profile`, `question-bank`, `resource`
- `src/shared/` — `api`, `auth`, `content`, `markdown`, `model`, `styles`, `ui`

Routing lives in `src/app/router/routes.ts`. Authenticated pages render inside `src/app/layouts/MainLayout.vue`.

Path aliases in `vite.config.ts`:
- `@` → `./src`
- `@ppt-manifest` → `./server/app/resource/templates/ppt_manifest.json`

### Backend shape

Modular by feature area under `server/app/`. Most domains follow the same pattern:
- `api.py` — FastAPI routes
- `service.py` — business logic / orchestration
- `schemas.py`, `request.py`, or `response.py` — DTOs

Key domains:
- `auth` — registration, login, token validation, current-user resolution
- `chat` — SSE tutor conversation, uploads, chat history, profile/school endpoints, memory integration
  - `chat/agent/` — TutorAgent LangGraph graph (`nodes.py`, `state.py`, `tools.py`, `background.py`)
  - `chat/memory/` — `compression.py`, `long_term.py`, `service.py`
  - `chat/storage/`, `chat/tools/`, `chat/streaming.py`, `chat/context_builder.py`
- `resource` — standalone resource generation and event streaming
  - `resource/agents/` — `base.py`, `planning`, `content`, `mindmap`, `quiz`, `code`, `reading`, `ppt`, `video`, `cartoon`, `review` (each inherits `BaseResourceAgent`, registered via `@register_agent`)
  - `resource/workflow/` — LangGraph parent workflow
  - `resource/orchestrator.py` — background job orchestration
- `path` — learning-path planning, node workspace, quizzes, auxiliary node resources, path evaluation
  - `path/workflows.py` — LangGraph learn workflow
  - `path/service.py` — `PathService.run_generation()`, `PathPlannerAgent`
- `profile` — learner profile inference and retrieval
- `evaluation` — learning events and summaries
- `dashboard` — homepage aggregation and recommendations
- `quiz` — question bank and wrong-question APIs
- `shared/` — cross-domain modules: `video/`, `cartoon/`, `ppt/`, `research/`, `utils/`
- `infra` — database, models, logging, prompts, config, response envelope, LLM singleton

Application startup is centered on `server/app/main.py`:
- `create_app()` configures CORS, exception handlers, and route installation
- `lifespan()` warms prompt templates, initializes the database, and runs health checks
- `server/app/routes.py` mounts all HTTP and WebSocket routers

## API boundaries that matter

Current route grouping (trust `server/app/routes.py` and each domain `api.py` over older docs):
- `/api/v1/users/*` — auth/user endpoints
- `/api/v1/ai/chat/*` — tutor chat stream, uploads, sessions, profile/school helpers
- `/api/v1/ai/resources*` — standalone resource generation, status, detail, history, agents, SSE
- `/api/v1/ai/path-plan*` — learning-path generation, active/history views, node workspace, node quizzes/resources, path events/evaluation
- `/api/v1/ai/cartoon/*` — cartoon video generation
- `/api/v1/ai/dashboard*`, `/api/v1/ai/evaluation*`, `/api/v1/ai/quiz-bank*`, `/api/v1/ai/wrong-questions*` — supporting domains

## Critical Runtime Flows

### Tutor chat flow

`server/app/chat/api.py` exposes the SSE entrypoint at `POST /api/v1/ai/chat/stream`.
The runtime is orchestrated by `server/app/chat/service.py`:
- create a `ChatTurn`
- persist the user message and attachments
- build context via `context_builder.py` and delegate answering to `TutorAgent`
- stream SSE events back to the client
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

`server/app/resource/api.py` and `server/app/resource/orchestrator.py` implement two request modes:
- `POST /api/v1/ai/resources` — creates a background multi-agent resource task
- `POST /api/v1/ai/resources/single` — creates a single-agent task through the same orchestration

The runtime flow:
1. persist a `GeneratedResource` task record
2. start a background job
3. mark the resource as `generating`
4. run the LangGraph parent workflow from `server/app/resource/workflow/`
5. persist `GeneratedResourceItem` rows and final status
6. stream progress via SSE from `/api/v1/ai/resources/{id}/events`

Agent implementations live in `server/app/resource/agents/` and are coordinated through the resource workflow/orchestrator layer. Registered agents: `planning`, `content`, `mindmap`, `quiz`, `code`, `reading`, `ppt`, `video`, `cartoon`, `review`.

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

### Video rendering flow

Two independent pipelines, both require FFmpeg:

1. **Remotion lecture videos** — `resource/agents/video.py` → `shared/video/agent.py` → `shared/video/renderer.py` → `video-render/` (npx tsx scripts/render.ts)
   - Pipeline: `VideoMaterialAgent` → `VideoDirectorAgent` → `SceneWriterAgent` → `VideoTtsService` → `RemotionVideoRenderer`
   - Config: `config.yaml` → `video` section

2. **HyperFrames cartoon videos** — `resource/agents/cartoon.py` → `shared/cartoon/pipeline.py` → `shared/cartoon/renderer.py` → `npx hyperframes render`
   - Auto-detects CPU cores, memory, NVIDIA GPU (Linux only)
   - Low-memory mode (≤8GB) degrades to single-worker CPU rendering

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
Important groups: `app`, `database`, `jwt`, `models` (incl. `models.vision`), `spark`, `search`, `paths`, `knowledge`, `memory`, `chat`, `evaluation`, `paths_config`, `resource`, `quiz`, `video`.

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

Auth resolution in `server/app/auth/security.py` depends on the request-scoped `AsyncSession` from `get_session()`. Avoid swapping auth dependencies over to `session_scope()`.

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
8. `server/app/resource/orchestrator.py`
9. `server/app/path/api.py`
10. `server/app/path/service.py`
11. `server/app/infra/models.py`
12. `server/app/infra/types.py`
