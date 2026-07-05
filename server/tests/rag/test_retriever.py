"""RAG 检索模型与检索器测试。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.rag.models import RetrievedChunk, RetrievalResult, RetrievalStatus
from app.rag.retriever import IndexHealth


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


# ============ Task 2: 检索器测试 ============


def _make_health(ready: bool = True, reason: str = "ok", **kw: Any) -> IndexHealth:
    return IndexHealth(ready=ready, reason=reason, **kw)


def _fake_chroma_results(n: int = 3) -> dict[str, Any]:
    """生成 n 条 fake Chroma 查询结果。"""
    documents = [f"文档内容 {i}" for i in range(n)]
    metadatas = [
        {
            "chunk_id": f"chunk_{i}",
            "source": f"book/{i}.md",
            "title": f"教材{i}",
            "section": f"第{i}章",
            "course": "计算机网络" if i % 2 == 0 else "操作系统",
        }
        for i in range(n)
    ]
    distances = [0.1 + i * 0.05 for i in range(n)]
    return {"documents": [documents], "metadatas": [metadatas], "distances": [distances]}


class TestRetrieve:
    @pytest.mark.asyncio
    async def test_normal_returns_top_k(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = _fake_chroma_results(5)

            result = await retrieve("TCP 三次握手", top_k=3)
            assert result.status == "ok"
            assert len(result.chunks) == 3
            assert result.elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_dedup_by_chunk_id(self):
        from app.rag.retriever import retrieve

        docs = ["文档1", "文档2", "文档1重复"]
        metas = [
            {"chunk_id": "same_id", "source": "a.md", "title": "A", "section": "S1", "course": "CS"},
            {"chunk_id": "diff_id", "source": "b.md", "title": "B", "section": "S2", "course": "CS"},
            {"chunk_id": "same_id", "source": "a.md", "title": "A", "section": "S1", "course": "CS"},
        ]
        dists = [0.1, 0.2, 0.3]
        fake_results = {"documents": [docs], "metadatas": [metas], "distances": [dists]}

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = fake_results

            result = await retrieve("查询")
            assert result.status == "ok"
            chunk_ids = [c.chunk_id for c in result.chunks]
            assert chunk_ids.count("same_id") == 1

    @pytest.mark.asyncio
    async def test_course_name_in_query(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = _fake_chroma_results(2)

            await retrieve("TCP", course_name="计算机网络")

            embed_call_arg = mock_embed.call_args[0][0]
            assert "计算机网络" in embed_call_arg
            assert "TCP" in embed_call_arg

    @pytest.mark.asyncio
    async def test_embedding_unavailable(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = None

            result = await retrieve("TCP 三次握手")
            assert result.status == "unavailable"
            assert "embedding" in result.message

    @pytest.mark.asyncio
    async def test_collection_not_found(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health:
            mock_health.return_value = _make_health(ready=False, reason="collection_missing")

            result = await retrieve("TCP 三次握手")
            assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_chroma_exception(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.side_effect = RuntimeError("chroma crashed")

            result = await retrieve("查询")
            assert result.status == "unavailable"

    @pytest.mark.asyncio
    async def test_empty_results(self):
        from app.rag.retriever import retrieve

        fake_results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = fake_results

            result = await retrieve("不存在的查询")
            assert result.status == "empty"

    @pytest.mark.asyncio
    async def test_top_k_clamped(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = _fake_chroma_results(10)

            result = await retrieve("查询", top_k=20)
            assert result.status == "ok"
            assert len(result.chunks) <= 8

    @pytest.mark.asyncio
    async def test_top_k_minimum_1(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = _fake_chroma_results(5)

            result = await retrieve("查询", top_k=0)
            assert result.status == "ok"
            assert len(result.chunks) >= 1

    @pytest.mark.asyncio
    async def test_empty_chunks_filtered(self):
        from app.rag.retriever import retrieve

        docs = ["有内容", "", "   "]
        metas = [
            {"chunk_id": "a", "source": "a.md", "title": "A", "section": "", "course": ""},
            {"chunk_id": "b", "source": "b.md", "title": "B", "section": "", "course": ""},
            {"chunk_id": "c", "source": "c.md", "title": "C", "section": "", "course": ""},
        ]
        dists = [0.1, 0.2, 0.3]
        fake_results = {"documents": [docs], "metadatas": [metas], "distances": [dists]}

        with patch("app.rag.retriever.check_index_health") as mock_health, \
             patch("app.rag.retriever.embed_query") as mock_embed, \
             patch("app.rag.retriever._chroma_query") as mock_chroma:
            mock_health.return_value = _make_health(chunk_count=100)
            mock_embed.return_value = [0.1] * 1024
            mock_chroma.return_value = fake_results

            result = await retrieve("查询")
            assert result.status == "ok"
            for chunk in result.chunks:
                assert chunk.content.strip()

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        from app.rag.retriever import retrieve

        result = await retrieve("")
        assert result.status == "empty"

    @pytest.mark.asyncio
    async def test_kb_disabled_returns_unavailable(self):
        from app.rag.retriever import retrieve

        with patch("app.rag.retriever.KB_ENABLED", False):
            result = await retrieve("查询")
            assert result.status == "unavailable"


class TestIndexHealth:
    def test_ready(self):
        h = IndexHealth(ready=True, reason="ok", chunk_count=100)
        assert h.ready is True
        assert h.chunk_count == 100

    def test_not_ready(self):
        h = IndexHealth(ready=False, reason="manifest_missing")
        assert h.ready is False
        assert h.reason == "manifest_missing"
