from __future__ import annotations

from app.chat.agent.tool_runner import ToolExecutionResult


def test_tool_execution_result_exposes_raw_result_payload() -> None:
    payload = {"kind": "diagram", "title": "TCP 与 UDP"}

    result = ToolExecutionResult(invocation={"result_payload": payload})

    assert result.result_payload is payload


def test_tool_execution_result_without_invocation_has_no_raw_payload() -> None:
    result = ToolExecutionResult()

    assert result.result_payload is None
