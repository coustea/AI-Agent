from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
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
    diagram: dict | None = None


class FakeMemoryLayer:
    calls: list[dict] = []

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name

    async def list_sessions(self, *, user_id: int, limit: int):
        return [FakeSession(id="s-1")]

    async def list_short_term_messages(self, **kwargs):
        self.calls.append(kwargs)
        return [
            FakeMessage(
                role="assistant",
                content="历史回答",
                created_at=datetime(2026, 4, 1, 8, 0),
            )
        ]


def test_chat_history_does_not_filter_out_expired_short_term_messages(monkeypatch):
    from app.chat import service

    FakeMemoryLayer.calls = []
    monkeypatch.setattr(service, "MemoryLayer", FakeMemoryLayer)

    store = service.ConversationStore()
    items = asyncio.run(store.get_history(user_id=7, session_id="s-1"))

    assert items[0].content == "历史回答"
    assert FakeMemoryLayer.calls[0]["only_unexpired"] is False
