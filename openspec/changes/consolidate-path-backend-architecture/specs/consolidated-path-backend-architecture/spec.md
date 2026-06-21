## ADDED Requirements

### Requirement: Consolidated 4-File Architecture
The backend path-planning module SHALL consist of exactly four main modules under `server/app/path/`: `api.py`, `schemas.py`, `service.py`, and `workflows.py`, with no nested subdirectories like `workflows/` or `agents/`.

#### Scenario: Verify file consolidation
- **WHEN** importing modules from `app.path`
- **THEN** all path business logic, types, and workflows SHALL be successfully resolved from the consolidated files

### Requirement: Node Workspace and Lazy Tutorial Generation
The backend PathService SHALL support retrieving a node's workspace and lazily triggering tutorial generation via `/nodes/{node_id}/start-learning` if the tutorial has not yet been generated.

#### Scenario: Node tutorial lazy generation triggers on first-time study
- **WHEN** start-learning endpoint is hit for a node with no current tutorial
- **THEN** the system SHALL run the tutorial generation workflow, commit the generated tutorial, and return the workspace response
