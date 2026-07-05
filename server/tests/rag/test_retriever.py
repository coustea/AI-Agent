"""RAG 检索模型与检索器测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.rag.models import RetrievedChunk, RetrievalResult, RetrievalStatus


# ============ Task 1: 模型测试 ============


class TestRetrievedChunk:
    def test_create_minimal(self):
        chunk = RetrievedChunk(
            chunk_id="abc", content="text", source="s", title="t"
        )
        assert chunk.chunk_id == "abc"
        assert chunk.section == ""
        assert chunk.course == ""
        assert chunk.distance is None

    def test_create_full(self):
        chunk = RetrievedChunk(
            chunk_id="abc",
            content="text",
            source="s",
            title="t",
            section="sec",
            course="os",
            distance=0.42,
        )
        assert chunk.distance == 0.42

    def test_serialization_roundtrip(self):
        chunk = RetrievedChunk(
            chunk_id="abc", content="text", source="s", title="t", distance=0.1
        )
        data = chunk.model_dump()
        restored = RetrievedChunk.model_validate(data)
        assert restored == chunk


class TestRetrievalResult:
    def test_ok_status(self):
        result = RetrievalResult(
            status="ok",
            query="test",
            chunks=[RetrievedChunk(chunk_id="a", content="c", source="s", title="t")],
        )
        assert result.status == "ok"
        assert len(result.chunks) == 1

    def test_empty_status(self):
        result = RetrievalResult(status="empty", query="test")
        assert result.status == "empty"
        assert result.chunks == []

    def test_unavailable_status(self):
        result = RetrievalResult(status="unavailable", query="test", message="Ollama down")
        assert result.status == "unavailable"

    def test_chunks_default_not_shared(self):
        """chunks 默认值不能被多个实例共享。"""
        r1 = RetrievalResult(status="empty", query="q1")
        r2 = RetrievalResult(status="empty", query="q2")
        r1.chunks.append(RetrievedChunk(chunk_id="x", content="c", source="s", title="t"))
        assert len(r2.chunks) == 0

    def test_status_rejects_unknown(self):
        with pytest.raises(ValidationError):
            RetrievalResult(status="broken", query="test")

    def test_serialization_roundtrip(self):
        result = RetrievalResult(
            status="ok",
            query="tcp",
            chunks=[RetrievedChunk(chunk_id="a", content="c", source="s", title="t")],
            elapsed_ms=320,
        )
        data = result.model_dump()
        restored = RetrievalResult.model_validate(data)
        assert restored == result

    def test_json_roundtrip(self):
        result = RetrievalResult(
            status="ok",
            query="tcp",
            chunks=[RetrievedChunk(chunk_id="a", content="c", source="s", title="t")],
        )
        json_str = result.model_dump_json()
        restored = RetrievalResult.model_validate_json(json_str)
        assert restored == result
