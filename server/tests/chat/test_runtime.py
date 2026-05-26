from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.runtime import prepare_tutor_state, prepare_tutor_turn
from app.chat.agent import TutorAgent
from app.chat.request import ChatHistoryMessage
from app.chat.schemas import TutorAgentContext
from app.chat.service import ChatUseCases


def test_tutor_system_prompt_forbids_inline_diagram_code_by_default() -> None:
    from app.prompts import registry

    prompt = registry.get("chat/tutor_system").format(
        profile_context="profile",
        fact_context="memory",
        recent_chat_context="recent",
    )

    assert "不要在正文中输出 Mermaid" in prompt
    assert "界面会在你的回答下方直接渲染教学图解" not in prompt


def test_tutor_system_prompt_keeps_learning_topic_statement_brief() -> None:
    from app.prompts import registry

    prompt = registry.get("chat/tutor_system").format(
        profile_context="profile",
        fact_context="memory",
        recent_chat_context="recent",
    )

    assert "学生只是陈述正在学习某个主题" in prompt
    assert "不要立即展开成长篇课程讲义" in prompt
    assert "以下结构只适用于学生已经提出具体问题的回答" in prompt


class FakeTutorContextService:
    def __init__(self) -> None:
        self.long_term_context_calls = 0

    async def build_profile_context(self, user_id: int) -> str:
        return f"profile:{user_id}"

    async def build_memory_context(self, user_id: int) -> str:
        self.long_term_context_calls += 1
        return f"facts:{user_id}"

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str],
        file_urls: list[str],
    ):
        return [HumanMessage(content=user_message)], "recent context"

    @staticmethod
    def build_file_context(image_urls: list[str], file_urls: list[str]) -> str:
        return f"images={len(image_urls)} files={len(file_urls)}"


class CapturingLlmManager:
    def __init__(self) -> None:
        self.calls: list[list[Any]] = []

    async def astream(
        self,
        messages: list[Any],
        **kwargs: Any,
    ):
        self.calls.append(messages)
        yield AIMessage(content="这是搜索后的总结回答")


@pytest.mark.asyncio
async def test_llm_gateway_forces_provider_streaming_for_chat_tokens() -> None:
    from app.infra.llm import Llm

    class CapturingStreamModel:
        def __init__(self) -> None:
            self.stream_kwargs: list[dict[str, Any]] = []

        def bind(self, **_kwargs: Any):
            return self

        async def astream(self, _messages: list[Any], **kwargs: Any):
            self.stream_kwargs.append(kwargs)
            yield AIMessage(content="首段")

    model = CapturingStreamModel()
    gateway = Llm.__new__(Llm)
    gateway._text_model = model
    gateway._text_semaphore = None

    chunks = [chunk async for chunk in gateway.astream([HumanMessage(content="问题")])]

    assert [chunk.content for chunk in chunks] == ["首段"]
    assert model.stream_kwargs == [{"stream": True}]


class FakeMemoryServiceForChatUseCases:
    instances: list["FakeMemoryServiceForChatUseCases"] = []

    def __init__(self, *, module: str) -> None:
        self.module = module
        self.saved: list[dict[str, Any]] = []
        self.after_turn_calls: list[dict[str, Any]] = []
        FakeMemoryServiceForChatUseCases.instances.append(self)

    async def save_message(self, **kwargs: Any) -> int:
        self.saved.append(kwargs)
        return len(self.saved)

    async def get_profile_markdown(self, user_id: int) -> str:
        return f"profile:{user_id}"

    async def get_memory_markdown(self, user_id: int) -> str:
        return f"memory:{user_id}"

    def build_file_context(self, image_urls: list[str], file_urls: list[str]) -> str:
        return f"images={len(image_urls)} files={len(file_urls)}"

    async def list_summaries(self, user_id: int, session_id: str, limit: int = 2) -> list[str]:
        return []

    async def after_turn(self, **kwargs: Any) -> None:
        self.after_turn_calls.append(kwargs)


@pytest.mark.asyncio
async def test_prepare_tutor_turn_carries_teaching_diagram_state(monkeypatch) -> None:
    from app.chat import runtime as runtime_module

    monkeypatch.setattr(
        runtime_module.registry,
        "get",
        lambda key: "recent={recent_chat_context}",
    )

    prepared = await prepare_tutor_turn(
        ctx_service=FakeTutorContextService(),
        user_id=7,
        user_message="Explain TCP handshakes",
        session_id=None,
        image_urls=None,
        file_urls=None,
        enable_search=False,
        enable_long_term_memory=True,
        attachment_analysis=None,
        need_teaching_diagram=True,
    )

    assert prepared.initial_state["need_teaching_diagram"] is True
    assert prepared.initial_state["teaching_diagram"] is None
    assert prepared.initial_state["teaching_diagram_error"] is None
    assert prepared.initial_state["system_prompt"] == "recent=recent context"


