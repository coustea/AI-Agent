# Task 2 Report: Diagram Tool Boundary — Required Direct Execution & Auto Terminal Tool Behavior

## Changes Made

### `server/app/chat/agent/nodes.py` — `react_node`

**1. Required mode direct execution (lines 750-816)**

Replaced the previous `RuntimeError`-raising required-mode block with a robust implementation:

- Emits `agent_status` "generating diagram" event before the direct tool call (stage=`diagram_generation`, status=`running`)
- Calls `execute_tutor_tool` with `tool_call_id="direct-diagram-required"` and `arguments={"focus": question}`
- On success: validates via `validate_diagram_json`, sets `node_diagram_result`, returns immediately with `final_answer=""` and no `answer_token` events
- On validation failure: appends error to `node_errors` (no exception raised)
- On no payload: appends error to `node_errors` (no exception raised)
- On exception: catches it, logs warning, appends to `node_errors` (no exception raised)
- Emits completion `agent_status` event (status=`done` or `failed`)
- Voice mode condensation only applies when `node_diagram_result is not None`

**2. Auto mode terminal tool behavior (lines 1133-1168)**

Replaced `RuntimeError` raises with graceful error handling:

- On diagram tool success (validated payload): sets `node_diagram_result`, breaks out of `for tool_call` loop, then outer `while` loop breaks via the `if node_diagram_result is not None` check — no `ToolMessage` appended, no further LLM rounds
- On validation failure: logs warning, appends error to `node_errors`, appends `ToolMessage` with failure info, `continue`s to next tool_call
- On no payload: same graceful error path — appends error, appends `ToolMessage`, `continue`s
- The existing `except Exception` handler still catches any unexpected errors from `execute_tutor_tool` itself

**3. Deterministic fallback scoped to auto mode only (line 1187)**

Changed condition from `diagram_required and node_diagram_result is None and full_answer.strip()` to `not diagram_required and node_diagram_result is None and full_answer.strip()`. This ensures:
- In `required` mode: if the direct tool call failed, the turn fails with errors — no silent fallback
- In `auto` mode: the deterministic fallback still applies when the LLM mentions diagram keywords but doesn't produce valid markup

**4. Smart quote fix (line 846-848)**

Fixed pre-existing smart quote characters (U+201C/U+201D) in the `diagram_mode` prompt string that caused a `SyntaxError`. Replaced with properly escaped ASCII double quotes.

## Test Results

```
76 passed in 0.98s
```

Tests run: `test_agent_events.py`, `test_diagram_tool.py`, `test_diagram_mode_api.py`, `test_evidence_assembly.py`, `test_utils.py`, `test_streaming.py`, `test_tool_excute.py`

Pre-existing failures (unrelated to this task):
- `test_history.py` — `FakeMemoryService` missing `list_attachment_analyses`
- `test_schemas.py` — validation rule changes
- `test_teaching_diagram_agent.py` — renderer signature mismatches
- Multiple test files with import errors from prior refactoring

## Concerns

1. The auto-mode diagram tool failure path appends a `ToolMessage` and continues the ReAct loop. This means the LLM will see the failure message and may attempt to produce a text answer or retry. This is intentional per the brief ("let the existing error path handle it"), but could lead to an extra LLM round. If stricter behavior is desired (immediate termination on diagram tool failure in auto mode), the `continue` could be changed to a `break`.

2. The `condense_voice_diagram_answer(question)` call in required mode uses the raw `question` as the text to condense, since there is no LLM-generated answer text. This produces a short voice narration from the question itself, which may not be ideal. A future improvement could generate a brief narration from the diagram's `teaching_content` fields instead.
