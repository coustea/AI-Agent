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
- `npm run build` runs `vue-tsc -b && vite build`.
- There is no committed frontend lint or test script; use `npm run build` as the main automated frontend check.
- `vite.config.ts` currently proxies `/api` and `/ws` to `http://127.0.0.1:9000`, but `server/config.yaml` defaults the backend to port `9999`. If you run both apps together, update one side or start the backend on the port the frontend expects.

### Backend (run from `server/`)

```bash
uv sync
uv run fastapi dev app/main.py
uv run python app/main.py
uv run pytest
uv run pytest tests/chat/test_history.py -q
uv run pytest -x
```

Notes:
- FastAPI docs are served at `/docs` on the configured backend port.
- `pytest` is the main backend verification path.
- `vulture` is installed in the dev dependency group, but no project-standard lint command is configured.

## High-Level Architecture

### Frontend shape

The frontend is organized by app shell + feature domains rather than a flat component tree:
- `src/app/` — router, guards, layouts
- `src/features/` — domain features (`auth`, `chat`, `dashboard`, `learning`, `profile`, `resource`)
- `src/shared/` — shared API clients, auth helpers, UI, types, utilities

Routing lives in `src/app/router/routes.ts`. Protected pages are rendered inside `src/app/layouts/MainLayout.vue`. The main user-facing surfaces are dashboard, tutor, standalone resource generation/history, learning-path planning/overview/node learning, profile, question bank, and wrong-question review.

### Backend shape

The backend is modular by feature area under `server/app/`. Most domains follow the same pattern:
- `api.py` — FastAPI routes
- `service.py` — business logic / orchestration
- `schemas.py` or `request.py` / `response.py` — DTOs

Key domains:
- `auth` — registration, login, token validation, user info
- `chat` — streaming tutor conversation, uploads, chat history, diagram generation
- `resource` — standalone multi-agent resource generation
- `path` — learning-path planning, node workspace, node questions/resources, path evaluation
- `profile` — learner profile inference and storage
- `evaluation` — learning events and derived signals
- `dashboard` — homepage aggregation
- `quiz` — question-bank and wrong-question APIs
- `avatar` — digital-human / websocket-related flows
- `infra` — database, models, logging, prompts, LLM client, response envelope

Application startup is split across:
- `server/app/app_factory.py` — create FastAPI app, CORS, exception handlers, route installation
- `server/app/lifecycle.py` — warm prompts, initialize DB-related startup work, run health checks
- `server/app/routes.py` — mounts feature routers under `/api/v1/...`

### API boundaries that matter

Current route grouping is:
- `/api/v1/users` — auth/user endpoints
- `/api/v1/ai/chat/*` — tutor chat, uploads, session/history endpoints
- `/api/v1/ai/resources*` — standalone resource generation/history/detail/SSE
- `/api/v1/ai/path-plan*` — learning-path generation, node workspace, node resources, path events/evaluation
- `/api/v1/ai/dashboard*`, `/evaluation*`, `/quiz*`, `/wrong-*`, `/avatar*` — supporting domains

When wiring frontend/backend changes, use the real mounted prefixes above rather than older docs that refer to `/generate` or `/path` shorthand.

## Critical Runtime Flows

### Tutor chat flow

`server/app/chat/api.py` exposes the SSE entrypoint at `POST /api/v1/ai/chat/stream`.
The tutoring runtime is centered on `server/app/chat/agent.py`, which builds a LangGraph workflow roughly shaped as:
- `classify`
- optional `attachment_analysis`
- optional `search`
- `answer`
- optional `teaching_diagram_generate`

The chat system composes context from multiple sources:
- raw chat history
- compressed summary blocks
- long-term memory
- learner profile
- optional knowledge-base and web-search results

This is the main personalization pipeline in the repo.

### Standalone resource generation flow

`server/app/resource/api.py` and `server/app/resource/service.py` implement two distinct execution modes:
- `POST /api/v1/ai/resources` — creates a background multi-agent task
- `POST /api/v1/ai/resources/single` — runs a single selected agent without the full planning/review pipeline

The multi-agent flow is:
1. persist a `GeneratedResource` task record
2. build a plan / blueprint
3. run worker agents in parallel
4. review aggregated output
5. persist `GeneratedResourceItem` rows and final status
6. stream progress via SSE events

Agent implementations live in `server/app/resource/agents/` and are registered into a shared registry.

### Learning-path flow

The `path` domain is not just another view over standalone resources.
It owns its own API surface, background generation flow, and persistence models.
Typical flow:
1. `POST /api/v1/ai/path-plan` creates a path-generation task
2. background generation fills path, nodes, and related records
3. node workspace endpoints drive tutorial/questions/resources inside the path context
4. path learning events feed profile/evaluation updates

Path-node resources are stored and queried separately from standalone resource records. Preserve that boundary.

### Profile and memory flow

The learner model is spread across chat, profile, and evaluation domains:
- chat turns/messages are persisted in `ChatSession`, `ChatTurn`, and `ChatMessage`
- compressed history is stored in `ChatSessionSummaryBlock`
- reusable long-term facts are stored in `ChatLongTermMemory`
- learner profiles live in `GlobalProfile` and `CourseProfile`
- learning events feed back into profile/evaluation updates

When changing personalization behavior, inspect `chat`, `profile`, and `evaluation` together rather than treating them as isolated modules.

## Persistence, Config, and Conventions

### Configuration

Backend runtime configuration comes from `server/config.yaml`, not `.env`.
Important families include:
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

### Database and schema source of truth

The backend uses PostgreSQL via `asyncpg`.

Two files matter whenever schema changes are involved:
- `server/init_schema.sql` — operational schema/bootstrap SQL
- `server/app/infra/models.py` — SQLModel definitions used by application code

Keep them in sync. Do **not** assume startup will reconcile schema drift for you.

### Shared backend conventions

- API responses use the `HttpResponse` envelope: `{code, message, data}`.
- Auth is JWT-based and additionally checked against the `ActiveToken` whitelist table.
- Prompt loading is centralized through `app.infra.prompts`.
- Chat uploads and generated working files live under directories derived from `server/config.yaml` paths (typically `server/workplace/`).

## Frontend code style

Vue files must follow `docs/vue-code-style.md`:
- use `<script setup lang="ts">`
- use `<style scoped>`
- keep the required ordering inside `<script setup>`
- do not destructure `props` or `reactive()` state directly

## Files worth reading first

For quick orientation, start here:
1. `README.md`
2. `server/README.md`
3. `src/app/router/routes.ts`
4. `server/app/app_factory.py`
5. `server/app/routes.py`
6. `server/app/chat/agent.py`
7. `server/app/resource/service.py`
8. `server/app/path/api.py`
9. `server/app/infra/models.py`
10. `server/init_schema.sql`