@pytest.mark.asyncio
async def test_prepare_tutor_turn_skips_long_term_context_when_memory_disabled(monkeypatch) -> None:
    from app.chat import runtime as runtime_module

    monkeypatch.setattr(
        runtime_module.registry,
        "get",
        lambda key: "recent={recent_chat_context}",
    )

    ctx = FakeTutorContextService()

    prepared = await prepare_tutor_turn(
        ctx_service=ctx,
        user_id=7,
        user_message="Explain TCP handshakes",
        session_id=None,
        image_urls=None,
        file_urls=None,
        enable_search=False,
        enable_long_term_memory=False,
        attachment_analysis=None,
        need_teaching_diagram=False,
    )

    assert ctx.long_term_context_calls == 0


def test_prepare_tutor_state_uses_context_and_history_only() -> None:
    context = TutorAgentContext(
        user_id=7,
        session_id="session-1",
        system_prompt="system prompt",
        session_summary_context="summary",
        recent_chat_context="recent",
        file_context="images=1 files=0",
        attachment_analysis_context="attachment ctx",
        attachment_analysis={"analysis_context": "attachment ctx"},
        image_urls=["/uploads/a.png"],
        file_urls=[],
        enable_search=True,
        need_teaching_diagram=True,
        diagram_mode="requested",
        preferred_diagram_type="contrast",
        generate_video=False,
        resource_mode="none",
    )
    history = [
        ChatHistoryMessage(role="user", content="前一个问题"),
        ChatHistoryMessage(role="assistant", content="前一个回答"),
        ChatHistoryMessage(role="user", content="这轮问题"),
    ]

    state = prepare_tutor_state(context, history)

    assert state["user_id"] == 7
    assert state["session_id"] == "session-1"
    assert state["system_prompt"] == "system prompt"
    assert state["recent_chat_context"] == "recent"
    assert state["attachment_analysis_context"] == "attachment ctx"
    assert state["enable_search"] is True
    assert state["need_teaching_diagram"] is True
    assert state["teaching_diagram"] is None
    assert state["teaching_diagram_error"] is None
    assert state["diagram_type"] == "contrast"
    assert [type(message) for message in state["messages"]] == [HumanMessage, AIMessage, HumanMessage]


@pytest.mark.asyncio
async def test_search_summary_uses_unified_tutor_system_prompt(monkeypatch) -> None:
    from unittest.mock import AsyncMock
    import app.chat.agent
    monkeypatch.setattr(app.chat.agent, "adispatch_custom_event", AsyncMock())
    llm_manager = CapturingLlmManager()
    agent = TutorAgent(
        TutorAgentContext(
            user_id=7,
            session_id="session-1",
            system_prompt="system",
            session_summary_context="summary",
            recent_chat_context="recent",
            file_context="files",
            attachment_analysis_context="",
        )
    )
    agent.llm = llm_manager

    result = await agent._spark_summary_node(
        {
            "user_id": 7,
            "session_id": "session-1",
            "messages": [HumanMessage(content="TCP 三次握手是什么？")],
            "search_result": "搜索结果：TCP handshake uses SYN, SYN-ACK, ACK.",
            "system_prompt": "统一教学 prompt，包含 recent=recent context",
        },
        config={},
    )

    assert result["answer_text"] == "这是搜索后的总结回答"
    first_call = llm_manager.calls[0]
    assert isinstance(first_call[0], SystemMessage)
    assert "统一教学 prompt" in first_call[0].content


@pytest.mark.asyncio
async def test_classify_routes_attachment_with_search_to_search_path() -> None:
    agent = TutorAgent(
        TutorAgentContext(
            user_id=7,
            session_id="session-1",
            system_prompt="system",
            profile_context="profile",
            long_term_memory_context="memory",
            session_summary_context="summary",
            recent_chat_context="recent",
            file_context="files",
            attachment_analysis_context="",
        )
    )

    result = await agent._classify_node(
        {
            "user_id": 7,
            "session_id": "session-1",
            "messages": [HumanMessage(content="结合附件和最新资料解释 Transformer")],
            "file_urls": ["/uploads/transformer.pdf"],
            "image_urls": [],
            "enable_search": True,
            "resource_mode": "none",
        }
    )

    assert result == {"route": "search", "execution_mode": "search"}


@pytest.mark.asyncio
async def test_stream_chat_events_passes_history_to_context_runner_and_persists(monkeypatch) -> None:
    from app.chat import service as service_module

    FakeMemoryServiceForChatUseCases.instances = []
    monkeypatch.setattr(service_module, "MemoryService", FakeMemoryServiceForChatUseCases)
    monkeypatch.setattr(
        service_module, "get_memory_service",
        lambda **kw: FakeMemoryServiceForChatUseCases(**kw),
    )
    # 清除 MemoryService 单例缓存，确保 FakeMemoryService 被使用
    from app.memory.service import _memory_service_cache
    _memory_service_cache.clear()

    captured: dict[str, Any] = {}

    async def fake_runner(**kwargs: Any):
        captured.update(kwargs)
        yield {"event": "token", "data": "你好"}
        yield {"event": "diagram", "data": {"type": "contrast", "title": "判断图板"}}
        yield {
            "event": "done",
            "data": {
                "session_id": kwargs["context"].session_id,
                "full_response": "你好",
                "teaching_diagram": {"type": "contrast", "title": "判断图板"},
            },
        }

    uc = ChatUseCases(stream_runner=fake_runner)
    history = [
        ChatHistoryMessage(role="user", content="前一个问题"),
        ChatHistoryMessage(role="assistant", content="前一个回答"),
        ChatHistoryMessage(role="user", content="这轮问题"),
    ]

    events = [
        event
        async for event in uc.stream_chat_events(
            user_id=7,
            session_id="s1",
            history=history,
            enable_long_term_memory=True,
        )
    ]

    assert captured["history"] == history
    assert events[-1]["event"] == "done"

    memory = FakeMemoryServiceForChatUseCases.instances[0]
    assert [item["role"] for item in memory.saved] == ["user", "assistant"]
    assert memory.saved[0]["content"] == "这轮问题"
    assert memory.saved[1]["content"] == "你好"
    assert memory.saved[1]["teaching_diagram"] == {"type": "contrast", "title": "判断图板"}


