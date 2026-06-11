from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.chat.schemas import ConstraintReport, EvidenceSet, TurnRequest


@pytest.mark.asyncio
async def test_reasoning_agent_returns_tool_intent_from_model_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, tools):
            self.tools = tools
            return self

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            assert model is self.model
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-profile-1",
                        "name": "get_learner_profile",
                        "args": {"dimension": "goals", "reason": "personalize"},
                    }
                ],
            )

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=FakeLlm(), tools=[SimpleNamespace(name="get_learner_profile")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="结合我的目标给建议"),
        EvidenceSet(items=[]),
        ConstraintReport(),
    )

    assert result.tool_name == "get_learner_profile"
    assert result.payload == {"dimension": "goals", "reason": "personalize"}


@pytest.mark.asyncio
async def test_reasoning_agent_returns_final_answer_when_model_has_no_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, tools):
            return self

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            return AIMessage(content="先从定义和例子开始理解。")

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=FakeLlm(), tools=[SimpleNamespace(name="search_knowledge_base")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="解释什么是函数"),
        EvidenceSet(items=[]),
        ConstraintReport(),
    )

    assert result.answer == "先从定义和例子开始理解。"


@pytest.mark.asyncio
async def test_reasoning_agent_respects_explicit_empty_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, _tools):
            raise AssertionError("explicit tools=[] should not bind default tools")

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()
            self.seen_model = "unset"

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            self.seen_model = model
            return AIMessage(content="直接回答。")

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    fake_llm = FakeLlm()
    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=fake_llm, tools=[SimpleNamespace(name="get_learner_profile")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="解释什么是函数"),
        EvidenceSet(items=[]),
        ConstraintReport(),
        tools=[],
    )

    assert fake_llm.seen_model is None
    assert result.answer == "直接回答。"


@pytest.mark.asyncio
async def test_reasoning_agent_reasks_without_tools_when_only_skipped_tool_calls_are_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, _tools):
            return self

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()
            self.models: list[object | None] = []

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            self.models.append(model)
            if len(self.models) == 1:
                return SimpleNamespace(
                    content="",
                    tool_calls=[{"name": "get_learner_profile", "args": {}}],
                )
            return AIMessage(content="根据已有信息回答。")

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    fake_llm = FakeLlm()
    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=fake_llm, tools=[SimpleNamespace(name="get_learner_profile")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="结合我的目标给建议"),
        EvidenceSet(items=[]),
        ConstraintReport(executed_tools=["get_learner_profile"]),
    )

    assert fake_llm.models == [fake_llm.model, None]
    assert result.answer == "根据已有信息回答。"


@pytest.mark.asyncio
async def test_reasoning_agent_parses_json_string_tool_args(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, _tools):
            return self

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            return SimpleNamespace(
                content="",
                tool_calls=[
                    {
                        "name": "search_knowledge_base",
                        "args": '{"query": "函数", "top_k": 3}',
                    }
                ],
            )

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=FakeLlm(), tools=[SimpleNamespace(name="search_knowledge_base")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="解释什么是函数"),
        EvidenceSet(items=[]),
        ConstraintReport(),
    )

    assert result.tool_name == "search_knowledge_base"
    assert result.payload == {"query": "函数", "top_k": 3}
