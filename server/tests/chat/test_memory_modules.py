from __future__ import annotations

import pytest

from app.chat.memory.compression import ChatSessionCompressor
from app.chat.memory.long_term import ChatLongTermMemoryService


class TestChatSessionCompressor:
    def test_init_defaults(self):
        c = ChatSessionCompressor()
        assert c.keep_recent == 8
        assert c.min_messages == 14
        assert c.min_tokens == 3500

    def test_init_custom(self):
        c = ChatSessionCompressor(keep_recent=4, min_messages=10, min_tokens=2000)
        assert c.keep_recent == 4
        assert c.min_messages == 10
        assert c.min_tokens == 2000

    @pytest.mark.asyncio
    async def test_compress_invokes_rolling_prompt(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock
        from datetime import datetime, timezone
        from app.infra.llm import AIMessage
        from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock

        c = ChatSessionCompressor(keep_recent=2, min_messages=3, min_tokens=100)

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        # Mock latest_block query -> returns existing block
        prev_block = ChatSessionSummaryBlock(
            session_id="s1",
            block_index=1,
            summary_markdown="# 核心目标与意图\n- 学习 TCP",
            start_message_id=1,
            end_message_id=5,
        )
        # 1st exec: latest_block; 2nd exec: messages; 3rd exec: chat_session
        msg1 = ChatMessage(id=6, session_id="s1", role="user", content="三次握手是什么？", created_at=datetime.now(timezone.utc))
        msg2 = ChatMessage(id=7, session_id="s1", role="assistant", content="三次握手包括 SYN, SYN-ACK, ACK", created_at=datetime.now(timezone.utc))
        msg3 = ChatMessage(id=8, session_id="s1", role="user", content="那四次挥手呢？", created_at=datetime.now(timezone.utc))
        msg4 = ChatMessage(id=9, session_id="s1", role="assistant", content="四次挥手...", created_at=datetime.now(timezone.utc))

        session_obj = ChatSession(id="s1", user_id=1, summary_token_count=500)

        mock_exec = AsyncMock()
        mock_exec.side_effect = [
            MagicMock(first=lambda: prev_block),  # latest_block
            MagicMock(all=lambda: [msg1, msg2, msg3, msg4]),  # messages
            MagicMock(first=lambda: session_obj),  # chat_session
        ]
        mock_db.exec = mock_exec

        captured_messages = []
        async def fake_text(messages, **kwargs):
            captured_messages.extend(messages)
            return AIMessage("```markdown\n# 核心目标与意图\n- 深入理解 TCP\n```")

        mock_llm = MagicMock()
        mock_llm.text = fake_text
        c.llm = mock_llm

        block = await c._compress(db=mock_db, user_id=1, session_id="s1")

        assert block is not None
        assert block.block_index == 2
        # Verify markdown fences were cleanly stripped
        assert block.summary_markdown == "# 核心目标与意图\n- 深入理解 TCP"
        assert session_obj.summary_token_count == 0
        # Verify prompt had previous_summary and dialogue
        prompt_content = captured_messages[0].content
        assert "上一阶段滚动状态摘要" in prompt_content
        assert "学习 TCP" in prompt_content


class TestChatLongTermMemoryService:
    def test_init_defaults(self):
        svc = ChatLongTermMemoryService()
        assert svc.min_confidence == 0.75
        assert svc.cooldown_seconds == 1800

    def test_init_custom(self):
        svc = ChatLongTermMemoryService(
            min_confidence=0.8,
            cooldown_minutes=60,
        )
        assert svc.min_confidence == 0.8
        assert svc.cooldown_seconds == 3600

    def test_should_consider_update_user_signal(self):
        svc = ChatLongTermMemoryService()
        assert svc.should_consider_update(
            user_message="我喜欢视频教学",
            assistant_reply="好的",
        ) is True

    def test_should_consider_update_assistant_signal(self):
        svc = ChatLongTermMemoryService()
        assert svc.should_consider_update(
            user_message="hello",
            assistant_reply="以后我会注意讲解速度。",
        ) is True

    def test_should_consider_update_no_signal(self):
        svc = ChatLongTermMemoryService()
        assert svc.should_consider_update(
            user_message="hello",
            assistant_reply="好的，这是一道数学题。",
        ) is False

    def test_should_consider_update_empty(self):
        svc = ChatLongTermMemoryService()
        assert svc.should_consider_update(
            user_message="",
            assistant_reply="",
        ) is False
