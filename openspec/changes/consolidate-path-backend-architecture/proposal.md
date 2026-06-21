## Why

The backend path planning module (`server/app/path`) is currently split into 10 separate files spread across directories like `workflows/` and `agents/`. This excessive fragmentation makes it difficult to read, debug, and maintain. In addition, we need to clarify and document the front-to-back integration flow for path node workspace loading and tutorial generation, ensuring a clean and structured communication path without redundant calls.

## What Changes

- **Backend Architecture Consolidation**:
  - Merge existing path files and subdirectories (`workflows/`, `agents/`) into four consolidated files: `api.py`, `schemas.py`, `service.py`, and `workflows.py`.
  - Move TypedDict states and validation logic into `schemas.py`.
  - Move SSE event bus handling and general business logic into `service.py`.
  - Move the LangGraph workflows (`learn_workflow.py`, `plan_workflow.py`) and agent graph nodes (`planner.py`, `node_learning.py`) into `workflows.py`.
  - Remove empty `workflows/` and `agents/` directories.
- **Frontend-Backend Contract Clarity**:
  - Formally document the tutorial generation lifecycle where the frontend requests workspace data and triggers lazy tutorial generation via `POST /api/v1/ai/paths/nodes/{node_id}/start-learning` if not already generated.

## Capabilities

### New Capabilities
- `consolidated-path-backend-architecture`: Define the unified 4-file structure for the path planning and tutorial generation module, enforcing architecture simplification constraints.

### Modified Capabilities
<!-- Leave empty since we are not changing existing user-facing product specs, but rather restructuring backend architecture -->

## Impact

- **Affected Code**: `server/app/path/` files and directories, all import references to `app.path` submodules across the backend (e.g. `app.path.api`, `app.path.service`, `app.path.schemas`, `app.path.workflows.learn_workflow`, etc.).
- **APIs**: The API endpoints will remain identical, but internal logic imports will be updated.
- **Dependencies**: No new packages or dependencies are introduced.
