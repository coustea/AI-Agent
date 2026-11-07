from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@dataclass
class FakeSession:
    id: str


@dataclass
class FakeMessage:
    id: int
    role: str
    content: list[dict]
    created_at: datetime
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    run_id: str | None = None


class FakeMemoryService:
    calls: list[dict] = []

    def __init__(self, *, module: str) -> None:
        self.module = module

    async def list_sessions(self, *, user_id: int, limit: int):
        return [FakeSession(id="s-1")]

    async def list_messages(self, **kwargs):
        self.calls.append(kwargs)
        return [
            FakeMessage(
                id=1,
                role="assistant",
                content=[{"type": "text", "text": "历史回答"}],
                created_at=datetime(2026, 4, 1, 8, 0),
            )
        ]

    async def list_attachment_analyses(self, **kwargs):
        return []

    async def list_runs(self, **kwargs):
        return []


def test_chat_history_basic(monkeypatch):
    from app.chat import service

    FakeMemoryService.calls = []

    def fake_get_chat_memory_service():
        return FakeMemoryService(module="mentor")

    monkeypatch.setattr(service, "get_chat_memory_service", fake_get_chat_memory_service)

    use_cases = service.ChatUseCases()
    items = asyncio.run(use_cases.get_history(user_id=7, session_id="s-1"))

    assert items[0].content == [{"type": "text", "text": "历史回答"}]
    assert FakeMemoryService.calls[0].get("limit") == 50


def test_chat_history_includes_tool_messages(monkeypatch):
    from app.chat import service

    class FakeMemoryServiceWithTools(FakeMemoryService):
        async def list_messages(self, **kwargs):
            self.calls.append(kwargs)
            return [
                FakeMessage(
                    id=10,
                    role="assistant",
                    content=[{"type": "text", "text": "我先搜索一下"}],
                    created_at=datetime(2026, 4, 1, 8, 0),
                    tool_calls=[{"id": "call-search-1", "name": "tavily_search"}],
                ),
                FakeMessage(
                    id=11,
                    role="tool",
                    content=[{"type": "text", "text": "搜索结果摘要"}],
                    created_at=datetime(2026, 4, 1, 8, 0, 1),
                    tool_call_id="call-search-1",
                ),
            ]

    monkeypatch.setattr(service, "get_chat_memory_service", lambda: FakeMemoryServiceWithTools(module="mentor"))

    use_cases = service.ChatUseCases()
    items = asyncio.run(use_cases.get_history(user_id=7, session_id="s-1"))

    assert [item.role for item in items] == ["assistant", "tool"]
    assert items[0].tool_calls == [{"id": "call-search-1", "name": "tavily_search"}]
    tool_text_parts = [p for p in items[1].content if p.get("type") == "text"]
    assert any("搜索结果摘要" in p.get("text", "") for p in tool_text_parts)
    assert items[1].tool_call_id == "call-search-1"
