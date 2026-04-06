# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent personalized learning resource platform (多智能体个性化学习资源平台). Full-stack monorepo: Vue 3 + TypeScript frontend (`src/`) and FastAPI + SQLModel backend (`server/`).

## Commands

### Backend (from `server/` directory)

```bash
uv sync                                    # Install dependencies
uv run fastapi dev app/main.py             # Dev server with auto-reload (port 9999)
uv run python app/main.py                  # Production server (reads .env for host/port)
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

Feature modules follow a layered pattern:

```
modules/<module>/
  router.py       # FastAPI endpoints
  schemas.py      # Pydantic request/response models
  service.py      # Business logic
  repository.py   # SQLModel data access (optional, some modules skip this)
```

**Core infrastructure** (`core/`):
- `engine.py` — MySQL engine via PyMySQL, `init_db()` auto-creates all tables (no migration tool)
- `security.py` — JWT via PyJWT, bcrypt password hashing, `get_current_user` dependency. Token whitelist in `ActiveToken` DB table (not Redis)
- `response.py` — `HttpResponse` envelope: `{code, message, data}` with `.success()` and `.error()` factory methods
- `dependencies.py` — `get_session` yields a SQLModel `Session`
- `logging.py` — File-based logging with rotation

**Models** (`models/`): SQLModel table classes with auto-increment integer PKs (not UUIDs). Key models:
- `user.py` — `User` with profile fields
- `common.py` — `ActiveToken` (JWT whitelist), `ChatMessage` (short-term memory), `UserMemory` (long-term memory)
- `profile_builder.py` — `UserProfile` (8-dimension learning profile, keyed by user_id), `UserProfileHistory` (versioned snapshots)

### Multi-Agent System

The platform uses LangChain (not raw LangGraph) for agent orchestration:

**ChatAgent** (`profile_builder/chat_agent.py`) — Interactive learning tutor that streams responses via SSE. Reads 3-layer context (user profile, long-term memories, recent chat history) and builds the system prompt dynamically. Saves both user and assistant messages to short-term memory.

**ProfileBuilderAgent** (`profile_builder/profile_agent.py`) — Background agent that merges new conversation insights into the user's structured learning profile. Uses `with_structured_output(ProfileExtraction)` to enforce JSON schema. Triggered at message thresholds (3rd message for new users, then every 20 messages) and on logout.

**MindmapGenerator** (`resource_generator/mindmap_agent.py`) — Generates knowledge mindmaps: LLM produces markdown → MCP markmap service converts to interactive HTML.

**TutorAgent** (`tutor/agent.py`) — Minimal placeholder.

**MemoryService** (`memory/service.py`) — Central singleton managing all agent state:
- Short-term: `ChatMessage` table (raw conversation)
- Long-term: `UserMemory` table (LLM-summarized facts)
- Profile: `UserProfile` table (8-dimension structured profile) with versioned `UserProfileHistory`
- All agents share this service; it manages its own DB sessions internally (no external Session injection)

### MCP Integration

`MCPManager` singleton (`utils/mcp_manager.py`) manages external MCP tool services. Config loaded from `mcp/settings.json`. Supports variable substitution (`${SERVER_DIR}`, `${MCP_DIR}`, etc.) in config values. Agents call `mcp_manager.call_tool()` or get LangChain-compatible tools via `mcp_manager.get_tools()`.

Current MCP services: `markmap` — converts markdown to interactive mindmap HTML files, output to `server/workplace/mindmap/`.

### API Routes

All routes mounted in `main.py` under `/api/v1/`:

| Prefix | Module | Key Endpoints |
|--------|--------|---------------|
| `/api/v1/users` | user | `POST /` register, `POST /auth` login, `DELETE /auth` logout, `GET /me`, `PATCH /me` |
| `/api/v1/ai` | profile_builder | `POST /chat/stream` (SSE), `GET /profile`, `GET /profile/history`, `GET /chat/history` |

### Auth Flow

- Login returns JWT token; frontend stores in `localStorage`
- `get_current_user` dependency validates JWT + checks `ActiveToken` DB table whitelist
- Logout removes token from whitelist + triggers background profile build

### Frontend (`src/`)

Vue 3 Composition API (`<script setup lang="ts">`). Libraries: Element Plus, ECharts, Marked, Axios.

- `router/index.ts` — Public routes (`/login`, `/register`) and protected routes under `MainLayout`. Route guard checks `localStorage.token`.
- `api/auth.ts` — Auth API calls
- `api/ai.ts` — Profile assistant API calls (profile, history, chat)
- `utils/http.ts` — Axios instance with interceptors
- `views/` — Home, Login, Register, ProfileAssistant, ResourceGenerator, PathPlanner, Tutor, Evaluation

Vite dev server proxies `/api` to `http://localhost:9999` (matching backend port).

## Environment Variables

`.env` file is in `server/` directory:

```
SERVER_HOST=0.0.0.0
SERVER_PORT=9999

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=agent
DB_ECHO=false

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_BASE=https://your-endpoint
```

## Key Conventions

- All API responses use `HttpResponse` envelope (`{code, message, data}`)
- Error responses use `HttpResponse.error()` with appropriate HTTP status codes (not `HTTPException`) except for auth failures which use `HTTPException`
- Backend modules are self-contained with their own router/schemas/service layers
- Python managed with `uv`; frontend managed with `npm`
- Agent prompt templates stored as Python string constants or markdown files in `prompt/` subdirectories
- Global singletons pattern: `memory_service`, `mcp_manager`, `chat_agent`, `mindmap_generator` are module-level instances
- LLM config uses `OPENAI_API_BASE` for endpoint URL (OpenAI-compatible API)