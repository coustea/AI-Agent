"""Chat 记忆模块测试 —— 压缩器、长期记忆与工具函数。"""

from __future__ import annotations

from app.chat.memory import (
    LTM_CATEGORIES,
    LTM_CATEGORY_NAMES,
    MemoryUpdateOutput,
    compact_text,
    estimate_token_count,
    has_stable_signal,
    make_default_memory_markdown,
    now_utc,
)


class TestMemoryHelpers:
    def test_categories_and_markdown(self) -> None:
        """验证长期记忆分类与默认章节。"""
        assert len(LTM_CATEGORIES) == 7
        md = make_default_memory_markdown()
        for cat in LTM_CATEGORIES:
            assert LTM_CATEGORY_NAMES[cat] in md

    def test_token_and_compact(self) -> None:
        """验证文本计数、裁剪与时间格式。"""
        assert estimate_token_count("") == 0
        assert estimate_token_count("计算机网络 TCP 三次握手") >= 3
        assert compact_text("hello world", limit=6).endswith("...")
        assert now_utc().tzinfo is not None

    def test_stable_signal(self) -> None:
        """验证稳定偏好与学习目标的识别。"""
        assert has_stable_signal("好的") is False
        assert has_stable_signal("我总是记不住公式") is True
        assert has_stable_signal("我喜欢看图解") is True
        assert has_stable_signal("准备考研数学") is True
        assert MemoryUpdateOutput().need_update is False
