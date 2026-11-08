from __future__ import annotations

from app.infra.llm import AIMessage, HumanMessage, ToolMessage

from app.chat.context import convert_stored_message, prune_tool_messages
from app.infra.models import ChatMessage


def test_stored_tool_calls_restore_transcript() -> None:
    """持久化的工具调用应恢复为完整模型消息。"""
    message = convert_stored_message(ChatMessage(
        session_id="s1", role="assistant", content=[],
        tool_calls=[{"id": "call-1", "name": "grep", "args": {"pattern": "TCP"}}],
    ))
    assert message is not None
    assert message.tool_calls[0].id == "call-1"
    assert message.tool_calls[0].name == "grep"
    assert message.tool_calls[0].args == {"pattern": "TCP"}


def test_empty_assistant_is_omitted() -> None:
    """无文本且无工具调用的消息不进入模型上下文。"""
    assert convert_stored_message(ChatMessage(session_id="s1", role="assistant", content=[])) is None


def test_prune_tool_messages_retention_and_truncation() -> None:
    """旧工具输出裁剪后保留调用标识和近期原文。"""
    long_content = "X" * 500
    short_content = "Short output"

    messages = [
        HumanMessage("Turn 1: User asks question"),
        AIMessage("Let me search", tool_calls=[]),
        ToolMessage(content=long_content, tool_call_id="call-old-1"),
        HumanMessage("Turn 2: Followup question"),
        AIMessage("Let me check", tool_calls=[]),
        ToolMessage(content=short_content, tool_call_id="call-mid-1"),
        HumanMessage("Turn 3: Latest question"),
        AIMessage("Searching again", tool_calls=[]),
        ToolMessage(content=long_content, tool_call_id="call-new-1"),
    ]

    # keep_recent_turns = 2: Turn 2 and Turn 3 are recent.
    # Turn 1's ToolMessage is older than recent 2 turns and length > 300 -> pruned!
    # Turn 2's ToolMessage is recent and <= 300 -> intact
    # Turn 3's ToolMessage is recent -> intact
    pruned = prune_tool_messages(messages, keep_recent_turns=2, max_chars=300)

    assert len(pruned) == len(messages)
    # Old turn pruned:
    assert "[Tool output pruned: 原始长 500 字符" in pruned[2].content
    assert pruned[2].tool_call_id == "call-old-1"
    # Mid turn intact:
    assert pruned[5].content == short_content
    # Recent turn intact despite being long:
    assert pruned[8].content == long_content


def test_prune_tool_messages_keep_all_when_within_turn_limit() -> None:
    """短会话的工具输出保持原文。"""
    long_content = "Y" * 600
    messages = [
        HumanMessage("Turn 1"),
        ToolMessage(content=long_content, tool_call_id="c1"),
    ]
    pruned = prune_tool_messages(messages, keep_recent_turns=2, max_chars=300)
    assert pruned[1].content == long_content
