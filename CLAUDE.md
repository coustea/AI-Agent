# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent personalized learning resource platform (多智能体个性化学习资源平台). Full-stack monorepo: Vue 3 + TypeScript frontend (`src/`) and FastAPI + SQLModel backend (`server/`).

## Commands

### Backend (from `server/` directory)

```bash
uv sync                                    # Install dependencies
uv run fastapi dev app/main.py             # Dev server with auto-reload (port 9999)
uv run python app/main.py                  # Production server (reads config.yaml)
uv run pytest                              # Run tests
uv run pytest tests/modules/user/test_auth.py  # Run a single test file
uv run pytest -x                           # Stop on first failure
```

API docs at `http://localhost:9999/docs` when running.

### Frontend (from project root)

```bash
npm run dev        # Dev server at http://localhost:5173
npm run build      # Production build (runs vue-tsc type check first)
npm run preview    # Preview production build
```

No linter is configured for either frontend or backend.

## Architecture

### Backend (`server/app/`)

Feature modules are top-level directories, each self-contained:

```
auth/          # Authentication & user management
chat/          # AI tutor conversation (SSE streaming)
resource/      # Multi-agent resource generation
memory/        # Memory system facade (short-term, long-term, profile)
evaluation/    # Learning assessment & events
path/          # Course-level learning path planning
avatar/        # Digital human (讯飞) WebSocket bridge
infra/         # Shared infrastructure (DB, LLM, response, models, logging)
```

Each module follows a consistent file pattern:
- `api.py` — FastAPI endpoints + dependency injection
- `service.py` — Business logic + runtime orchestration
- `schemas.py` or `request.py`/`response.py` — Pydantic DTOs
- Module-specific files: `agent.py`, `tools/`, `agents/`, `bridge/`, etc.

**Infra layer** (`infra/`):
- `database.py` — PostgreSQL async engine via asyncpg, `init_db()` with retry logic. `DEBUG=true` drops all public-schema tables then recreates. Provides `get_session()` (DI) and `session_scope()` (explicit).
- `models.py` — All SQLModel table classes centralized here. Tables auto-created on startup (no migration tool). New tables must be added to `REGISTERED_MODELS` tuple.
- `llm.py` — `Llm` singleton wrapping `ChatOpenAI`. Provides `ainvoke()`, `astream()`, `ainvoke_json(schema, ...)`, `vision()`. Concurrency controlled by Semaphore per model. `ainvoke_json` uses 3-tier fallback: function calling → `response_format: json_object` → plain text + JSON parse.
- `response.py` — `HttpResponse` envelope `{code, message, data}` with `.success()` and `.error()` factory methods.
- `security.py` — JWT auth + bcrypt hashing. `AuthError` exception class. `get_current_user` dependency validates JWT + checks `ActiveToken` DB whitelist.
- `config.py` — Loads `config.yaml` with nested-path access via `get("path.to.key")`. All settings are module-level constants.
- `logging.py` — `get_logger()` facade (loguru-based).

**Database tables** (`infra/models.py`): PostgreSQL with JSONB columns. Key tables:
- `User` — Auto-increment int PK, `is_first_login` flag
- `ActiveToken` — JWT whitelist (DB-based, not Redis)
- `ChatSession` — UUID string PK, per-user multi-session, `attachment_analyses` JSONB, token-count triggers
- `ChatMessage` — Raw conversation with `tool_calls`, `attachments`, `teaching_diagram` JSONB
- `ChatSessionSummary` — Compressed context summaries (incremental/full)
- `UserLongTermMemory` — One row per user+module, `memory_markdown` as authoritative source
- `UserProfile` / `UserProfileHistory` — 8-dimension profile with JSONB + versioning
- `GeneratedResource` / `GeneratedResourceItem` — Resource generation records with agent outputs
- `LearningEvent` — Assessment events tracking
- `CoursePath` / `CoursePathNode` / `CoursePathResourceBinding` — Path planning structure
- `CoursePathGenerationTask` — Slow generation progress tracking
- `School` — Imported school data

### Multi-Agent System

Built on LangGraph (StateGraph pattern, not raw LangChain chains):

**TutorAgent** (`chat/agent.py`) — LangGraph StateGraph with nodes: `classify` → `decide_learner_context` → `direct_answer` / `search_node` / `spark_summary` / `attachment_answer` / `teaching_diagram_generate`. Streams via SSE. Reads 3-layer context (profile, long-term memory, chat history). Uses `runtime_context` ContextVar for user session injection. Tools: `learner_context`, `search` (DuckDuckGo/SerpAPI/Tavily).

**Resource Generation** (`resource/service.py`) — Two flat orchestration functions in service layer:
- `bg_gen_task()` — Multi-agent mode: PlanningAgent → parallel Worker Agents → ReviewAgent → save. PlanningAgent generates blueprint + per-agent instructions, workers run concurrently via `asyncio.gather`, ReviewAgent validates.
- `bg_single_gen_task()` — Single-agent mode: direct `AGENT_REGISTRY[agent_id].run(state)` with only `learning_need` + `profile`. Used by path planning and on-demand generation. No Planning/Review overhead.

