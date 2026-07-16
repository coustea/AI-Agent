"""索引构建器测试。

测试当前的 RAG 模块：
  - build.py      构建流程编排
  - load.py       文档加载
  - metadata.py   元数据推断
  - splitter.py   文档分割
  - store.py      向量库 + BM25 存储
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.documents import Document

from app.rag.bm25 import BM25Index
from app.rag.build import _ensure_complete_index, _read_manifest, _write_manifest, build_index
from app.rag.load import DocumentLoadError, load_directory
from app.rag.metadata import enrich_metadata, infer_title, infer_course, infer_section
from app.rag.splitter import split_documents
from app.rag.store import _stable_chunk_id


class TestSplitDocuments:
    """测试 split_documents 函数（基于 Document 输入）。"""

    def test_simple_markdown(self):
        """测试简单 Markdown 文本分割。"""
        doc = Document(
            page_content="这是一段普通文本。",
            metadata={"source": "test.md", "file_type": ".md"},
        )
        chunks = split_documents([doc])
        assert len(chunks) >= 1
        assert any("普通文本" in chunk.page_content for chunk in chunks)

    def test_heading_split(self):
        """测试按标题分割。"""
        text = "## 第一节\n" + "内容1" * 200 + "\n\n## 第二节\n" + "内容2" * 200
        doc = Document(
            page_content=text,
            metadata={"source": "test.md", "file_type": ".md"},
        )
        chunks = split_documents([doc])
        assert len(chunks) >= 2

    def test_empty_input(self):
        """测试空输入。"""
        doc = Document(page_content="", metadata={"source": "empty.md"})
        chunks = split_documents([doc])
        assert chunks == []

    def test_whitespace_only(self):
        """测试空白输入。"""
        doc = Document(page_content="   ", metadata={"source": "ws.md"})
        chunks = split_documents([doc])
        assert chunks == []

    def test_code_block_protection(self):
        """测试代码块不被拆开。"""
        text = "前文\n```python\nprint('hello')\n```\n后文"
        doc = Document(
            page_content=text,
            metadata={"source": "test.md", "file_type": ".md"},
        )
        chunks = split_documents([doc])
        # 代码块不应被拆开（至少有一个 chunk 包含完整代码块）
        for chunk in chunks:
            if "print" in chunk.page_content:
                assert "```" in chunk.page_content

    def test_metadata_preserved(self):
        """测试元数据被保留。"""
        doc = Document(
            page_content="测试内容足够长来产生一个chunk",
            metadata={"source": "test.md", "file_type": ".md", "course": "计算机网络"},
        )
        chunks = split_documents([doc])
        assert len(chunks) >= 1
        # 元数据应被保留
        for chunk in chunks:
            assert chunk.metadata.get("source") == "test.md"
            assert chunk.metadata.get("course") == "计算机网络"


class TestMetadata:
    """测试元数据推断函数。"""

    def test_stable_chunk_id(self):
        """测试稳定 chunk ID 生成。"""
        doc1 = Document(
            page_content="content",
            metadata={"source": "a.md", "section": "sec", "heading_path": "path"},
        )
        doc2 = Document(
            page_content="content",
            metadata={"source": "a.md", "section": "sec", "heading_path": "path"},
        )
        id1 = _stable_chunk_id(doc1)
        id2 = _stable_chunk_id(doc2)
        assert id1 == id2  # 相同输入产生相同 ID

    def test_different_content_different_id(self):
        """测试不同内容产生不同 ID。"""
        doc1 = Document(
            page_content="content1",
            metadata={"source": "a.md", "section": "sec"},
        )
        doc2 = Document(
            page_content="content2",
            metadata={"source": "a.md", "section": "sec"},
        )
        id1 = _stable_chunk_id(doc1)
        id2 = _stable_chunk_id(doc2)
        assert id1 != id2

    def test_infer_title(self):
        """测试标题推断。"""
        assert infer_title("book/计算机网络.final.md") == "计算机网络"
        assert infer_title("book/os.md") == "os"

    def test_infer_course(self):
        """测试课程推断。"""
        # 新结构：第一级目录匹配
        assert infer_course("计算机网络/chapter1/tcp.md") == "计算机网络"
        assert infer_course("操作系统/process.md") == "操作系统"
        # 无匹配返回空
        assert infer_course("未知教材/test.md") == ""

    def test_infer_section(self):
        """测试章节提取。"""
        assert infer_section("## TCP 连接\n内容") == "TCP 连接"
        assert infer_section("普通文本") == ""

    def test_enrich_metadata(self):
        """测试元数据填充。"""
        doc = Document(
            page_content="## TCP 连接\n内容足够长",
            metadata={"source": "计算机网络/tcp.md", "file_type": ".md"},
        )
        enriched = enrich_metadata([doc])
        assert len(enriched) == 1
        assert enriched[0].metadata.get("course") == "计算机网络"
        # title 从文件名推断：tcp.md -> tcp
        assert enriched[0].metadata.get("title") == "tcp"
        # heading_path 由 splitter 填充，enrich_metadata 不涉及


class TestLoadDocuments:
    """测试文档加载函数。"""

    def test_load_from_dir(self, tmp_path: Path):
        """测试从目录加载文档。"""
        (tmp_path / "test.final.md").write_text("测试内容", encoding="utf-8")
        docs = load_directory(tmp_path, extensions={".md"})
        assert len(docs) == 1
        assert "测试内容" in docs[0].page_content

    def test_missing_dir(self):
        """测试缺失目录抛出异常。"""
        with pytest.raises(FileNotFoundError):
            load_directory(Path("/nonexistent"), extensions={".md"})

    def test_no_matching_docs(self, tmp_path: Path):
        """测试无匹配文档。"""
        (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
        docs = load_directory(tmp_path, extensions={".md"})
        assert docs == []

    def test_empty_file_skipped(self, tmp_path: Path):
        """测试空文件被跳过。"""
        (tmp_path / "empty.md").write_text("   ", encoding="utf-8")
        docs = load_directory(tmp_path, extensions={".md"})
        assert docs == []

    def test_load_failure_aborts_with_relative_source_path(self, tmp_path: Path):
        """单个源文件无法加载时不能发布不完整知识库。"""
        broken_file = tmp_path / "chapter" / "broken.md"
        broken_file.parent.mkdir()
        broken_file.write_text("内容", encoding="utf-8")

        with patch("app.rag.load._load_file", side_effect=OSError("read failed")):
            with pytest.raises(DocumentLoadError, match="chapter/broken.md"):
                load_directory(tmp_path, extensions={".md"})


class TestManifest:
    """测试 manifest 写入与读取。"""

    def test_write_and_read(self, tmp_path: Path):
        """测试 manifest 写入与读取。"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        _write_manifest(
            output_dir=tmp_path,
            collection="langchain",
            chunk_count=100,
            doc_count=4,
            source_dir=source_dir,
            source_snapshot={"test.md": "abc123"},
            batch_size=16,
            embedding_dimension=1024,
            bm25_metadata={
                "filename": "bm25_index.pkl",
                "schema_version": "1",
                "chunk_count": 100,
                "sha256": "abc123",
            },
        )
        manifest = _read_manifest(tmp_path)
        assert manifest is not None
        assert manifest["schema_version"] == "1"
        assert manifest["collection"] == "langchain"
        assert manifest["chunk_count"] == 100
        assert manifest["document_count"] == 4
        assert manifest["embedding_model"]  # 非空

    def test_read_missing(self, tmp_path: Path):
        """测试读取缺失的 manifest。"""
        assert _read_manifest(tmp_path) is None


