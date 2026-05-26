"""Tests for TutorAgent internal nodes and chat_stream.

The TutorAgent has been refactored to use LangGraph orchestration.
These tests verify the key node methods, constants, and schemas.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import TutorAgentContext


def _make_context(**overrides: Any) -> TutorAgentContext:
    """Create a minimal TutorAgentContext with sensible defaults."""
    defaults = {
        "user_id": 7,
        "session_id": "session-1",
        "system_prompt": "system",
        "profile_context": "profile",
        "long_term_memory_context": "memory",
        "session_summary_context": "summary",
        "recent_chat_context": "recent",
        "file_context": "files",
        "attachment_analysis_context": "",
    }
    defaults.update(overrides)
    return TutorAgentContext(**defaults)


def test_tutor_agent_init_stores_context():
    """TutorAgent.__init__ stores the provided context and creates llm."""
    from app.chat.agent import TutorAgent

    context = _make_context()
    agent = TutorAgent(context)

    assert agent.context is context
    assert agent.context.user_id == 7
    assert agent.context.session_id == "session-1"


def test_classify_node_routes_attachment_with_search(monkeypatch):
    """_classify_node routes attachment+search to search path."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context())

    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="结合附件和最新资料解释 Transformer")],
        "file_urls": ["/uploads/transformer.pdf"],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert result["route"] == "search"
    assert result["execution_mode"] == "search"


def test_classify_node_routes_direct_when_no_search_no_attachments(monkeypatch):
    """_classify_node routes to direct when no search and no attachments."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context(enable_search=False))

    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="什么是 TCP 三次握手？")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert result["route"] == "direct"
    assert result["execution_mode"] == "direct"


def test_classify_node_routes_search_for_fresh_information_request(monkeypatch):
    """_classify_node routes fresh-information requests to search deterministically."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context(enable_search=False))

    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="最新AI新闻有哪些？")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert result["route"] == "search"
    assert result["execution_mode"] == "search"


def test_classify_node_does_not_enable_diagram_for_concept_question():
    """A concept question must not gain a diagram without an explicit request."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context())
    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="文件管理的核心机制是什么？")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert "need_teaching_diagram" not in result


def test_classify_node_enables_diagram_for_explicit_user_request():
    """Explicit visualization wording activates a teaching diagram."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context())
    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="请用图解说明文件管理流程")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert result["need_teaching_diagram"] is True


def test_classify_node_keeps_frontend_diagram_selection_enabled():
    """The UI switch remains an authoritative explicit request."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context())
    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="文件管理是什么？")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": True,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert "need_teaching_diagram" not in result


def test_teaching_diagram_generate_node_exists():
    """Verify _teaching_diagram_generate_node method exists on TutorAgent."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context())
    assert hasattr(agent, "_teaching_diagram_generate_node")
    assert callable(getattr(agent, "_teaching_diagram_generate_node"))


def test_graph_node_names_include_all_current_nodes():
    """Verify GRAPH_NODE_NAMES includes all nodes in the current workflow."""
    from app.chat.agent import GRAPH_NODE_NAMES

    expected = {"classify", "direct_answer", "search_node", "spark_summary", "attachment_answer", "teaching_diagram_generate"}
    assert GRAPH_NODE_NAMES == expected


def test_answer_node_names_subset_of_graph_node_names():
    """ANSWER_NODE_NAMES should be a subset of GRAPH_NODE_NAMES."""
    from app.chat.agent import ANSWER_NODE_NAMES, GRAPH_NODE_NAMES

    assert ANSWER_NODE_NAMES <= GRAPH_NODE_NAMES
    assert ANSWER_NODE_NAMES == {"direct_answer", "spark_summary", "attachment_answer"}


def test_routing_no_longer_defines_llm_intent_schema():
    """Routing is deterministic and does not maintain an LLM classifier schema."""
    from app.chat import agent as agent_module

    assert not hasattr(agent_module, "Intent")


def test_chat_stream_signature():
    """Verify chat_stream accepts history parameter."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context())
    # Verify chat_stream method exists and accepts history
    assert hasattr(agent, "chat_stream")
    import inspect
    sig = inspect.signature(agent.chat_stream)
    assert "history" in sig.parameters
    # chat_stream should NOT require image_urls or file_urls as parameters
    assert "image_urls" not in sig.parameters
    assert "file_urls" not in sig.parameters


def test_classify_node_skips_llm_route_call_for_stable_concept_question():
    """Stable learning questions must not pay for a model classification round trip."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context(enable_search=False))
    agent.llm.ainvoke_json = AsyncMock()
    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="操作系统中的处理机调度是什么？")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert result["route"] == "direct"
    agent.llm.ainvoke_json.assert_not_awaited()


def test_classify_node_detects_explicit_fresh_information_without_llm():
    """Fresh-information wording deterministically enables the search path."""
    from app.chat.agent import TutorAgent

    agent = TutorAgent(_make_context(enable_search=False))
    agent.llm.ainvoke_json = AsyncMock()
    state = {
        "user_id": 7,
        "session_id": "session-1",
        "messages": [HumanMessage(content="请查一下今天最新发布的 Linux 调度更新")],
        "file_urls": [],
        "image_urls": [],
        "enable_search": False,
        "need_teaching_diagram": False,
        "resource_mode": "none",
    }

    import asyncio
    result = asyncio.run(agent._classify_node(state))

    assert result["route"] == "search"
    assert result["enable_search"] is True
    agent.llm.ainvoke_json.assert_not_awaited()


def test_chat_stream_emits_incremental_answer_tokens_from_streaming_llm():
    """The UI receives chunks without truncating the teaching response budget."""
    from app.chat.agent import TutorAgent

    class StreamingLLM:
        def __init__(self) -> None:
            self.stream_kwargs = []

        def bind_tools(self, tools: Any, **kwargs: Any) -> "StreamingLLM":
            return self

        async def astream(self, *_args, **kwargs):
            self.stream_kwargs.append(kwargs)
            yield AIMessageChunk(content="处理机调度")
            yield AIMessageChunk(content="负责分配 CPU 时间。")

        async def ainvoke(self, *_args, **_kwargs):
            raise AssertionError("answer path must stream instead of waiting for ainvoke")

    async def collect_events():
        agent = TutorAgent(_make_context(enable_search=False))
        streaming_llm = StreamingLLM()
        agent.llm = streaming_llm
        events = [
            event
            async for event in agent.chat_stream(
                [ChatHistoryMessage(role="user", content="处理机调度是什么？")]
            )
        ]
        return events, streaming_llm

    import asyncio
    events, streaming_llm = asyncio.run(collect_events())
    token_values = [event["data"] for event in events if event["event"] == "token"]

    assert token_values == ["处理机调度", "负责分配 CPU 时间。"]
    assert events[-1]["data"]["full_response"] == "处理机调度负责分配 CPU 时间。"
    assert "max_tokens" not in streaming_llm.stream_kwargs[0]
