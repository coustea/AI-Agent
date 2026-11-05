"""chat 事件契约与 TutorAgent ReAct 循环测试。"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.chat.agent import TutorAgent
from app.chat.schemas import TutorInput
from app.chat.stream import ChatEventName, runtime_status
from app.infra.llm import TextDelta, ToolCall, TurnDone


class TestChatEventNames:
    def test_content_replace_is_valid(self):
        event: ChatEventName = "content.replace"
        assert event == "content.replace"


class TestRuntimeStatus:
    def test_done_to_completed(self):
        assert runtime_status("done") == "completed"

    def test_error_to_failed(self):
        assert runtime_status("error") == "failed"

    def test_running_stays(self):
        assert runtime_status("running") == "running"

    def test_none_defaults_to_running(self):
        assert runtime_status(None) == "running"


def _make_input() -> TutorInput:
    return TutorInput(
        user_id=1,
        username="u",
        session_id="s1",
        user_message_id=1,
        question="hi",
    )


class TestSaveActivity:
    @pytest.mark.asyncio
    async def test_persists_activity(self):
        memory_service = AsyncMock()
        agent = TutorAgent(memory_service=memory_service)
        inp = _make_input()
        payload = {"stage": "thinking", "status": "running"}

        await agent._save_activity(inp, payload)

        memory_service.upsert_activity.assert_awaited_once()
        kwargs = memory_service.upsert_activity.await_args.kwargs
        assert kwargs["user_id"] == 1
        assert kwargs["session_id"] == "s1"
        assert kwargs["payload"] == payload

    @pytest.mark.asyncio
    async def test_persist_failure_is_swallowed(self):
        memory_service = AsyncMock()
        memory_service.upsert_activity.side_effect = RuntimeError("db down")
        agent = TutorAgent(memory_service=memory_service)

        await agent._save_activity(_make_input(), {"stage": "thinking"})


class _FakeLLM:
    def __init__(self, rounds: list[list[Any]]) -> None:
        self._rounds = rounds
        self.calls: list[dict[str, Any]] = []

    async def stream(self, messages, *, tools=None, tool_choice=None):
        self.calls.append({"messages": list(messages), "tools": tools, "tool_choice": tool_choice})
        items = self._rounds.pop(0) if self._rounds else [TurnDone(text="")]
        for item in items:
            yield item


class TestTutorAgentLoop:
    @pytest.mark.asyncio
    async def test_agent_yields_plain_event_dicts(self):
        agent = TutorAgent(memory_service=AsyncMock())
        fake_llm = _FakeLLM([[TextDelta("你好"), TurnDone(text="你好")]])

        with (
            patch("app.chat.agent.build_messages", AsyncMock(return_value=[])),
            patch("app.chat.agent.build_tutor_tools", return_value=[]),
            patch("app.chat.agent.LLM", return_value=fake_llm),
        ):
            events = [e async for e in agent.chat(_make_input())]

        assert all(set(e) == {"event", "data"} for e in events)
        kinds = [e["event"] for e in events]
        assert "token" in kinds
        assert "done" in kinds
        done = next(e for e in events if e["event"] == "done")
        assert done["data"]["final_answer"] == "你好"

    @pytest.mark.asyncio
    async def test_agent_executes_tool_and_continues(self):
        from pydantic import BaseModel
        from app.shared.tools import Tool

        class _Args(BaseModel):
            q: str

        async def _echo(q: str) -> dict[str, Any]:
            return {"text": f"知识:{q}", "sources": [{"title": "T", "url": "https://x"}]}

        echo_tool = Tool("echo", "Echo tool", _Args, _echo)
        agent = TutorAgent(memory_service=AsyncMock())
        fake_llm = _FakeLLM([
            [TurnDone(text="", tool_calls=(ToolCall(id="c1", name="echo", args={"q": "TCP"}),))],
            [TextDelta("最终回答"), TurnDone(text="最终回答")],
        ])

        with (
            patch("app.chat.agent.build_messages", AsyncMock(return_value=[])),
            patch("app.chat.agent.build_tutor_tools", return_value=[echo_tool]),
            patch("app.chat.agent.LLM", return_value=fake_llm),
        ):
            events = [e async for e in agent.chat(_make_input())]

        done = next(e for e in events if e["event"] == "done")
        assert done["data"]["final_answer"] == "最终回答"
        assert len(done["data"]["tool_invocations"]) == 1
        assert done["data"]["tool_invocations"][0]["tool_name"] == "echo"
        assert len(done["data"]["sources"]) == 1
        assert done["data"]["sources"][0]["url"] == "https://x"