@pytest.mark.asyncio
async def test_stream_chat_events_builds_context_and_calls_agent_with_history_only(monkeypatch) -> None:
    from app.chat import service as service_module

    FakeMemoryServiceForChatUseCases.instances = []
    monkeypatch.setattr(service_module, "MemoryService", FakeMemoryServiceForChatUseCases)
    monkeypatch.setattr(
        service_module, "get_memory_service",
        lambda **kw: FakeMemoryServiceForChatUseCases(**kw),
    )
    # 清除 MemoryService 单例缓存，确保 FakeMemoryService 被使用
    from app.memory.service import _memory_service_cache
    _memory_service_cache.clear()

    captured: dict[str, Any] = {}

    class FakeTutorAgent:
        def __init__(self, context: TutorAgentContext) -> None:
            captured["context"] = context

        async def chat_stream(self, history: list[ChatHistoryMessage]):
            captured["history"] = history
            yield {"event": "token", "data": "回答"}
            yield {
                "event": "done",
                "data": {
                    "session_id": captured["context"].session_id,
                    "full_response": "回答",
                },
            }

    monkeypatch.setattr(service_module, "TutorAgent", FakeTutorAgent)

    uc = ChatUseCases()
    history = [ChatHistoryMessage(role="user", content="这轮问题")]

    events = [
        event
        async for event in uc.stream_chat_events(
            user_id=7,
            session_id="s1",
            history=history,
            image_urls=["/uploads/a.png"],
            enable_search=True,
            need_teaching_diagram=True,
        )
    ]

    assert captured["history"] == history
    context = captured["context"]
    assert context.user_id == 7
    assert context.session_id == "s1"
    assert context.file_context == "images=1 files=0"
    assert context.enable_search is True
    assert context.need_teaching_diagram is True
    assert context.diagram_mode == "requested"
    assert events[-1] == {"event": "done", "data": {"session_id": "s1", "full_response": "回答"}}


def test_chat_stream_rejects_invalid_history_json(monkeypatch) -> None:
    from app.chat import api

    class FakeUseCases:
        def default_session_id(self, user_id: int) -> str:
            return f"user-{user_id}-default-mentor"

    monkeypatch.setattr(api, "get_chat_usecases", lambda: FakeUseCases())

    response = asyncio.run(
        api.mentor_chat_stream(
            message=None,
            history="{not-json",
            session_id=None,
            attachments=None,
            need_teaching_diagram=False,
            generate_video=False,
            enable_search=False,
            enable_long_term_memory=False,
            current_user=SimpleNamespace(id=7),
        )
    )

    # HttpResponse.error() returns JSONResponse; decode body
    import json
    body = json.loads(response.body)
    assert body["code"] == 400
    assert "history 格式错误" in body["message"]


def test_chat_stream_parses_history_and_keeps_message_compatibility(monkeypatch) -> None:
    from app.chat import api

    captured: dict[str, Any] = {}

    class FakeUseCases:
        def default_session_id(self, user_id: int) -> str:
            return f"user-{user_id}-default-mentor"

        async def stream_chat(self, **kwargs: Any):
            captured.update(kwargs)
            yield "event: done\ndata: {}\n\n"

    monkeypatch.setattr(api, "get_chat_usecases", lambda: FakeUseCases())
    history = json.dumps(
        [
            {"role": "user", "content": "第一问"},
            {"role": "assistant", "content": "第一答"},
            {"role": "user", "content": "第二问"},
        ],
        ensure_ascii=False,
    )

    response = asyncio.run(
        api.mentor_chat_stream(
            message="兼容消息",
            history=history,
            session_id=None,
            attachments=None,
            need_teaching_diagram=True,
            generate_video=False,
            enable_search=False,
            enable_long_term_memory=False,
            current_user=SimpleNamespace(id=7),
        )
    )

    async def consume_response() -> None:
        async for _ in response.body_iterator:
            pass

    asyncio.run(consume_response())

    assert captured["user_message"] == "兼容消息"
    assert [item.content for item in captured["history"]] == ["第一问", "第一答", "第二问"]
    assert captured["session_id"] == "user-7-default-mentor"
    assert captured["need_teaching_diagram"] is True
