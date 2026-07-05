from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.utils import (
    extract_question,
    is_unusable_reply_text,
    normalize_message_content,
    truncate,
)


# ── normalize_message_content ──


class TestNormalizeMessageContent:
    def test_string_passthrough(self):
        assert normalize_message_content("hello") == "hello"

    def test_none_returns_empty(self):
        assert normalize_message_content(None) == ""

    def test_non_string_strified(self):
        assert normalize_message_content(42) == "42"

    def test_list_strified(self):
        result = normalize_message_content([{"text": "a"}])
        assert isinstance(result, str)


# ── truncate ──


class TestTruncate:
    def test_short(self):
        assert truncate("hi", 100) == "hi"

    def test_long(self):
        result = truncate("hello world", 10)
        assert len(result) <= 13
        assert result.endswith("...")

    def test_newlines_normalized(self):
        result = truncate("a\nb\nc", 100)
        assert "\n" not in result

    def test_non_string(self):
        result = truncate({"key": "val"}, 50)
        assert "key" in result


# ── is_unusable_reply_text ──


class TestIsUnusableReplyText:
    def test_empty(self):
        assert is_unusable_reply_text("") is True

    def test_whitespace(self):
        assert is_unusable_reply_text("   ") is True

    def test_timestamp_markers(self):
        assert is_unusable_reply_text("生成时间：") is True
        assert is_unusable_reply_text("生成时间:2024-01-01") is True
        assert is_unusable_reply_text("更新时间：") is True

    def test_short_text(self):
        assert is_unusable_reply_text("短") is True
        assert is_unusable_reply_text("1234567") is True

    def test_valid_text(self):
        assert is_unusable_reply_text("这是一个有效的回答内容。") is False


# ── extract_question ──


class TestExtractQuestion:
    def test_no_human_messages(self):
        msgs = [SystemMessage(content="system")]
        assert extract_question(msgs) == ""

    def test_simple_question(self):
        msgs = [HumanMessage(content="什么是TCP？")]
        assert extract_question(msgs) == "什么是TCP？"

    def test_with_images_attachment(self):
        msgs = [HumanMessage(content="解释这张图 [Attached Images: /api/.../pic.png]")]
        result = extract_question(msgs)
        assert "[Attached" not in result
        assert "解释这张图" in result

    def test_with_files_attachment(self):
        msgs = [HumanMessage(content="看看这个 [Attached Files: /api/.../doc.pdf]")]
        result = extract_question(msgs)
        assert "[Attached" not in result

    def test_multiple_messages_takes_last(self):
        msgs = [
            HumanMessage(content="第一个问题"),
            HumanMessage(content="第二个问题"),
        ]
        assert extract_question(msgs) == "第二个问题"
