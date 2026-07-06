"""知识库索引健康检查测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.rag.retriever import IndexHealth, check_index_health


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
        """Manifest chunk_count 为零。"""
        manifest = {
            "schema_version": "1",
            "collection": "langchain",
            "embedding_model": "bge-m3",
            "chunk_count": 0,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        with patch("app.rag.retriever.KB_ENABLED", True), \
             patch("app.rag.retriever.KB_DIR", str(tmp_path)):
            health = check_index_health()
            assert not health.ready
            assert "zero" in health.reason


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
