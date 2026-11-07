"""Chat 历史消息组装与上传服务测试（验证过滤中间 tool/tool_calls 消息与无 N+1 快照组装）。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.chat import service
from app.infra.models import ChatMessage, ChatRun as ChatRunRow


@pytest.mark.asyncio
async def test_get_history_filters_tool_messages_and_attaches_run_state(monkeypatch) -> None:
    now = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    raw_messages = [
        ChatMessage(
            id=1,
            session_id="s-1",
            role="user",
            content=[{"type": "text", "text": "什么是三次握手？"}],
            created_at=now,
        ),
        ChatMessage(
            id=2,
            session_id="s-1",
            run_id="r-1",
            role="assistant",
            content=[],
            tool_calls=[{"id": "c1", "name": "knowledge_search", "args": {"query": "三次握手"}}],
            created_at=now,
        ),
        ChatMessage(
            id=3,
            session_id="s-1",
            run_id="r-1",
            role="tool",
            content=[{"type": "text", "text": "内部工具输出不应展示给用户气泡"}],
            tool_call_id="c1",
            created_at=now,
        ),
        ChatMessage(
            id=4,
            session_id="s-1",
            run_id="r-1",
            role="assistant",
            content=[{"type": "text", "text": "三次握手包含 SYN、SYN-ACK、ACK。"}],
            created_at=now,
        ),
    ]
    raw_runs = [
        ChatRunRow(
            id="r-1",
            session_id="s-1",
            user_id=7,
            user_message_id=1,
            status="completed",
            phase="completed",
            phase_label="回答完成",
            content="三次握手包含 SYN、SYN-ACK、ACK。",
            total_elapsed_ms=1200,
            steps=[
                {
                    "step_id": "tool:c1",
                    "kind": "knowledge",
                    "title": "检索课程知识库",
                    "subtitle": "检索关键词：三次握手",
                    "status": "completed",
                    "elapsed_ms": 400,
                }
            ],
            created_at=now,
        )
    ]

    exec_mock = AsyncMock(
        side_effect=[
            SimpleNamespace(all=lambda: list(reversed(raw_messages))),
            SimpleNamespace(all=lambda: raw_runs),
        ]
    )

    @asynccontextmanager
    async def _fake_scope():
        yield SimpleNamespace(exec=exec_mock)

    monkeypatch.setattr(service, "session_scope", _fake_scope)

    items = await service.get_history(user_id=7, session_id="s-1", limit=50)
    # 中间带 tool_calls 的 assistant 与 role="tool" 消息均被过滤，仅剩 user + 最终 assistant
    assert [item.role for item in items] == ["user", "assistant"]
    assert items[0].id == 1
    assert items[1].id == 4
    assert items[1].run is not None
    assert items[1].run["status"] == "completed"
    assert len(items[1].run["steps"]) == 1
    assert items[1].run["steps"][0]["title"] == "检索课程知识库"
