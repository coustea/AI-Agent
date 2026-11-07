"""Chat 记忆模块测试 —— 压缩器、长期记忆与工具函数。"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.chat.memory import (
    LTM_CATEGORIES,
    LTM_CATEGORY_NAMES,
    ChatLongTermMemoryService,
    ChatSessionCompressor,
    MemoryUpdateOutput,
    compact_text,
    estimate_token_count,
    has_stable_signal,
    make_default_memory_markdown,
    now_utc,
)
from app.infra.llm import AIMessage
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock


class TestMemoryHelpers:
    def test_categories_and_markdown(self) -> None:
        assert len(LTM_CATEGORIES) == 7
        md = make_default_memory_markdown()
        for cat in LTM_CATEGORIES:
            assert LTM_CATEGORY_NAMES[cat] in md

    def test_token_and_compact(self) -> None:
        assert estimate_token_count("") == 0
        assert estimate_token_count("计算机网络 TCP 三次握手") >= 3
        assert compact_text("hello world", limit=6).endswith("...")
        assert now_utc().tzinfo is not None

    def test_stable_signal(self) -> None:
        assert has_stable_signal("好的") is False
        assert has_stable_signal("我总是记不住公式") is True
        assert has_stable_signal("我喜欢看图解") is True
        assert has_stable_signal("准备考研数学") is True
        assert MemoryUpdateOutput().need_update is False


class TestChatSessionCompressor:
    @pytest.mark.asyncio
    async def test_compress_invokes_rolling_prompt(self) -> None:
        c = ChatSessionCompressor(keep_recent=2, min_messages=3, min_tokens=100)
        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        prev_block = ChatSessionSummaryBlock(
            session_id="s1",
            block_index=1,
            summary_markdown="# 核心目标与意图\n- 学习 TCP",
            start_message_id=1,
            end_message_id=5,
        )
        now = datetime.now(timezone.utc)
        msgs = [
            ChatMessage(id=6, session_id="s1", role="user", content="三次握手是什么？", created_at=now),
            ChatMessage(id=7, session_id="s1", role="assistant", content="SYN, SYN-ACK, ACK", created_at=now),
            ChatMessage(id=8, session_id="s1", role="user", content="四次挥手呢？", created_at=now),
            ChatMessage(id=9, session_id="s1", role="assistant", content="FIN-ACK...", created_at=now),
        ]
        session_obj = ChatSession(id="s1", user_id=1, summary_token_count=500)

        mock_db.exec = AsyncMock(
            side_effect=[
                MagicMock(first=lambda: prev_block),
                MagicMock(all=lambda: msgs),
                MagicMock(first=lambda: session_obj),
            ]
        )

        captured_messages = []

        async def fake_text(messages, **kwargs):
            captured_messages.extend(messages)
            return AIMessage("```markdown\n# 核心目标与意图\n- 深入理解 TCP\n```")

        c.llm = MagicMock(text=fake_text)
        block = await c._compress(db=mock_db, user_id=1, session_id="s1")

        assert block is not None
        assert block.block_index == 2
        assert block.summary_markdown == "# 核心目标与意图\n- 深入理解 TCP"
        assert session_obj.summary_token_count == 0
        assert "上一阶段滚动状态摘要" in captured_messages[0].content


class TestChatLongTermMemoryService:
    def test_should_consider_update(self) -> None:
        svc = ChatLongTermMemoryService()
        assert svc.should_consider_update(user_message="我喜欢视频教学", assistant_reply="好的") is True
        assert svc.should_consider_update(user_message="hi", assistant_reply="以后我会注意讲解速度。") is True
        assert svc.should_consider_update(user_message="hi", assistant_reply="这是一道题") is False
