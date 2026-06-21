## ADDED Requirements

### Requirement: Backend Compilation and Pytest Execution
The backend codebase MUST compile successfully without any Python syntax or indentation errors, and all tests in `tests/resource` MUST pass.

#### Scenario: Running pytest on resource tests
- **WHEN** running `uv run pytest tests/resource` in the `server` directory
- **THEN** all tests are successfully collected, executed, and pass

### Requirement: LangGraph Resource Generation Workflow
The backend SHALL execute the resource generation workflow using the LangGraph engine defined in `workflow_graph.py` without falling back to the legacy orchestration code.

#### Scenario: Triggering resource generation task
- **WHEN** a client calls the POST `/resources` or `/resources/single` endpoint
- **THEN** the server compiles and runs the Parent Graph to schedule all agents, saving the final results to the database upon completion
