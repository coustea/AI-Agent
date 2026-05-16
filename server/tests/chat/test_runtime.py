from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.runtime import prepare_tutor_turn
from app.chat.agent import TutorAgent


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

    async def ainvoke(
        self,
        model_type: str,
        messages: list[Any],
        *,
        model_kwargs: dict[str, Any] | None = None,
    ) -> AIMessage:
        self.calls.append(messages)
        return AIMessage(content="这是搜索后的总结回答")


@pytest.mark.asyncio
async def test_prepare_tutor_turn_carries_need_diagram_state() -> None:
    prepared = await prepare_tutor_turn(
        ctx_service=FakeTutorContextService(),
        prompts={
            "tutor_system": (
                "profile={profile_context} fact={fact_context} recent={recent_chat_context}"
            )
        },
        user_id=7,
        user_message="Explain TCP handshakes",
        session_id=None,
        image_urls=None,
        file_urls=None,
        enable_search=False,
        enable_long_term_memory=True,
        attachment_analysis=None,
        need_diagram=True,
    )

    assert prepared.initial_state["need_diagram"] is True
    assert prepared.initial_state["diagram"] is None
    assert prepared.initial_state["diagram_error"] is None
    assert prepared.initial_state["system_prompt"] == "profile=profile:7 fact=facts:7 recent=recent context"


@pytest.mark.asyncio
async def test_prepare_tutor_turn_skips_long_term_context_when_memory_disabled() -> None:
    ctx = FakeTutorContextService()

    prepared = await prepare_tutor_turn(
        ctx_service=ctx,
        prompts={
            "tutor_system": (
                "profile={profile_context} fact={fact_context} recent={recent_chat_context}"
            )
        },
        user_id=7,
        user_message="Explain TCP handshakes",
        session_id=None,
        image_urls=None,
        file_urls=None,
        enable_search=False,
        enable_long_term_memory=False,
        attachment_analysis=None,
        need_diagram=False,
    )

    assert ctx.long_term_context_calls == 0
    assert prepared.initial_state["fact_context"] == "长期记忆未启用。"
    assert "fact=长期记忆未启用。" in prepared.initial_state["system_prompt"]


@pytest.mark.asyncio
async def test_search_summary_uses_unified_tutor_system_prompt() -> None:
    llm_manager = CapturingLlmManager()
    agent = TutorAgent.__new__(TutorAgent)
    agent.llm_manager = llm_manager
    agent.spark_model_kwargs = {"temperature": 0.7, "streaming": True}

    result = await agent._spark_summary_node(
        {
            "user_id": 7,
            "session_id": "session-1",
            "messages": [HumanMessage(content="TCP 三次握手是什么？")],
            "search_result": "搜索结果：TCP handshake uses SYN, SYN-ACK, ACK.",
            "system_prompt": "统一教学 prompt，包含 profile=profile:7 fact=facts:7 recent=recent context",
        }
    )

    assert result["answer_text"] == "这是搜索后的总结回答"
    first_call = llm_manager.calls[0]
    assert isinstance(first_call[0], SystemMessage)
    assert "统一教学 prompt" in first_call[0].content
    assert "profile=profile:7" in first_call[0].content


@pytest.mark.asyncio
async def test_classify_routes_attachment_with_search_to_search_path() -> None:
    agent = TutorAgent.__new__(TutorAgent)

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

    assert result == {"route": "search", "execution_mode": "attachment_search"}
