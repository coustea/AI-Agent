# AI Learning Platform (多智能体个性化学习资源平台)

A comprehensive AI-powered learning platform leveraging Multi-Agent Systems (MAS) to provide personalized tutoring, learner profiling, path planning, and multimodal resource generation.

## Project Overview

### Core Architecture
- **MAS Design**: Orchestrates multiple specialized agents using **LangGraph** (for stateful conversations) and a DAG-based parallel execution model (for resource generation).
- **Three-Layer Memory**: Integrates **Short-term History** (ChatSession), **Summarized Context** (Incremental Summary), and **Long-term Memory** (User Facts) for deep personalization.
- **Learner Profiling**: Maintains an 8-dimensional user profile (Goal, Preference, Style, Proficiency, etc.) updated dynamically from interactions and events.

### Tech Stack
- **Frontend**: Vue 3 (Composition API), TypeScript, Vite 7, Element Plus, ECharts, Mermaid, Katex.
- **Backend**: FastAPI (Python 3.13+), SQLModel (PostgreSQL with `asyncpg`), LangChain, LangGraph.
- **AI/LLM**: Support for OpenAI-compatible APIs (GPT-4o-mini), Zhipu GLM-4V (Vision), and Spark (Voice/Vision).
- **Tools**: Tavily/SerpAPI/DuckDuckGo for web search, Tesseract OCR for vision analysis.

---

## Building and Running

### Prerequisites
- Python 3.13+ and [uv](https://docs.astral.sh/uv/)
- Node.js 18+ and npm
- PostgreSQL 14+
- Tesseract OCR (with `chi_sim` and `eng` languages)

### Backend Setup (in `server/`)
1. **Sync Dependencies**: `uv sync`
2. **Configure**: Copy/edit `config.yaml` (Note: `config.yaml` is the authoritative source, not `.env`).
3. **Run Dev Server**: `uv run fastapi dev app/main.py` (Port 9999)
4. **Test**: `uv run pytest`

### Frontend Setup (at root)
1. **Install**: `npm install`
2. **Run Dev Server**: `npm run dev` (Port 5173, proxies `/api` to 9999)
3. **Build**: `npm run build` (Includes `vue-tsc` type checking)

---

## Development Conventions

### Backend (app/ modular structure)
- **Module Pattern**: Each feature (auth, chat, resource, profile) is a directory containing `api.py` (routes), `service.py` (logic), and `schemas.py` (DTOs).
- **Unified Response**: Use `app.infra.response.HttpResponse` for all API results: `{code, message, data}`.
- **Database**: 
  - Use **SQLModel** in `app.infra.models.py`. 
  - New tables must be added to `REGISTERED_MODELS` to be auto-created by `init_db()`.
  - Prefer `AsyncSession` via `get_session` (DI) or `session_scope` (manual).
- **Agent Workflows**:
  - `TutorAgent`: Uses LangGraph `StateGraph` for multi-step reasoning, tool usage, and diagram generation.
  - `ResourceAgents`: Inherit from `BaseResourceAgent` and register via `@register_agent`. Execute in parallel via `asyncio.gather`.

### Frontend (src/ structure)
- **Vue 3 Style**: Use `<script setup lang="ts">` exclusively.
- **Component Order**: Imports → defineProps/Emits → Composables → Refs/Reactive → Computed → Watchers → Lifecycle → Methods.
- **CSS**: Use `<style scoped>` and follow the project's color variable system.

---

## Key Files & Directories

### Backend Entry Points
- `server/app/main.py`: App initialization and route mounting.
- `server/config.yaml`: Centralized configuration.
- `server/app/infra/models.py`: Authoritative database schema definitions.
- `server/app/chat/agent.py`: Core logic for the AI Tutor.
- `server/app/resource/service.py`: Orchestration of multi-agent resource generation.

### Frontend Entry Points
- `src/main.ts`: Entry file, plugin registration (LearningTracker).
- `src/router/index.ts`: Route definitions and auth guards.
- `src/shared/layouts/MainLayout.vue`: Primary immersive UI shell.
- `src/chat/views/Tutor.vue`: AI Tutor interaction interface.
- `src/resource/views/ResourceGenerator.vue`: MAS resource generation UI.

---

## Knowledge & Memory System
- **Long-term Memory**: Facts extracted from conversations into `UserLongTermMemory`.
- **Profiles**: Incremental updates to `UserProfile` 8-dimension data.
- **Knowledge Base**: Integrated RAG using ChromaDB/FAISS (configured in `config.yaml`).
