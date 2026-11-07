from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.infra.llm import AIMessage, HumanMessage, ToolMessage

from app.chat.context import normalize_tool_calls, prune_tool_messages


def testnormalize_tool_calls_restores_tool_transcript():
    tool_calls = [{"id": "call-search-1", "name": "tavily_search", "args": {"query": "TCP"}, "type": "tool_call"}]
    normalized = normalize_tool_calls(tool_calls)

    assert len(normalized) == 1
    assert normalized[0]["id"] == "call-search-1"
    assert normalized[0]["name"] == "tavily_search"
    assert normalized[0]["args"] == {"query": "TCP"}
    assert normalized[0]["type"] == "tool_call"


def testnormalize_tool_calls_handles_none_and_empty():
    assert normalize_tool_calls(None) == []
    assert normalize_tool_calls([]) == []


def testnormalize_tool_calls_skips_non_dict():
    result = normalize_tool_calls(["not a dict", 42])
    assert result == []


def test_prune_tool_messages_retention_and_truncation():
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


def test_prune_tool_messages_keep_all_when_within_turn_limit():
    long_content = "Y" * 600
    messages = [
        HumanMessage("Turn 1"),
        ToolMessage(content=long_content, tool_call_id="c1"),
    ]
    pruned = prune_tool_messages(messages, keep_recent_turns=2, max_chars=300)
    assert pruned[1].content == long_content
