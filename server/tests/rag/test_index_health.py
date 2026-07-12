"""知识库索引健康检查测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.rag.retriever import (
    IndexHealth,
    _get_cached_health,
    check_index_health,
    reset_health_cache,
)


class TestCheckIndexHealth:
    def test_kb_disabled(self):
        with patch("app.rag.retriever.KB_ENABLED", False):
            health = check_index_health()
            assert not health.ready
            assert "disabled" in health.reason

    def test_kb_dir_missing(self):
        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", "/nonexistent_dir_for_test"):
            health = check_index_health()
            assert not health.ready
            assert "missing" in health.reason

    def test_manifest_missing(self, tmp_path: Path):
        """目录存在但无 manifest。"""
        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", str(tmp_path)):
            health = check_index_health()
            assert not health.ready
            assert "manifest" in health.reason

    def test_schema_version_mismatch(self, tmp_path: Path):
        """Manifest schema_version 不一致。"""
        manifest = {
            "schema_version": "99",
            "collection": "langchain",
            "embedding_model": "bge-m3",
            "chunk_count": 100,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", str(tmp_path)):
            health = check_index_health()
            assert not health.ready
            assert "schema" in health.reason

    def test_collection_mismatch(self, tmp_path: Path):
        """Manifest collection 与配置不一致。"""
        manifest = {
            "schema_version": "1",
            "collection": "wrong_collection",
            "embedding_model": "bge-m3",
            "chunk_count": 100,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", str(tmp_path)):
            health = check_index_health()
            assert not health.ready
            assert "collection" in health.reason

    def test_embedding_model_mismatch(self, tmp_path: Path):
        """Manifest embedding_model 与配置不一致。"""
        manifest = {
            "schema_version": "1",
            "collection": "langchain",
            "embedding_model": "wrong-model",
            "chunk_count": 100,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", str(tmp_path)):
            health = check_index_health()
            assert not health.ready
            assert "embedding" in health.reason

    def test_chunk_count_zero(self, tmp_path: Path):
        """结构错误要先于 embedding 配置差异报告。"""
        manifest = {
            "schema_version": "1",
            "collection": "langchain",
            "embedding_model": "bge-m3",
            "chunk_count": 0,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", str(tmp_path)), \
             patch("app.rag.retriever.KB_EMBED_MODEL", "bge-m3"):
            health = check_index_health()
            assert not health.ready
            assert health.reason == "chunk_count_zero"

    @pytest.mark.asyncio
    async def test_health_cache_is_scoped_to_requested_directory(self, tmp_path: Path):
        """不同输出目录不能复用同一个健康检查缓存。"""
        reset_health_cache()
        first = tmp_path / "first"
        second = tmp_path / "second"
        first_health = IndexHealth(ready=False, reason="first")
        second_health = IndexHealth(ready=False, reason="second")

        with patch(
            "app.rag.retriever.check_index_health",
            side_effect=[first_health, second_health],
        ) as check:
            assert (await _get_cached_health(first)).reason == "first"
            assert (await _get_cached_health(second)).reason == "second"

        assert check.call_count == 2
        reset_health_cache()


class TestIndexHealthModel:
    def test_ready(self):
        h = IndexHealth(ready=True, reason="ok", chunk_count=100)
        assert h.ready is True
        assert h.chunk_count == 100

    def test_not_ready(self):
        h = IndexHealth(ready=False, reason="manifest_missing")
        assert h.ready is False

    def test_serialization(self):
        h = IndexHealth(ready=True, reason="ok", document_count=4, chunk_count=100)
        data = h.model_dump()
        restored = IndexHealth.model_validate(data)
        assert restored == h
