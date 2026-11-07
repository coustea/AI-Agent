"""Chat harness 测试 —— 事件归约、纯 Agent 循环、钩子落库顺序。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from app.chat.harness.events import (
    ChatActivity,
    RunEvent,
    RunState,
    encode_chat_sse,
    reduce_state,
)
from app.chat.harness.handlers import ChatRunHandlers, RunContext
from app.chat.harness.hooks import HookBus
from app.chat.harness.loop import AgentLoop
from app.infra.llm import TextDelta, ToolCall, TurnDone
from app.shared.tools.registry import Tool


class _FakeLLM:
    """按预设轮次产出流式片段的假模型。"""

    def __init__(self, rounds: list[list[Any]]) -> None:
        """保存待消费的轮次队列。"""
        self._rounds = rounds
        self.calls: list[dict[str, Any]] = []

    async def stream(self, messages, *, tools=None, tool_choice=None):
        """依次产出当前轮次的片段。"""
        self.calls.append({"tools": tools, "tool_choice": tool_choice})
        items = self._rounds.pop(0) if self._rounds else [TurnDone(text="")]
        for item in items:
            yield item


class _EchoArgs(BaseModel):
    """echo 工具参数。"""

    q: str


async def _echo(q: str) -> dict[str, Any]:
    """回显工具实现。"""
    return {"text": f"知识:{q}", "sources": [{"title": "T", "url": "https://x"}]}


def _make_loop(rounds: list[list[Any]], tools: list[Tool] | None = None, **kwargs: Any) -> AgentLoop:
    """装配一个脱离数据库的循环实例。"""
    from app.shared.tools.registry import ToolRegistry

    hooks = HookBus()
    return AgentLoop(
        llm=_FakeLLM(rounds),
        messages=[],
        registry=ToolRegistry(tools=tools) if tools else None,
        hooks=hooks,
        **kwargs,
    )


class TestReduceState:
    def test_delta_accumulates(self):
        state = RunState(run_id="r1")
        state = reduce_state(state, RunEvent(run_id="r1", sequence=1, event="text.delta", data={"delta": "你"}))
        state = reduce_state(state, RunEvent(run_id="r1", sequence=2, event="text.delta", data={"delta": "好"}))
        assert state.content == "你好"

    def test_stale_sequence_is_ignored(self):
        state = RunState(run_id="r1", sequence=5, content="abc")
        after = reduce_state(state, RunEvent(run_id="r1", sequence=3, event="text.delta", data={"delta": "x"}))
        assert after is state

    def test_foreign_run_is_ignored(self):
        state = RunState(run_id="r1")
        after = reduce_state(state, RunEvent(run_id="r2", sequence=1, event="run.started"))
        assert after is state

    def test_activity_is_upserted(self):
        state = RunState(run_id="r1")
        activity = ChatActivity(activity_id="tool:c1", kind="tool", title="调用 echo")
        state = reduce_state(
            state,
            RunEvent(run_id="r1", sequence=1, event="activity.updated", data=activity.model_dump()),
        )
        state = reduce_state(
            state,
            RunEvent(
                run_id="r1",
                sequence=2,
                event="activity.updated",
                data=ChatActivity(
                    activity_id="tool:c1", kind="tool", title="调用 echo", status="completed"
                ).model_dump(),
            ),
        )
        assert len(state.activities) == 1
        assert state.activities[0].status == "completed"

    def test_terminal_sets_status_and_error(self):
        state = RunState(run_id="r1", status="running")
        state = reduce_state(
            state,
            RunEvent(run_id="r1", sequence=1, event="run.failed", data={"error": "boom"}),
        )
        assert state.status == "failed"
        assert state.error == "boom"

    def test_sse_frame_uses_chat_event_name(self):
        frame = encode_chat_sse(RunEvent(run_id="r1", sequence=4, event="run.started"))
        assert "event: chat.event" in frame
        assert frame.startswith("id: 4")


class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_plain_answer_without_tools(self):
        loop = _make_loop([[TextDelta("你好"), TurnDone(text="你好")]])
        assert await loop.run() == "你好"

    @pytest.mark.asyncio
    async def test_tool_result_is_fed_back_in_order(self):
        loop = _make_loop(
            [
                [TurnDone(text="", tool_calls=(ToolCall(id="c1", name="echo", args={"q": "TCP"}),))],
                [TextDelta("最终回答"), TurnDone(text="最终回答")],
            ],
            tools=[Tool("echo", "Echo", _EchoArgs, _echo)],
        )
        assert await loop.run() == "最终回答"
        assert [m.role for m in loop.messages] == ["assistant", "tool"]

    @pytest.mark.asyncio
    async def test_multi_tool_turn_keeps_call_order(self):
        seen: list[str] = []

        async def _record(q: str) -> dict[str, Any]:
            seen.append(q)
            return {"text": q}

        tools = [
            Tool("echo_a", "A", _EchoArgs, _record),
            Tool("echo_b", "B", _EchoArgs, _record),
        ]
        loop = _make_loop(
            [
                [TurnDone(
                    text="",
                    tool_calls=(
                        ToolCall(id="c1", name="echo_a", args={"q": "x"}),
                        ToolCall(id="c2", name="echo_b", args={"q": "y"}),
                    ),
                )],
                [TurnDone(text="完成")],
            ],
            tools=tools,
        )
        await loop.run()
        tool_messages = [m for m in loop.messages if m.role == "tool"]
        assert [m.tool_call_id for m in tool_messages] == ["c1", "c2"]
        assert sorted(seen) == ["x", "y"]

    @pytest.mark.asyncio
    async def test_max_steps_raises(self):
        loop = _make_loop(
            [
                [TurnDone(text="", tool_calls=(ToolCall(id=f"c{i}", name="echo", args={"q": "x"}),))]
                for i in range(3)
            ],
            tools=[Tool("echo", "Echo", _EchoArgs, _echo)],
            max_steps=2,
            max_tool_rounds=10,
        )
        with pytest.raises(RuntimeError, match="超过最大推理步数"):
            await loop.run()

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        class _SlowLLM:
            async def stream(self, messages, *, tools=None, tool_choice=None):
                """永不返回的流。"""
                await asyncio.sleep(5)
                yield TurnDone(text="")

        loop = AgentLoop(
            llm=_SlowLLM(),
            messages=[],
            registry=None,
            hooks=HookBus(),
            timeout_s=0.01,
        )
        with pytest.raises(RuntimeError, match="运行超时"):
            await loop.run()

    @pytest.mark.asyncio
    async def test_tool_failure_is_captured_as_result(self):
        async def _boom(q: str) -> dict[str, Any]:
            """总是抛错的工具。"""
            raise RuntimeError("炸了")

        loop = _make_loop(
            [
                [TurnDone(text="", tool_calls=(ToolCall(id="c1", name="boom", args={"q": "x"}),))],
                [TurnDone(text="兜底回答")],
            ],
            tools=[Tool("boom", "Boom", _EchoArgs, _boom)],
        )
        assert await loop.run() == "兜底回答"
        tool_message = next(m for m in loop.messages if m.role == "tool")
        assert "工具执行失败" in tool_message.content


class TestHookBus:
    @pytest.mark.asyncio
    async def test_handler_failure_does_not_break_others(self):
        bus = HookBus()
        seen: list[str] = []

        async def _bad() -> None:
            """故意抛错。"""
            raise RuntimeError("bad")

        async def _good() -> None:
            """记录被调用。"""
            seen.append("ok")

        bus.on("run_started", _bad)
        bus.on("run_started", _good)
        await bus.trigger("run_started")
        assert seen == ["ok"]


class TestHandlersPersistence:
    @pytest.mark.asyncio
    async def test_multi_tool_turn_persists_one_request_then_ordered_results(self):
        """一轮多个工具调用：只落一条 assistant 消息，tool 结果按调用顺序落库。"""
        memory = AsyncMock()
        memory.save_message.return_value = SimpleNamespace(id=7)
        events = AsyncMock()
        ctx = RunContext(
            run_id="r1",
            user_id=1,
            username="u",
            session_id="s1",
            user_message_id=1,
            question="hi",
        )
        handlers = ChatRunHandlers(ctx, events)
        handlers.memory = memory

        calls = [
            ("c1", ToolCall(id="c1", name="echo_a", args={"q": "x"})),
            ("c2", ToolCall(id="c2", name="echo_b", args={"q": "y"})),
        ]
        with patch("app.chat.harness.handlers.session_scope", _fake_session_scope):
            await handlers.on_tools_started(calls)

        saved = [call.kwargs for call in memory.save_message.await_args_list]
        request_rows = [row for row in saved if row.get("tool_calls")]
        assert len(request_rows) == 1, "多个 tool_calls 必须合并成一条 assistant 消息"
        assert [tc["id"] for tc in request_rows[0]["tool_calls"]] == ["c1", "c2"]
        assert request_rows[0]["run_id"] == "r1"

    @pytest.mark.asyncio
    async def test_tool_results_persist_in_call_order(self):
        memory = AsyncMock()
        memory.save_message.return_value = SimpleNamespace(id=8)
        events = AsyncMock()
        ctx = RunContext(
            run_id="r1",
            user_id=1,
            username="u",
            session_id="s1",
            user_message_id=1,
            question="hi",
        )
        handlers = ChatRunHandlers(ctx, events)
        handlers.memory = memory

        from app.chat.harness.loop import ToolResult

        results = [
            ToolResult("c1", "echo_a", {"q": "x"}, "结果一", "ok"),
            ToolResult("c2", "echo_b", {"q": "y"}, "结果二", "ok"),
        ]
        with patch("app.chat.harness.handlers.session_scope", _fake_session_scope):
            for result in results:
                await handlers.on_tool_finished(result)

        saved = [call.kwargs for call in memory.save_message.await_args_list]
        assert [row["tool_call_id"] for row in saved] == ["c1", "c2"]
        assert all(row["run_id"] == "r1" for row in saved)


@asynccontextmanager
async def _fake_session_scope():
    """替代数据库会话，避免测试触碰真实 MySQL。"""
    yield SimpleNamespace(get=AsyncMock(return_value=None), add=lambda *_: None, commit=AsyncMock())
