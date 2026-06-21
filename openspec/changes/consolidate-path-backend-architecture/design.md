## Context

The backend path-planning module (`server/app/path/`) is currently over-fragmented, comprising 10 files across nested subdirectories:
- `server/app/path/__init__.py`
- `server/app/path/api.py`
- `server/app/path/events.py`
- `server/app/path/schemas.py`
- `server/app/path/service.py`
- `server/app/path/validation.py`
- `server/app/path/agents/node_learning.py`
- `server/app/path/agents/planner.py`
- `server/app/path/workflows/learn_workflow.py`
- `server/app/path/workflows/plan_workflow.py`
- `server/app/path/workflows/state.py`

This structure creates unnecessary complexity, high cognitive load, and redundant imports.

## Goals / Non-Goals

**Goals:**
- Consolidate files in `server/app/path/` into exactly 4 files: `api.py`, `schemas.py`, `service.py`, and `workflows.py`.
- Keep existing logic, functionality, and data structures 100% intact, including LangGraph workflows and database schema.
- Document and clarify the lazy tutorial generation flow triggered by the frontend.

**Non-Goals:**
- Rewrite the underlying LangGraph logic or LLM prompts.
- Change the frontend application's functionality.
- Modify database schemas or SQLModel tables.

## Decisions

### 1. Consolidated Module Layout
- **`schemas.py`**: Merge existing `schemas.py`, `workflows/state.py` (TypedDict states like `LearnState`, `PlanState`), and `validation.py` (plan validation functions).
- **`service.py`**: Merge existing `service.py` and `events.py` (SSE Event Bus logic, `path_event_bus`).
- **`workflows.py`**: Merge `workflows/learn_workflow.py`, `workflows/plan_workflow.py`, `agents/planner.py` (retaining `PathPlannerAgent`), and `agents/node_learning.py` (retaining `NodeLearningAgent` logic or integrating it as graph nodes).
- **`api.py`**: Kept as is, but imports updated.
*Rationale*: This groups path planning by concern (Rest API -> Service Business Logic -> State Schemas -> Workflows/Agents). The `agents/` and `workflows/` folders are deleted to simplify the module structure.

### 2. Frontend-Backend Integration for Node Tutorials
- Confirming that the frontend uses the lazy-loading flow: when visiting a path node workspace, it checks if `current_tutorial` is null. If it is null, the frontend shows the generation animation and triggers `POST /api/v1/ai/paths/nodes/{node_id}/start-learning`. The backend executes `learn_graph.ainvoke(state)` to generate the markdown content, saves it, and returns it.
- We will preserve this flow without any breaking changes to ensure compatibility.

## Risks / Trade-offs

- **Broken imports across other modules**: Known risk of broken imports in other modules (e.g. `tests/`, `app/routes.py`, `app/chat/`).
- **Mitigation**: Run global grep search for `app.path` imports, update all import references, and run `uv run pytest` to ensure tests continue passing.
