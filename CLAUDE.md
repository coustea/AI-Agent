# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent personalized learning platform (多智能体个性化学习资源平台). This is a full-stack monorepo:
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
npm run build
npm run preview
```

Notes:
- `npm run build` runs `vue-tsc -b && vite build` and is the main frontend validation path.
- There is no committed frontend lint or test script.
- `vite.config.ts` proxies `/api` and `/ws` to `http://127.0.0.1:9999` by default, overridable with `VITE_API_PROXY_TARGET` and `VITE_WS_PROXY_TARGET`.

### Backend (run from `server/`)

```bash
uv sync
uv run fastapi dev app/main.py
uv run python app/main.py
uv run pytest
uv run pytest tests/chat/test_history.py -q
uv run pytest tests/dashboard/test_home_api.py -q
uv run pytest tests/chat/test_history.py -q -k summary
uv run pytest -x
```

Notes:
- Backend requires Python `>=3.13`.
- FastAPI docs are served at `/docs` on the configured backend port.
- `pytest` is the main backend verification path.
- `vulture` is installed in the dev dependency group, but no project-standard lint command is configured.

## High-Level Architecture

### Frontend shape

The frontend is organized by app shell + feature domains rather than a flat component tree:
- `src/app/` — router, layouts, app-level wiring
- `src/features/` — feature domains such as `auth`, `chat`, `dashboard`, `learning-path`, `profile`, `question-bank`, `resource`
- `src/shared/` — shared API clients, auth helpers, UI, types, utilities

Routing lives in `src/app/router/routes.ts`. Authenticated pages render inside `src/app/layouts/MainLayout.vue`. Main user-facing surfaces include dashboard, tutor, standalone resource generation/history/detail, learning-path entry/overview/node/history, path-resource history/detail, profile, and question bank.

### Backend shape

The backend is modular by feature area under `server/app/`. Most domains follow the same pattern:
- `api.py` — FastAPI routes
- `service.py` — business logic / orchestration
- `schemas.py`, `request.py`, or `response.py` — DTOs

Key domains:
- `auth` — registration, login, token validation, current-user resolution
- `chat` — SSE tutor conversation, uploads, chat history, profile/school endpoints, memory integration
- `resource` — standalone resource generation and event streaming
- `path` — learning-path planning, node workspace, quizzes, auxiliary node resources, path evaluation
- `profile` — learner profile inference and retrieval
- `evaluation` — learning events and summaries
- `dashboard` — homepage aggregation and recommendations
- `quiz` — question bank and wrong-question APIs
- `avatar` — digital-human REST endpoints and WebSocket bridge
- `infra` — database, models, logging, prompts, config, response envelope

Application startup is centered on `server/app/main.py`:
- `create_app()` configures CORS, exception handlers, and route installation
- `lifespan()` warms prompt templates, initializes the database, and runs health checks
- `server/app/routes.py` mounts all HTTP and WebSocket routers

## API boundaries that matter

Current route grouping is:
- `/api/v1/users/*` — auth/user endpoints
- `/api/v1/ai/chat/*` — tutor chat stream, uploads, sessions, profile/school helpers
- `/api/v1/ai/resources*` — standalone resource generation, status, detail, history, agents, SSE
- `/api/v1/ai/path-plan*` — learning-path generation, active/history views, node workspace, node quizzes/resources, path events/evaluation
- `/api/v1/ai/dashboard*`, `/api/v1/ai/evaluation*`, `/api/v1/ai/quiz-bank*`, `/api/v1/ai/wrong-questions*`, `/api/v1/ai/avatar*` — supporting domains
- `/ws/avatar` — avatar WebSocket bridge authenticated by `?token=...`

When wiring frontend/backend changes, trust `server/app/routes.py` and each domain `api.py` over older docs that refer to `/resource` vs `/resources` or `/path` shorthand.

## Critical Runtime Flows

### Tutor chat flow

`server/app/chat/routers/chat_router.py` exposes the SSE entrypoint at `POST /api/v1/ai/chat/stream`.
The runtime is orchestrated by `server/app/chat/service.py`:
- create a `ChatTurn`
- persist the user message and attachments
- build context and delegate answering to `TutorAgent`
- stream SSE events back to the client
- persist the final assistant reply
- run post-turn compression / long-term-memory checks

Chat context is assembled from multiple layers spanning chat, profile, and memory code:
- raw chat history
- compressed summary blocks (`ChatSessionSummaryBlock`)
- long-term memory (`ChatLongTermMemory`)
- learner profile (`GlobalProfile`, `CourseProfile`)
- optional web-search / knowledge-base sources

This is the main personalization pipeline in the repo.

### Standalone resource generation flow

`server/app/resource/api.py` and `server/app/resource/orchestrator.py` implement two request modes:
- `POST /api/v1/ai/resources` — creates a background standalone resource task
- `POST /api/v1/ai/resources/single` — creates a single-agent task through the same background orchestration entrypoint

The runtime flow is:
1. persist a `GeneratedResource` task record
2. start a background job
3. mark the resource as `generating`
4. run the LangGraph parent workflow from `server/app/resource/workflow/`
5. persist `GeneratedResourceItem` rows and final status
6. stream progress via SSE from `/api/v1/ai/resources/{id}/events`

Agent implementations live in `server/app/resource/agents/` and are coordinated through the resource workflow/orchestrator layer.

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
Important groups include:
- `app` — host/port/debug
- `database`
- `jwt`
- `models` and `models.vision`
- `spark`
- `avatar`
- `search`
- `paths`
- `knowledge`
- `memory`
- `chat`
- `evaluation`
- `paths_config`
- `resource`
- `quiz`
- `asr`

### Database and schema source of truth

The backend uses PostgreSQL via `asyncpg`.

Two files matter whenever schema changes are involved:
- `server/init_schema.sql` — operational schema/bootstrap SQL
- `server/app/infra/models.py` — SQLModel definitions used by application code

Keep them in sync. Startup does not reconcile schema drift for you.
New tables also need to be added to `REGISTERED_MODELS` in `server/app/infra/models.py` so `init_db()` can create them.

### Session and auth conventions

Database session usage is intentionally split:
- `get_session()` — FastAPI dependency injection for request handlers
- `session_scope()` — background tasks / manual async context manager with commit/rollback handling

Auth resolution in `server/app/auth/security.py` depends on the request-scoped `AsyncSession` from `get_session()`. Avoid swapping auth dependencies over to `session_scope()`.

### Shared backend conventions

- API responses use the `HttpResponse` envelope: `{code, message, data}`.
- Auth is JWT-based and additionally checked against the `ActiveToken` whitelist table.
- Prompt loading is centralized and warmed during app startup.
- Chat uploads and generated working files live under paths derived from `server/config.yaml`.

## Frontend conventions reflected in the repo

- Vue SFCs use `<script setup lang="ts">`.
- Components and views are split by feature domain instead of a global component hierarchy.
- There is no committed standalone frontend rule file to trust more than the code itself, so follow the existing local patterns in nearby files.

## Files worth reading first

For quick orientation, start here:
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
12. `server/init_schema.sql`
