"""文档提取、路径安全校验与工具语义化描述测试。"""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

import app.chat.context as context_mod
from app.chat.context import read_uploaded_file_content, resolve_uploaded_path
from app.chat.tools import build_read_document_tool, describe_tool_call


class TestReadAndResolveFiles:
    def setup_method(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self._orig = context_mod.WORKPLACE_DIR
        context_mod.WORKPLACE_DIR = Path(self.tmpdir).resolve()

    def teardown_method(self) -> None:
        context_mod.WORKPLACE_DIR = self._orig

    def _create_file(self, rel_path: str, content: str = "文档内容ABC") -> Path:
        p = Path(self.tmpdir) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_read_uploaded_file_content(self) -> None:
        p = self._create_file("test.txt", "hello world")
        assert read_uploaded_file_content(str(p)) == "hello world"
        assert "不存在" in read_uploaded_file_content("/nonexistent/x.txt")

    def test_resolve_uploaded_path(self) -> None:
        self._create_file("user1/chat/s1/uploads/doc.txt")
        res = resolve_uploaded_path("/static/user1/chat/s1/uploads/doc.txt")
        assert res is not None
        assert res[0] == "user1"
        assert resolve_uploaded_path("/etc/passwd") is None

    @pytest.mark.asyncio
    async def test_read_document_tool_and_permissions(self) -> None:
        self._create_file("user1/chat/s1/uploads/a.txt", "内容A")
        self._create_file("user2/chat/s1/uploads/secret.txt", "机密")
        tool = build_read_document_tool(username="user1", session_id="s1", workdir=Path(self.tmpdir))

        out = await tool.handler(path="/static/user1/chat/s1/uploads/a.txt")
        assert out["status"] == "ok"
        assert "内容A" in out["text"]

        denied = await tool.handler(path="/static/user2/chat/s1/uploads/secret.txt")
        assert denied["status"] == "failed"

    def test_describe_tool_call_semantics(self) -> None:
        kind, title, sub = describe_tool_call("search_knowledge_base", {"query": "TCP拥塞控制"})
        assert kind == "knowledge"
        assert "检索课程知识库" in title
        assert "TCP拥塞控制" in sub

        v_kind, v_title, v_sub = describe_tool_call(
            "view_image",
            {"path": "/static/u/chat/s/uploads/circuit.png", "question": "分析电路图"},
        )
        assert v_kind == "vision"
        assert "circuit.png" in v_title
        assert "分析电路图" in v_sub
