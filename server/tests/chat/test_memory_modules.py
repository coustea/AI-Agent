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
