from __future__ import annotations

from pydantic import BaseModel

from app.chat.schemas import (
    NormalizedToolResult,
    SourceItem,
    UploadResponse,
    normalize_tool_result,
)


class TestSourceItem:
    def test_defaults(self):
        s = SourceItem(source="web")
        assert s.title == ""
        assert s.url == ""
        assert s.published_at is None


class TestNormalizedToolResult:
    def test_defaults(self):
        r = NormalizedToolResult()
        assert r.text == ""
        assert r.sources == []
        assert r.metadata == {}


class TestNormalizeToolResult:
    def test_none(self):
        result = normalize_tool_result(None)
        assert result.text == ""
        assert result.sources == []

    def test_string(self):
        result = normalize_tool_result("hello world")
        assert result.text == "hello world"
        assert result.sources == []

    def test_empty_string(self):
        result = normalize_tool_result("")
        assert result.text == ""

    def test_dict_with_text(self):
        result = normalize_tool_result({"text": "answer", "url": "http://x"})
        assert result.text == "answer"
        assert result.metadata.get("url") == "http://x"

    def test_dict_with_message(self):
        result = normalize_tool_result({"message": "fallback text"})
        assert result.text == "fallback text"

    def test_dict_with_sources(self):
        result = normalize_tool_result({
            "text": "info",
            "sources": [{"source": "web", "url": "http://x", "title": "X"}],
        })
        assert result.text == "info"
        assert len(result.sources) == 1
        assert result.sources[0].url == "http://x"

    def test_dict_no_text_no_message(self):
        result = normalize_tool_result({"key": "value"})
        assert result.text == ""

    def test_pydantic_model(self):
        class FakeModel(BaseModel):
            text: str = ""
            extra: bool = False
        result = normalize_tool_result(FakeModel(text="from model", extra=True))
        assert result.text == "from model"
        assert result.metadata.get("extra") is True

    def test_int(self):
        result = normalize_tool_result(42)
        assert result.text == "42"


class TestUploadResponse:
    def test_minimal(self):
        r = UploadResponse(url="/api/v1/ai/chat/uploads/1/s1/f.txt")
        assert r.url == "/api/v1/ai/chat/uploads/1/s1/f.txt"
        assert r.file_type == "document"
        assert r.original_name == ""
        assert r.size_bytes == 0

    def test_full(self):
        r = UploadResponse(
            url="/u",
            file_type="image",
            original_name="pic.png",
            size_bytes=1024,
            mime_type="image/png",
        )
        assert r.mime_type == "image/png"
