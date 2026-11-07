"""Chat Agent 单循环与 RunStream 实时透明状态流测试。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.chat.agent import RunStream, _active_streams, request_cancel_run, run_tutor_agent
from app.chat.schemas import RunArtifact, RunStep
from app.infra.llm import TextDelta, ToolCall, TurnDone
from app.shared.tools import Tool


@asynccontextmanager
async def _noop_session_scope():
    """在单元测试中替代真实数据库会话。"""
    yield SimpleNamespace(
        get=AsyncMock(return_value=None),
        exec=AsyncMock(return_value=SimpleNamespace(first=lambda: None)),
        add=lambda *_: None,
    )


class _EchoArgs(BaseModel):
    query: str


class TestRunStream:
    @pytest.mark.asyncio
    async def test_snapshot_and_sub_steps_flow(self) -> None:
        stream = RunStream("run-test-1")
        queue, snap = await stream.subscribe()
        assert snap.event == "run.snapshot"
        assert snap.data["status"] == "queued"

        await stream.set_phase("thinking", "正在思考...")
        ev1 = await queue.get()
        assert ev1.event == "phase.changed"
        assert ev1.data["phase"] == "thinking"

        step = RunStep(
            step_id="tool:c1",
            kind="subagent",
            title="生成教学动画视频",
            subtitle="主题：快速排序",
            status="running",
            progress=5,
        )
        await stream.upsert_step(step)
        ev2 = await queue.get()
        assert ev2.event == "step.upsert"

        await stream.append_sub_step("tool:c1", "第 1 步：编写分镜脚本", progress=30)
        ev_phase = await queue.get()
        ev_step = await queue.get()
        assert ev_phase.event == "phase.changed"
        assert "第 1 步：编写分镜脚本" in ev_phase.data["phase_label"]
        assert ev_step.event == "step.upsert"
        assert ev_step.data["progress"] == 30
        assert len(ev_step.data["sub_steps"]) == 1

        await stream.append_text_delta("你好")
        await stream.add_artifact(RunArtifact(id="v1", kind="video", title="快排", url="/static/v.mp4"))
        await stream.finish("completed", phase_label="回答完成")

        assert stream.state.status == "completed"
        assert stream.state.content == "你好"
        assert stream.state.steps[0].status == "completed"
        assert stream.state.steps[0].sub_steps[0].status == "completed"
        await stream.unsubscribe(queue)


class TestRunTutorAgent:
    @pytest.mark.asyncio
    async def test_multi_step_tool_and_streaming_answer(self, monkeypatch) -> None:
        rounds = [
            [TurnDone(text="", tool_calls=(ToolCall(id="c1", name="knowledge_search", args={"query": "TCP"}),))],
            [TextDelta("TCP 是面向连接的协议。"), TurnDone(text="TCP 是面向连接的协议。")],
        ]

        class FakeLLM:
            def __init__(self, **kwargs: Any) -> None:
                pass

            async def stream(self, messages, *, tools=None, tool_choice=None):
                for item in rounds.pop(0):
                    yield item

        async def _fake_search(query: str) -> dict[str, Any]:
            return {
                "text": f"检索到 {query} 资料",
                "sources": [{"source": "kb", "title": "计算机网络", "score": 0.95}],
            }

        monkeypatch.setattr("app.chat.agent.session_scope", _noop_session_scope)
        monkeypatch.setattr("app.chat.agent.build_turn_messages", AsyncMock(return_value=[]))
        monkeypatch.setattr(
            "app.chat.agent.build_tutor_tools",
            lambda **kwargs: [Tool("knowledge_search", "Search KB", _EchoArgs, _fake_search)],
        )
        monkeypatch.setattr("app.chat.agent.LLM", FakeLLM)
        monkeypatch.setattr("app.chat.agent.run_post_turn_memory_jobs", AsyncMock())

        state = await run_tutor_agent(
            run_id="run-agent-1",
            user_id=1,
            username="alice",
            session_id="s-1",
            user_message_id=10,
            question="什么是 TCP？",
        )

        assert state.status == "completed"
        assert state.content == "TCP 是面向连接的协议。"
        assert len(state.sources) == 1
        assert state.sources[0].title == "计算机网络"
        # 包含第 1 轮思考、1 个工具调用、第 2 轮思考，且全部为 completed（无残留 running）
        assert [s.kind for s in state.steps] == ["thinking", "knowledge", "thinking"]
        assert all(s.status == "completed" for s in state.steps)

    @pytest.mark.asyncio
    async def test_cancel_during_run(self, monkeypatch) -> None:
        class SlowLLM:
            def __init__(self, **kwargs: Any) -> None:
                pass

            async def stream(self, messages, *, tools=None, tool_choice=None):
                request_cancel_run("run-cancel-1")
                yield TextDelta("半截回答")
                yield TurnDone(text="半截回答")

        monkeypatch.setattr("app.chat.agent.session_scope", _noop_session_scope)
        monkeypatch.setattr("app.chat.agent.build_turn_messages", AsyncMock(return_value=[]))
        monkeypatch.setattr("app.chat.agent.build_tutor_tools", lambda **kwargs: [])
        monkeypatch.setattr("app.chat.agent.LLM", SlowLLM)

        state = await run_tutor_agent(
            run_id="run-cancel-1",
            user_id=1,
            username="alice",
            session_id="s-1",
            user_message_id=11,
            question="测试取消",
        )
        assert state.status == "cancelled"
        assert "run-cancel-1" not in _active_streams
