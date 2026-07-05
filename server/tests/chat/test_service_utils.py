from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from app.chat.streaming import ContentSafetyFilter, SafetyResult
from app.chat.context_builder import normalize_tool_calls
from app.chat.service import (
    ChatMessageItem,
)
from app.chat.storage.file_store import LocalFileStore, _guess_mime_type


# ── normalize_tool_calls ──


class TestNormalizeToolCalls:
    def test_none_input(self):
        assert normalize_tool_calls(None) == []

    def test_empty_list(self):
        assert normalize_tool_calls([]) == []

    def test_normalizes_valid(self):
        result = normalize_tool_calls([{"id": "c1", "name": "search", "args": {"q": "x"}}])
        assert len(result) == 1
        assert result[0]["id"] == "c1"
        assert result[0]["name"] == "search"
        assert result[0]["args"] == {"q": "x"}
        assert result[0]["type"] == "tool_call"

    def test_missing_fields(self):
        result = normalize_tool_calls([{}])
        assert result[0]["id"] == ""
        assert result[0]["name"] == ""
        assert result[0]["args"] == {}

    def test_non_dict_skipped(self):
        result = normalize_tool_calls(["bad", 42])
        assert result == []

    def test_args_not_dict(self):
        result = normalize_tool_calls([{"id": "1", "name": "x", "args": "bad"}])
        assert result[0]["args"] == {}


# ── _guess_mime_type ──


