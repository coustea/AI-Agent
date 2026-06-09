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
    role: str
    content: str
    created_at: datetime
    attachments: list[dict] | None = None
    tool_calls: list[dict] | None = None
    knowledge_sources: list[dict] | None = None
    teaching_diagram: dict | None = None


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
                role="assistant",
                content="历史回答",
                created_at=datetime(2026, 4, 1, 8, 0),
                teaching_diagram={"type": "journey", "title": "握手过程"},
            )
        ]


def test_chat_history_does_not_filter_out_expired_short_term_messages(monkeypatch):
    from app.chat import service

    FakeMemoryService.calls = []
    monkeypatch.setattr(service, "MemoryService", FakeMemoryService)

    store = service.ConversationStore(memory_service=FakeMemoryService(module="mentor"))
    items = asyncio.run(store.get_history(user_id=7, session_id="s-1"))

    assert items[0].content == "历史回答"
    assert items[0].teaching_diagram == {"type": "journey", "title": "握手过程"}
    assert FakeMemoryService.calls[0]["only_unexpired"] is False


def test_chat_history_includes_knowledge_sources(monkeypatch):
    from app.chat import service

    class FakeMemoryServiceWithKnowledge(FakeMemoryService):
        async def list_messages(self, **kwargs):
            self.calls.append(kwargs)
            return [
                FakeMessage(
                    role="assistant",
                    content="answer",
                    created_at=datetime(2026, 4, 1, 8, 0),
                    knowledge_sources=[{"rank": 1, "source": "chapter1.md", "file_name": "chapter1.md"}],
                )
            ]

    FakeMemoryServiceWithKnowledge.calls = []
    monkeypatch.setattr(service, "MemoryService", FakeMemoryServiceWithKnowledge)

    store = service.ConversationStore(memory_service=FakeMemoryServiceWithKnowledge(module="mentor"))
    items = asyncio.run(store.get_history(user_id=7, session_id="s-1"))

    assert items[0].knowledge_sources == [{"rank": 1, "source": "chapter1.md", "file_name": "chapter1.md"}]
