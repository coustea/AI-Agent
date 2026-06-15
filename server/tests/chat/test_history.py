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
    content: str
    created_at: datetime
    attachments: list[dict] | None = None
    tool_calls: list[dict] | None = None
    knowledge_sources: list[dict] | None = None
    teaching_diagram: dict | None = None
    turn_id: int | None = None
    tool_call_id: str | None = None
    message_kind: str | None = None


@dataclass
class FakeAttachmentAnalysis:
    id: int
    message_id: int
    file_id: int | None
    analysis_type: str
    summary_text: str
    file_name: str | None = None
    file_url: str | None = None
    extracted_text: str | None = None
    structured_json: dict | None = None


@dataclass
class FakeToolInvocation:
    id: int
    assistant_message_id: int | None
    tool_message_id: int | None
    tool_call_id: str
    tool_name: str
    result_text: str
    status: str = "success"


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
                content="历史回答",
                created_at=datetime(2026, 4, 1, 8, 0),
                teaching_diagram={"type": "journey", "title": "握手过程"},
            )
        ]

    async def list_attachment_analyses(self, *, user_id: int, session_id: str, limit: int = 20):
        return []

    async def list_tool_invocations(self, *, user_id: int, session_id: str, limit: int = 20):
        return []

    async def list_message_attachments(self, *, user_id: int, session_id: str, message_ids: list[int]):
        return {}


def test_chat_history_does_not_filter_out_expired_short_term_messages(monkeypatch):
    from app.chat import service

    FakeMemoryService.calls = []

    def fake_get_chat_memory_service():
        return FakeMemoryService(module="mentor")

    monkeypatch.setattr(service, "get_chat_memory_service", fake_get_chat_memory_service)

    use_cases = service.ChatUseCases()
    items = asyncio.run(use_cases.get_history(user_id=7, session_id="s-1"))

    assert items[0].content == "历史回答"
    assert items[0].teaching_diagram == {"type": "journey", "title": "握手过程"}
    assert FakeMemoryService.calls[0].get("limit") == 50


def test_chat_history_includes_knowledge_sources(monkeypatch):
    from app.chat import service

    class FakeMemoryServiceWithKnowledge(FakeMemoryService):
        async def list_messages(self, **kwargs):
            self.calls.append(kwargs)
            return [
                FakeMessage(
                    id=2,
                    role="assistant",
                    content="answer",
                    created_at=datetime(2026, 4, 1, 8, 0),
                    knowledge_sources=[{"rank": 1, "source": "chapter1.md", "file_name": "chapter1.md"}],
                )
            ]

    FakeMemoryServiceWithKnowledge.calls = []
    monkeypatch.setattr(service, "get_chat_memory_service", lambda: FakeMemoryServiceWithKnowledge(module="mentor"))

    use_cases = service.ChatUseCases()
    items = asyncio.run(use_cases.get_history(user_id=7, session_id="s-1"))

    assert items[0].knowledge_sources == [{"rank": 1, "source": "chapter1.md", "file_name": "chapter1.md"}]


def test_chat_history_includes_tool_messages_and_attachment_analyses(monkeypatch):
    from app.chat import service

    class FakeMemoryServiceWithExecution(FakeMemoryService):
        async def list_messages(self, **kwargs):
            self.calls.append(kwargs)
            return [
                FakeMessage(
                    id=10,
                    role="assistant",
                    content="我先搜索一下",
                    created_at=datetime(2026, 4, 1, 8, 0),
                    tool_calls=[{"id": "call-search-1", "name": "tavily_search"}],
                    turn_id=3,
                    message_kind="assistant_tool_request",
                ),
                FakeMessage(
                    id=11,
                    role="tool",
                    content="搜索结果摘要",
                    created_at=datetime(2026, 4, 1, 8, 0, 1),
                    tool_call_id="call-search-1",
                    turn_id=3,
                    message_kind="tool_result",
                ),
            ]

        async def list_attachment_analyses(self, *, user_id: int, session_id: str, limit: int = 20):
            return [
                FakeAttachmentAnalysis(
                    id=1,
                    message_id=10,
                    file_id=20,
                    file_name="circuit.png",
                    file_url="/api/v1/ai/chat/uploads/7/s-1/circuit.png",
                    analysis_type="vision",
                    summary_text="图片中是一道电路题，已标出关键元件。",
                    structured_json={"labels": ["R1", "R2"]},
                )
            ]

        async def list_tool_invocations(self, *, user_id: int, session_id: str, limit: int = 20):
            return [
                FakeToolInvocation(
                    id=1,
                    assistant_message_id=10,
                    tool_message_id=11,
                    tool_call_id="call-search-1",
                    tool_name="tavily_search",
                    result_text="搜索结果摘要",
                )
            ]

    monkeypatch.setattr(service, "get_chat_memory_service", lambda: FakeMemoryServiceWithExecution(module="mentor"))

    use_cases = service.ChatUseCases()
    items = asyncio.run(use_cases.get_history(user_id=7, session_id="s-1"))

    assert [item.role for item in items] == ["assistant", "tool"]
    assert items[0].tool_calls == [{"id": "call-search-1", "name": "tavily_search"}]
    assert items[1].content == "搜索结果摘要"
    assert items[1].tool_call_id == "call-search-1"
    assert items[0].attachment_analyses == [
        {
            "id": 1,
            "file_id": 20,
            "file_name": "circuit.png",
            "file_url": "/api/v1/ai/chat/uploads/7/s-1/circuit.png",
            "analysis_type": "vision",
            "summary_text": "图片中是一道电路题，已标出关键元件。",
            "structured_json": {"labels": ["R1", "R2"]},
        }
    ]


def test_chat_history_prefers_attachment_association_records(monkeypatch):
    from app.chat import service

    class FakeMemoryServiceWithBoundAttachments(FakeMemoryService):
        async def list_messages(self, **kwargs):
            self.calls.append(kwargs)
            return [
                FakeMessage(
                    id=21,
                    role="user",
                    content="请帮我看看这个附件",
                    created_at=datetime(2026, 4, 1, 8, 0),
                    attachments=None,
                )
            ]

        async def list_message_attachments(self, *, user_id: int, session_id: str, message_ids: list[int]):
            assert message_ids == [21]
            return {
                21: [
                    {
                        "file_id": 501,
                        "url": "/api/v1/ai/chat/uploads/7/s-1/diagram.png",
                        "type": "image",
                        "name": "diagram.png",
                        "mime_type": "image/png",
                        "extension": ".png",
                        "storage_key": "7/s-1/diagram.png",
                        "size_bytes": 1024,
                    }
                ]
            }

    monkeypatch.setattr(service, "get_chat_memory_service", lambda: FakeMemoryServiceWithBoundAttachments(module="mentor"))

    use_cases = service.ChatUseCases()
    items = asyncio.run(use_cases.get_history(user_id=7, session_id="s-1"))

    assert len(items) == 1
    assert items[0].attachments is not None
    assert items[0].attachments == [
        {
            "url": "/api/v1/ai/chat/uploads/7/s-1/diagram.png",
            "type": "image",
            "name": "diagram.png",
        }
    ]