class TestGuessMimeType:
    def test_known_types(self):
        assert _guess_mime_type(".png") == "image/png"
        assert _guess_mime_type(".jpg") == "image/jpeg"
        assert _guess_mime_type(".pdf") == "application/pdf"
        assert _guess_mime_type(".txt") == "text/plain"
        assert _guess_mime_type(".docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert _guess_mime_type(".csv") == "text/csv"

    def test_unknown_type(self):
        assert _guess_mime_type(".xyz") == "application/octet-stream"

    def test_empty(self):
        assert _guess_mime_type("") == "application/octet-stream"


# ── ContentSafetyFilter ──


class TestContentSafetyFilter:
    def setup_method(self):
        self.f = ContentSafetyFilter()

    def test_empty_safety_terms(self):
        """安全配置为空时不报错 (section 11.1)"""
        import app.chat.streaming as chat_streaming
        prev = list(chat_streaming.SAFETY_SENSITIVE_TERMS)
        try:
            chat_streaming.SAFETY_SENSITIVE_TERMS = ()
            f = ContentSafetyFilter()
            assert f.sensitive_patterns == []
            assert f.stream_guard_chars == 0
        finally:
            chat_streaming.SAFETY_SENSITIVE_TERMS = tuple(prev)

    @pytest.mark.asyncio
    async def test_clean_text(self):
        result = await self.f.check("这是一段正常的文本。")
        assert result.has_violation is False
        assert result.sanitized_text == "这是一段正常的文本。"

    @pytest.mark.asyncio
    async def test_empty_text(self):
        result = await self.f.check("")
        assert result.has_violation is False
        assert result.sanitized_text == ""

    @pytest.mark.asyncio
    async def test_sensitive_term_replaced(self):
        result = await self.f.check("这里有色情内容")
        assert result.has_violation is True
        assert "色情" not in result.sanitized_text
        assert "***" in result.sanitized_text

    @pytest.mark.asyncio
    async def test_multiple_sensitive_terms(self):
        result = await self.f.check("赌博和毒品都不好")
        assert result.has_violation is True
        assert "赌博" not in result.sanitized_text
        assert "毒品" not in result.sanitized_text

    @pytest.mark.asyncio
    async def test_violation_no_sanitization_needed(self):
        result = await self.f.check("暴力是不对的")
        assert result.has_violation is True
        assert "暴力" not in result.sanitized_text

    def test_guard_chars_positive(self):
        assert self.f.stream_guard_chars >= 1

    def test_sensitive_patterns_compiled(self):
        assert len(self.f.sensitive_patterns) >= 1


# ── ChatMessageItem ──


class TestChatMessageItem:
    def test_minimal(self):
        item = ChatMessageItem(id=1, role="user", content=[{"type": "text", "text": "hello"}])
        assert item.id == 1
        assert item.role == "user"
        assert item.content == [{"type": "text", "text": "hello"}]

    def test_model_dump_minimal(self):
        item = ChatMessageItem(id=1, role="user", content=[{"type": "text", "text": "hello"}])
        d = item.model_dump()
        assert d == {"id": 1, "role": "user", "content": [{"type": "text", "text": "hello"}], "created_at": None}

    def test_model_dump_with_tool_calls(self):
        item = ChatMessageItem(
            id=1,
            role="assistant",
            content=[{"type": "text", "text": "answer"}],
            tool_calls=[{"id": "c1", "name": "search"}],
        )
        d = item.model_dump()
        assert "tool_calls" in d
        assert len(d["tool_calls"]) == 1

    def test_model_dump_full(self):
        item = ChatMessageItem(
            id=1,
            role="assistant",
            content=[{"type": "text", "text": "answer"}],
            tool_calls=[{"id": "c1", "name": "search"}],
            tool_call_id=None,
            created_at="2026-01-01",
        )
        d = item.model_dump()
        assert d["tool_calls"] == [{"id": "c1", "name": "search"}]
        assert d["created_at"] == "2026-01-01"


# ── LocalFileStore ──


class TestLocalFileStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = LocalFileStore()
        self.store.upload_dir = Path(self.tmpdir)

    def test_list_files_empty(self):
        files = self.store.list_files(user_id=1, session_id="s1")
        assert files == []

    @pytest.mark.asyncio
    async def test_save_txt_file(self):
        result = await self.store.save_upload(
            filename="test.txt",
            content=b"hello world",
            user_id=1,
            session_id="s1",
        )
        assert result["file_type"] == "document"
        assert result["original_name"] == "test.txt"
        assert result["size_bytes"] == 11
        assert result["extension"] == ".txt"
        files = self.store.list_files(user_id=1, session_id="s1")
        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_save_image_file(self):
        result = await self.store.save_upload(
            filename="pic.png",
            content=b"\x89PNG\r\n",
            user_id=1,
            session_id="s1",
        )
        assert result["file_type"] == "image"
        assert result["mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_save_unsupported_extension(self):
        with pytest.raises(ValueError, match="不支持的文件类型"):
            await self.store.save_upload(
                filename="file.exe",
                content=b"bad",
                user_id=1,
                session_id="s1",
            )

    @pytest.mark.asyncio
    async def test_save_image_too_large(self):
        with pytest.raises(ValueError, match="文件大小超过限制"):
            await self.store.save_upload(
                filename="big.png",
                content=b"x" * (5 * 1024 * 1024 + 1),
                user_id=1,
                session_id="s1",
            )

    @pytest.mark.asyncio
    async def test_save_doc_too_large(self):
        with pytest.raises(ValueError, match="文件大小超过限制"):
            await self.store.save_upload(
                filename="big.pdf",
                content=b"x" * (10 * 1024 * 1024 + 1),
                user_id=1,
                session_id="s1",
            )

    def test_safe_filename(self):
        assert self.store._safe_filename("normal.txt") == "normal.txt"
        assert self.store._safe_filename("a/b.txt") == "ab.txt"
        assert self.store._safe_filename('a<>b.txt') == "ab.txt"
        long_name = "a" * 200 + ".txt"
        safe = self.store._safe_filename(long_name)
        assert len(safe) <= 100

    def test_safe_filename_empty_after_strip(self):
        result = self.store._safe_filename("///")
        assert result == "" or len(result) > 0

    def test_resolve_user_file_permission_error(self):
        with pytest.raises(PermissionError):
            self.store.resolve_user_file(
                current_user_id=1,
                owner_id=2,
                session_id="s1",
                filename="test.txt",
            )

    def test_resolve_user_file_dotdot(self):
        with pytest.raises(ValueError, match="非法文件名"):
            self.store.resolve_user_file(
                current_user_id=1,
                owner_id=1,
                session_id="s1",
                filename="../etc/passwd",
            )

    def test_resolve_user_file_not_exists(self):
        with pytest.raises(FileNotFoundError):
            self.store.resolve_user_file(
                current_user_id=1,
                owner_id=1,
                session_id="s1",
                filename="nonexistent.txt",
            )


# ── SafetyResult ──


class TestSafetyResult:
    def test_tuple(self):
        sr = SafetyResult(has_violation=True, sanitized_text="clean")
        assert sr.has_violation is True
        assert sr.sanitized_text == "clean"
