from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.chat.utils.files import read_uploaded_file_content, analyze_documents


class TestReadUploadedFileContent:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_not_exists(self):
        result = read_uploaded_file_content("/nonexistent/file.txt")
        assert "不存在" in result

    def test_not_file(self):
        result = read_uploaded_file_content(self.tmpdir)
        assert "不是文件" in result

    def test_txt_file(self):
        p = Path(self.tmpdir) / "test.txt"
        p.write_text("hello world", encoding="utf-8")
        result = read_uploaded_file_content(str(p))
        assert result == "hello world"

    def test_md_file(self):
        p = Path(self.tmpdir) / "readme.md"
        p.write_text("# Title\nContent", encoding="utf-8")
        result = read_uploaded_file_content(str(p))
        assert "# Title" in result

    def test_log_file(self):
        p = Path(self.tmpdir) / "app.log"
        p.write_text("2026-01-01 ERROR something", encoding="utf-8")
        result = read_uploaded_file_content(str(p))
        assert "ERROR" in result

    def test_empty_file(self):
        p = Path(self.tmpdir) / "empty.txt"
        p.write_text("")
        result = read_uploaded_file_content(str(p))
        assert "为空" in result

    def test_unsupported_extension(self):
        p = Path(self.tmpdir) / "data.xyz"
        p.write_text("content")
        result = read_uploaded_file_content(str(p))
        assert "不支持" in result

    def test_long_file_truncated(self):
        p = Path(self.tmpdir) / "long.txt"
        p.write_text("x" * 20000, encoding="utf-8")
        result = read_uploaded_file_content(str(p), max_content_chars=100)
        assert len(result) > 100
        assert "截断" in result

    def test_custom_max_chars(self):
        p = Path(self.tmpdir) / "test.txt"
        p.write_text("short", encoding="utf-8")
        result = read_uploaded_file_content(str(p), max_content_chars=1000)
        assert result == "short"


class TestAnalyzeDocuments:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        import app.chat.utils.files as mod
        self._orig = mod.UPLOAD_DIR
        mod.UPLOAD_DIR = Path(self.tmpdir)

    def teardown_method(self):
        import app.chat.utils.files as mod
        mod.UPLOAD_DIR = self._orig

    def _create_file(self, rel_path: str, content: str = "test content") -> Path:
        p = Path(self.tmpdir) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    @pytest.mark.asyncio
    async def test_no_files(self):
        result = await analyze_documents(current_user_id=1, file_urls=[], question="分析")
        assert result["success"] is False
        assert "未找到" in result["error"]

    @pytest.mark.asyncio
    async def test_one_file(self):
        self._create_file("1/s1/doc.txt", "文档内容ABC")
        result = await analyze_documents(
            current_user_id=1,
            file_urls=["/api/v1/ai/chat/uploads/1/s1/doc.txt"],
            question="总结这个文档",
        )
        assert result["success"] is True
        assert "文档内容ABC" in result["analysis_text"]
        assert len(result["documents"]) == 1

    @pytest.mark.asyncio
    async def test_forbidden_user(self):
        self._create_file("2/s1/secret.txt", "secret")
        result = await analyze_documents(
            current_user_id=1,
            file_urls=["/api/v1/ai/chat/uploads/2/s1/secret.txt"],
            question="分析",
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_multiple_files(self):
        self._create_file("1/s1/a.txt", "content A")
        self._create_file("1/s1/b.txt", "content B")
        result = await analyze_documents(
            current_user_id=1,
            file_urls=[
                "/api/v1/ai/chat/uploads/1/s1/a.txt",
                "/api/v1/ai/chat/uploads/1/s1/b.txt",
            ],
            question="分析",
        )
        assert result["success"] is True
        assert len(result["documents"]) == 2
        assert "content A" in result["analysis_text"]
        assert "content B" in result["analysis_text"]
