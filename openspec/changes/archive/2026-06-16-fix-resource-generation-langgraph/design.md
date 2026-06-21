## Context

A recent refactoring to migration toward a LangGraph-based workflow left the `server/app/resource/service.py` file with syntactically corrupted and duplicated code at the bottom. This prevents the server from compiling, and breaks test runner capability entirely.

## Goals / Non-Goals

**Goals:**
- Fix all syntax and indentation errors in `server/app/resource/service.py` to restore backend compilation.
- Remove all deprecated, legacy, and corrupted orchestration code in `server/app/resource/service.py` that is now handled natively by the LangGraph engine in `workflow_graph.py`.
- Restore the `count_resources` and `_source_allowed` helper methods in `ResourceService` to functional states.
- Ensure that all resource tests in `tests/resource/` execute and pass successfully.

**Non-Goals:**
- Adding new features or new agent types to the resource generation system.
- Modifying the state, node structure, or conditional routing of the LangGraph workflow in `workflow_graph.py`.

## Decisions

### Decision: Clean Replacement of `run_multi_agent_generation`
- **Rationale**: The old, manual thread-gathering and SSE emitting logic in the old `run_multi_agent_generation` function has been completely superseded by LangGraph nodes and StateGraph compilation in `workflow_graph.py` (specifically nodes like `planning_node`, `worker_node`, `pre_audit_node`, `ppt_node`, `video_node`, and `save_node`). 
- **Action**: Completely discard the old orchestration loop, saving/reviewing methods from the bottom of `service.py`, and implement a clean, lightweight entry point that sets up the `AgentEventEmitter` and calls `build_parent_graph().ainvoke(...)`.

## Risks / Trade-offs

### [Risk] Lock release failure on error 
- **Mitigation**: Ensure that `usecases._release_write_lock(resource_id)` is executed inside a `finally` block to prevent resource generation locks from leaking, regardless of workflow outcome.