**Resource Agents** (`resource/agents/`): `planning`, `content`, `mindmap`, `quiz`, `code`, `reading`, `ppt`, `review`. Each inherits `BaseResourceAgent` and is registered via `@register_agent` decorator into `AGENT_REGISTRY`. Every agent can run independently — `blueprint`/`instruction` in `WorkerState` are Optional (None = single-agent mode, present = multi-agent mode). `AgentEventEmitter` handles SSE progress streaming.

**MemoryService** (`memory/service.py`) — Facade delegating to sub-services:
- `MemoryStore` (`store.py`) — DB CRUD for sessions, messages, summaries, long-term memory, profiles
- `SessionCompressor` (`compression.py`) — Short-term → summary compression
- `LongTermMemoryExtractor` (`long_term.py`) — Fact extraction into `UserLongTermMemory`
- `ProfileBuilder` (`profile.py`) — 8-dimension profile from memory + events

Triggered at token-count thresholds on `ChatSession`.

**Path Planner** (`path/`) — `planner.py` agent for course-level learning path generation with progress tracking via `CoursePathGenerationTask`. Node resource generation uses `bg_single_gen_task()` (single-agent mode) instead of the full multi-agent pipeline.

**Avatar Bridge** (`avatar/`) — `RealtimeBridge` manages WebSocket connections for 讯飞 digital-human. ASR (speech recognition) → avatar playback. Separate from tutoring logic.

### API Routes

All routes mounted in `main.py` under `/api/v1/`:

| Prefix | Module | Key Endpoints |
|--------|--------|---------------|
| `/api/v1/users` | auth | `POST /` register, `POST /auth` login, `DELETE /auth` logout, `GET /me`, `PATCH /me` |
| `/api/v1/ai` | chat | `POST /chat/stream` (SSE), `POST /chat/upload`, session CRUD, history |
| `/api/v1/ai` | resource | `POST /generate` (SSE), `POST /generate/single`, `GET /agents`, `GET /resources` |
| `/api/v1/ai` | path | Path planning endpoints |
| `/api/v1/ai` | evaluation | Assessment endpoints |
| `/api/v1/ai` | avatar | Digital-human WebSocket bridge |

### Auth Flow

- Login returns JWT token; frontend stores in `localStorage`
- `get_current_user` dependency validates JWT + checks `ActiveToken` DB table whitelist
- Logout removes token from whitelist + triggers background profile build
- `AuthError` exception caught by global handler → `HttpResponse.error(code=401)`

### Frontend (`src/`)

Vue 3 Composition API (`<script setup lang="ts">`). Libraries: Element Plus, ECharts, Marked, Axios, markdown-it, mermaid, markmap-lib.

Protected routes under `MainLayout`: dashboard, resource-generator, path-planner, tutor, evaluation, profile, resource-detail, question-bank. Public: login, register, onboarding.

Vite dev server proxies `/api` → `http://localhost:9999` and `/ws` → `ws://localhost:9999`.

Composables: `useGlobalProfile`, `useLearningTracker`. Components: chat, common, resource, ppt-engine, `TutorMessageContent`, `GlobalProfileDialog`, `OnboardingDialog`.

## Configuration

Config loaded from `server/config.yaml` (not `.env`). Structure:

```yaml
app:          # host, port, debug
database:     # url (postgresql+asyncpg://...), pool settings
jwt:          # secret_key, algorithm, expire_days
models:       # base_url, api_key, model_name, concurrency; vision sub-config
avatar:       # 讯飞 digital-human WebSocket config
search:       # tavily_key
paths:        # workplace, logs, knowledge dirs
memory:       # profile_gate_turns, msg_limit, budgets
chat:         # file content limits, upload limits
```

`DEBUG=true` drops all tables on startup — only use in development.

## Vue 3 Frontend Code Style

All `.vue` files must follow the conventions in `docs/vue-code-style.md`. Key rules:
- Use `<script setup lang="ts">` only, no Options API
- Strict internal ordering: imports → defineProps/defineEmits → defineModel → composables → ref/reactive → computed → constants → watch → lifecycle hooks → functions
- Must use `<style scoped>`, respect `prefers-reduced-motion`
- Never destructure `props` or `reactive` objects

## Key Conventions

- All API responses use `HttpResponse` envelope (`{code, message, data}`)
- Error responses use `HttpResponse.error()` with appropriate HTTP status codes (not `HTTPException`) except for auth failures which raise `AuthError` caught by global handler
- Backend modules are self-contained with their own api/service/schemas layers
- Python managed with `uv`; frontend managed with `npm`
- Agent prompt templates loaded via `app.prompts.registry` or stored as `.md` files in module directories
- Module-level singleton pattern for services and agents
- LLM config uses OpenAI-compatible API (`base_url` in config.yaml)
- Database is PostgreSQL (asyncpg), not MySQL
- `config.yaml` is the single config source (not `.env`)
- New SQLModel tables must be added to `REGISTERED_MODELS` in `infra/models.py`
- Python code must follow Google Python Style Guide (see `server/docs/google_python_style_guide.md`)