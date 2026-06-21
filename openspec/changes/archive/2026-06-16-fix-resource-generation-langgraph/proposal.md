## Why

A code corruption issue in `server/app/resource/service.py` has introduced a Python compilation error (`IndentationError` and duplicate trailing blocks). This completely blocks the backend server from compiling and running tests, and prevents the LangGraph-based multi-agent resource generation workflow from running. 

This change will clean up all the leftover/corrupted old orchestration code and restore the clean LangGraph pipeline to a functional, compilable state.

## What Changes

- **Clean up leftover code**: Completely delete the corrupted, duplicated non-LangGraph orchestration logic at the bottom of `server/app/resource/service.py`.
- **Restore helper methods**: Restore the complete and correct implementations of `count_resources` and the helper `_source_allowed` static method in `ResourceService`.
- **Align orchestration entry point**: Clean up the `run_multi_agent_generation` function so it only contains the clean LangGraph invocation (`graph.ainvoke`).

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None

## Impact

- **Affected Files**: `server/app/resource/service.py`
- **APIs**: Restores the `/api/v1/ai/resources` (POST) and `/api/v1/ai/resources/single` (POST) API endpoints functionality.
- **Testing**: Fixes backend test collection errors, allowing `pytest` tests to be run successfully for all resource agents.
