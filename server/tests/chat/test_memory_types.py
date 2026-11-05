from __future__ import annotations

import pytest

from app.chat.memory.types import (
    DIALOGUE_ROLES,
    LTM_CATEGORIES,
    LTM_CATEGORY_NAMES,
    STABLE_SIGNAL_PATTERNS,
    MemoryUpdateOutput,
    compact_text,
    estimate_token_count,
    has_stable_signal,
    make_default_memory_markdown,
    now,
)


# ── Constants ──


class TestConstants:
    def test_dialogue_roles(self):
        assert "user" in DIALOGUE_ROLES
        assert "assistant" in DIALOGUE_ROLES
        assert "system" not in DIALOGUE_ROLES

    def test_ltm_categories_count(self):
        assert len(LTM_CATEGORIES) == 7

    def test_ltm_category_names_cover_all(self):
        for cat in LTM_CATEGORIES:
            assert cat in LTM_CATEGORY_NAMES


# ── now() ──


class TestNow:
    def test_returns_utc(self):
        dt = now()
        assert dt.tzinfo is not None


# ── estimate_token_count ──


class TestEstimateTokenCount:
    def test_empty(self):
        assert estimate_token_count("") == 0

    def test_whitespace(self):
        assert estimate_token_count("   ") == 0

    def test_short_text(self):
        count = estimate_token_count("hello")
        assert count >= 1

    def test_chinese_text(self):
        count = estimate_token_count("计算机网络")
        assert count >= 1

    def test_long_text(self):
        text = "word " * 100
        count = estimate_token_count(text)
        assert count > 50


# ── compact_text ──


class TestCompactText:
    def test_short_not_truncated(self):
        assert compact_text("hello", limit=100) == "hello"

    def test_long_truncated(self):
        result = compact_text("hello world", limit=5)
        assert len(result) <= 5
        assert result.endswith("...")

    def test_empty(self):
        assert compact_text("", limit=10) == ""


# ── make_default_memory_markdown ──


class TestMakeDefaultMemoryMarkdown:
    def test_contains_all_categories(self):
        md = make_default_memory_markdown()
        assert "长期记忆" in md
        for cat in LTM_CATEGORIES:
            name = LTM_CATEGORY_NAMES[cat]
            assert name in md


# ── has_stable_signal ──


class TestHasStableSignal:
    def test_empty(self):
        assert has_stable_signal("") is False

    def test_non_significant(self):
        assert has_stable_signal("好的") is False
        assert has_stable_signal("谢谢") is False
        assert has_stable_signal("收到") is False

    def test_repeated_problem(self):
        assert has_stable_signal("我总是出错") is True
        assert has_stable_signal("经常记不住公式") is True

    def test_preference(self):
        assert has_stable_signal("我喜欢视频教学") is True
        assert has_stable_signal("不喜欢太长的回答") is True

    def test_goal(self):
        assert has_stable_signal("准备考研数学") is True

    def test_background(self):
        assert has_stable_signal("我的专业是计算机") is True

    def test_normal_text(self):
        assert has_stable_signal("请帮我解释一下TCP三次握手") is False


# ── MemoryUpdateOutput ──


class TestMemoryUpdateOutput:
    def test_defaults(self):
        m = MemoryUpdateOutput()
        assert m.need_update is False
        assert m.memory_markdown is None
        assert m.confidence == 0.75

    def test_custom(self):
        m = MemoryUpdateOutput(need_update=True, memory_markdown="# LTM", confidence=0.9)
        assert m.need_update is True
        assert m.memory_markdown == "# LTM"
