from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.chat.agent import nodes
from app.chat.agent.nodes import react_node, split_reasoning_and_answer
from app.infra.tool_excute import Tool


def test_split_public_summary_from_answer_envelope() -> None:
    text = """
先判断学生选择的算法，再用例子解释护航效应。

<answer>
**FCFS** 是先来先服务调度算法。
</answer>
"""

    reasoning, answer = split_reasoning_and_answer(text)

    assert reasoning == "先判断学生选择的算法，再用例子解释护航效应。"
    assert answer == "**FCFS** 是先来先服务调度算法。"


def test_plain_text_is_not_treated_as_final_answer() -> None:
    reasoning, answer = split_reasoning_and_answer("你好，有什么可以帮你？")

    assert reasoning == "你好，有什么可以帮你？"
    assert answer == ""


def test_unclosed_answer_envelope_does_not_leak_into_summary_or_answer() -> None:
    reasoning, answer = split_reasoning_and_answer(
        "已经整理完成。<answer>这是尚未闭合的正式回答"
    )

    assert reasoning == ""
    assert answer == ""


class FakeChunk:
    def __init__(
        self,
        content: str = "",
        tool_calls: list[dict] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.tool_call_chunks = []

    def __add__(self, other: "FakeChunk") -> "FakeChunk":
        return FakeChunk(
            content=self.content + other.content,
            tool_calls=other.tool_calls or self.tool_calls,
        )


class FakeModel:
    def __init__(self) -> None:
        self.bound_tools: list[dict] = []

    def bind_tools(self, tools: list[dict]):
        self.bound_tools = tools
        return self


class FakeLlm:

    def __init__(self, iterations: list[list[FakeChunk]]) -> None:
        self.iterations = iter(iterations)
        self.model = FakeModel()
        self.stream_models = []

    async def astream(self, messages: list, temperature: float, model=None):
        self.stream_models.append(model)
        for chunk in next(self.iterations):
            yield chunk


class RecordingAgent:
    def __init__(self) -> None:
        self.events = []

    async def _emit_event(self, state, event, **kwargs):
        self.events.append(event)
        return [event]


class FakePrompts:
    class ChatPrompts:
        @staticmethod
        def render(name: str, **kwargs) -> str:
            return "system"

    @staticmethod
    def get(name: str) -> "FakePrompts.ChatPrompts":
        return FakePrompts.ChatPrompts()


@pytest.mark.asyncio
async def test_tool_iteration_text_stays_in_activity_and_final_answer_is_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SearchArgs(BaseModel):
        query: str

    async def search_knowledge_base(query: str) -> str:
        return f"课程资料：{query}"

    search_tool = Tool(
        name="search_knowledge_base",
        description="搜索课程知识库",
        args_model=SearchArgs,
        handler=search_knowledge_base,
    )
    llm = FakeLlm([
        [
            FakeChunk(
                "需要先查询课程知识库。"
            ),
            FakeChunk(
                tool_calls=[{
                    "id": "call-1",
                    "name": "search_knowledge_base",
                    "args": {"query": "FCFS"},
                }]
            ),
        ],
        [
            FakeChunk(
                "资料已齐全，可以组织讲解。\n\n"
                "<answer>**FCFS** 是先来先服务。</answer>"
            )
        ],
    ])
    monkeypatch.setattr(nodes, "build_tutor_tools", lambda context: [search_tool])
    agent = RecordingAgent()

    result = await react_node(
        agent,
        {
            "question": "讲解 FCFS",
            "user_id": 1,
            "session_id": "session-1",
        },
        llm=llm,
        prompts=FakePrompts(),
        memory_service=None,
    )

    token_events = [
        event.payload["token"]
        for event in agent.events
        if event.type == "answer_token"
    ]
    completed_thinking = [
        event
        for event in agent.events
        if event.type == "agent_status"
        and event.payload.get("stage") == "thinking"
        and event.payload.get("status") == "done"
    ]
    tool_activities = [
        event
        for event in agent.events
        if event.type == "agent_status"
        and event.payload.get("kind") == "tool"
    ]

    assert "".join(token_events) == "**FCFS** 是先来先服务。"
    assert result["final_answer"] == "**FCFS** 是先来先服务。"
    assert [event.payload["summary"] for event in completed_thinking] == [
        "需要先查询课程知识库。",
        "资料已齐全，可以组织讲解。",
    ]
    assert llm.model.bound_tools[0]["function"]["name"] == "search_knowledge_base"
    assert all(model is llm.model for model in llm.stream_models)
    assert all("<answer>" not in token for token in token_events)
    assert [event.payload["status"] for event in tool_activities] == ["running", "done"]
    assert agent.events.index(completed_thinking[0]) < agent.events.index(tool_activities[0])
    assert agent.events.index(tool_activities[-1]) < agent.events.index(completed_thinking[-1])
    assert agent.events.index(completed_thinking[-1]) < next(
        index for index, event in enumerate(agent.events) if event.type == "answer_token"
    )


@pytest.mark.asyncio
async def test_missing_answer_envelope_is_repaired_before_streaming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = FakeLlm([
        [FakeChunk("这段文字没有最终回答边界。")],
        [FakeChunk("格式已修复。<answer>这是正式回答。</answer>")],
    ])
    monkeypatch.setattr(nodes, "build_tutor_tools", lambda context: [])
    agent = RecordingAgent()

    result = await react_node(
        agent,
        {
            "question": "你好",
            "user_id": 1,
            "session_id": "session-1",
        },
        llm=llm,
        prompts=FakePrompts(),
        memory_service=SimpleNamespace(),
    )

    token_text = "".join(
        event.payload["token"]
        for event in agent.events
        if event.type == "answer_token"
    )
    assert token_text == "这是正式回答。"
    assert result["final_answer"] == "这是正式回答。"
    assert "这段文字没有最终回答边界。" not in token_text
    assert len(llm.stream_models) == 2