class TestBuildIndex:
    """测试索引构建流程。"""

    @pytest.mark.asyncio
    async def test_no_source_docs_fails(self, tmp_path: Path):
        """测试无源文档时构建失败。"""
        empty_dir = tmp_path / "empty_src"
        empty_dir.mkdir()
        out_dir = tmp_path / "output"

        with pytest.raises(ValueError, match="No matching documents"):
            build_index(source_dir=empty_dir, output_dir=out_dir)

    @pytest.mark.asyncio
    async def test_embedding_failure_preserves_existing(self, tmp_path: Path):
        """测试 embedding 失败不删除现有索引。"""
        # 创建一个源文件
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.final.md").write_text(
            "# 测试\n内容足够长来产生一个chunk",
            encoding="utf-8",
        )

        # 创建正式索引目录（模拟已有索引）
        out_dir = tmp_path / "kb"
        out_dir.mkdir()
        (out_dir / "existing.txt").write_text("existing index", encoding="utf-8")

        with patch("app.rag.embeddings.embed_documents") as mock_embed:
            mock_embed.return_value = None  # embedding 失败

            with pytest.raises(RuntimeError, match="embedding service did not return vectors"):
                build_index(source_dir=src_dir, output_dir=out_dir)

        # 正式索引目录应仍然存在
        assert out_dir.exists()
        assert (out_dir / "existing.txt").exists()

    def test_bm25_rejects_misaligned_texts_and_metadata(self):
        """BM25 文档必须与向量 chunk 一一对应。"""
        with pytest.raises(ValueError, match="texts/metadatas"):
            BM25Index().build(["first", "second"], [{"chunk_id": "one"}])

    def test_incomplete_staged_index_does_not_replace_existing(self, tmp_path: Path):
        """临时索引缺少 BM25 时不得进入替换阶段。"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_dir.joinpath("lesson.md").write_text("lesson", encoding="utf-8")
        output_dir = tmp_path / "index"
        output_dir.mkdir()
        output_dir.joinpath("existing.txt").write_text("keep", encoding="utf-8")
        chunk = Document(page_content="lesson", metadata={"source": "lesson.md"})

        with patch("app.rag.build.load_directory", return_value=[chunk]), \
             patch("app.rag.build.enrich_metadata", return_value=[chunk]), \
             patch("app.rag.build.split_documents", return_value=[chunk]), \
             patch("app.rag.build.probe_embedding_service", return_value=2), \
             patch("app.rag.build.build_store", return_value=(1, 1)), \
             patch("app.rag.build.build_bm25", return_value={"schema_version": "1"}), \
             patch("app.rag.build.verify_store"), \
             patch(
                 "app.rag.build._ensure_complete_index",
                 side_effect=RuntimeError("bm25 index incomplete"),
             ), \
             patch("app.rag.build._swap_index") as swap_index:
            with pytest.raises(RuntimeError, match="bm25 index incomplete"):
                build_index(source_dir=source_dir, output_dir=output_dir)

        swap_index.assert_not_called()
        assert output_dir.joinpath("existing.txt").read_text(encoding="utf-8") == "keep"

    def test_check_only_does_not_modify(self, tmp_path: Path):
        """测试 --check-only 不修改磁盘。"""
        from app.rag.build import check_index

        # 无论结果如何，不应创建或删除文件
        before_files = set(tmp_path.rglob("*"))
        check_index(output_dir=tmp_path / "nonexistent")
        after_files = set(tmp_path.rglob("*"))
        assert before_files == after_files
