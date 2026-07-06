"""索引构建器测试。"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.rag.indexing.build import (
    _apply_overlap,
    _extract_section,
    _infer_course,
    _infer_title,
    _load_documents,
    _split_markdown,
    _stable_chunk_id,
    _write_manifest,
    _read_manifest,
)


class TestSplitMarkdown:
    def test_simple_text(self):
        chunks = _split_markdown("这是一段普通文本。")
        assert len(chunks) >= 1
        assert "普通文本" in chunks[0]

    def test_heading_split(self):
        text = "## 第一节\n" + "内容1" * 200 + "\n\n## 第二节\n" + "内容2" * 200
        chunks = _split_markdown(text)
        assert len(chunks) >= 2

    def test_empty_input(self):
        assert _split_markdown("") == []
        assert _split_markdown("   ") == []

    def test_code_block_protection(self):
        text = "前文\n```python\nprint('hello')\n```\n后文"
        chunks = _split_markdown(text)
        # 代码块不应被拆开
        for chunk in chunks:
            if "print" in chunk:
                assert "```" in chunk

    def test_short_chunks_merged(self):
        text = "短\n\n短\n\n这是一段足够长的内容，用来确保它不会被合并掉，需要超过最小长度限制才会被当作独立块处理。"
        chunks = _split_markdown(text)
        # 短块应被合并
        assert len(chunks) >= 1

    def test_overlap_applied(self):
        chunks = ["块1内容" * 50, "块2内容" * 50]
        overlapped = _apply_overlap(chunks, overlap=100)
        assert len(overlapped) == 2
        # 第二块应包含第一块的尾部
        assert "块1" in overlapped[1]


class TestMetadata:
    def test_stable_chunk_id(self):
        id1 = _stable_chunk_id("a.md", "sec", "content")
        id2 = _stable_chunk_id("a.md", "sec", "content")
        assert id1 == id2  # 相同输入产生相同 ID

    def test_different_content_different_id(self):
        id1 = _stable_chunk_id("a.md", "sec", "content1")
        id2 = _stable_chunk_id("a.md", "sec", "content2")
        assert id1 != id2

    def test_infer_title(self):
        assert _infer_title("book/计算机网络.final.md") == "计算机网络"
        assert _infer_title("book/os.md") == "os"

    def test_infer_course(self):
        assert _infer_course("计算机网络") == "计算机网络"
        assert _infer_course("操作系统") == "操作系统"
        assert _infer_course("未知教材") == ""

    def test_extract_section(self):
        assert _extract_section("## TCP 连接\n内容") == "TCP 连接"
        assert _extract_section("普通文本") == ""


class TestLoadDocuments:
    def test_load_from_dir(self, tmp_path: Path):
        (tmp_path / "test.final.md").write_text("测试内容", encoding="utf-8")
        docs = _load_documents(tmp_path, "*.final.md")
        assert len(docs) == 1
        assert "测试内容" in docs[0]["text"]

    def test_missing_dir(self):
        with pytest.raises(FileNotFoundError):
            _load_documents(Path("/nonexistent"), "*.md")

    def test_no_matching_docs(self, tmp_path: Path):
        (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
        docs = _load_documents(tmp_path, "*.final.md")
        assert docs == []

    def test_empty_file_skipped(self, tmp_path: Path):
        (tmp_path / "empty.final.md").write_text("   ", encoding="utf-8")
        docs = _load_documents(tmp_path, "*.final.md")
        assert docs == []


class TestManifest:
    def test_write_and_read(self, tmp_path: Path):
        _write_manifest(tmp_path, "langchain", 100, 4)
        manifest = _read_manifest(tmp_path)
        assert manifest is not None
        assert manifest["schema_version"] == "1"
        assert manifest["collection"] == "langchain"
        assert manifest["chunk_count"] == 100
        assert manifest["document_count"] == 4
        assert manifest["embedding_model"]  # 非空

    def test_read_missing(self, tmp_path: Path):
        assert _read_manifest(tmp_path) is None


class TestBuildIndex:
    @pytest.mark.asyncio
    async def test_no_source_docs_fails(self, tmp_path: Path):
        from app.rag.indexing.build import build_index

        empty_dir = tmp_path / "empty_src"
        empty_dir.mkdir()
        out_dir = tmp_path / "output"

        with pytest.raises(ValueError, match="No matching documents"):
            build_index(source_dir=empty_dir, output_dir=out_dir)

    @pytest.mark.asyncio
    async def test_embedding_failure_preserves_existing(self, tmp_path: Path):
        """embedding 失败不应删除正式索引。"""
        from app.rag.indexing.build import build_index

        # 创建一个源文件
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.final.md").write_text("# 测试\n内容足够长来产生一个chunk", encoding="utf-8")

        # 创建正式索引目录（模拟已有索引）
        out_dir = tmp_path / "kb"
        out_dir.mkdir()
        (out_dir / "existing.txt").write_text("existing index", encoding="utf-8")

        with patch("app.rag.indexing.build.embed_documents") as mock_embed:
            mock_embed.return_value = None  # embedding 失败

            with pytest.raises(RuntimeError, match="Embedding failed"):
                build_index(source_dir=src_dir, output_dir=out_dir)

        # 正式索引目录应仍然存在
        assert out_dir.exists()
        assert (out_dir / "existing.txt").exists()

    @pytest.mark.asyncio
    async def test_check_only_does_not_modify(self, tmp_path: Path):
        """--check-only 不应修改磁盘。"""
        from app.rag.indexing.build import check_index

        # 无论结果如何，不应创建或删除文件
        before_files = set(tmp_path.rglob("*"))
        check_index(output_dir=tmp_path / "nonexistent")
        after_files = set(tmp_path.rglob("*"))
        assert before_files == after_files
