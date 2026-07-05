from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import AIMessage, ToolMessage

from app.chat.context_builder import normalize_tool_calls


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
