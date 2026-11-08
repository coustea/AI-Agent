"""文档提取、路径安全校验与工具语义化描述测试。"""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

import app.chat.files as context_mod
from app.chat.files import read_uploaded_file_content, resolve_uploaded_path
from app.chat.tools import build_read_document_tool
from app.chat.hooks import describe_tool_call


class TestReadAndResolveFiles:
    def setup_method(self) -> None:
        """准备隔离的上传目录。"""
        self.tmpdir = tempfile.mkdtemp()
        self._orig = context_mod.WORKPLACE_DIR
        context_mod.WORKPLACE_DIR = Path(self.tmpdir).resolve()

    def teardown_method(self) -> None:
        """恢复文件路径配置。"""
        context_mod.WORKPLACE_DIR = self._orig

    def _create_file(self, rel_path: str, content: str = "文档内容ABC") -> Path:
        """在隔离目录创建测试文件。"""
        p = Path(self.tmpdir) / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_read_uploaded_file_content(self) -> None:
        """验证文本读取与文件不存在提示。"""
        p = self._create_file("test.txt", "hello world")
        assert read_uploaded_file_content(str(p)) == "hello world"
        with pytest.raises(FileNotFoundError):
            read_uploaded_file_content("/nonexistent/x.txt")

    def test_resolve_uploaded_path(self) -> None:
        """验证上传地址解析与工作区外路径拒绝。"""
        self._create_file("user1/chat/s1/uploads/doc.txt")
        res = resolve_uploaded_path("/static/user1/chat/s1/uploads/doc.txt")
        assert res is not None
        assert res[0] == "user1"
        assert resolve_uploaded_path("/etc/passwd") is None

    @pytest.mark.asyncio
    async def test_read_document_tool_and_permissions(self) -> None:
        """验证文档读取与跨用户权限隔离。"""
        self._create_file("user1/chat/s1/uploads/a.txt", "内容A")
        self._create_file("user2/chat/s1/uploads/secret.txt", "机密")
        tool = build_read_document_tool(username="user1", session_id="s1", workdir=Path(self.tmpdir))

        out = await tool.handler(path="/static/user1/chat/s1/uploads/a.txt")
        assert out["status"] == "ok"
        assert "内容A" in out["text"]

        denied = await tool.handler(path="/static/user2/chat/s1/uploads/secret.txt")
        assert denied["status"] == "failed"

    def test_describe_tool_call_semantics(self) -> None:
        """验证工具步骤标题与参数描述。"""
        title, sub = describe_tool_call("search_knowledge_base", {"query": "TCP拥塞控制"})
        assert "检索课程知识库" in title
        assert "TCP拥塞控制" in sub

        v_title, v_sub = describe_tool_call(
            "view_image",
            {"path": "/static/u/chat/s/uploads/circuit.png", "question": "分析电路图"},
        )
        assert "circuit.png" in v_title
        assert "分析电路图" in v_sub


def test_attachment_limit_is_per_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """历史上传数量不限制新上传，每轮消息仍检查附件数量和归属。"""
    from app.chat import service
    from app.chat.files import save_upload
    from app.chat.schemas import AgentInput, AttachmentInput

    def uploads(username: str, session_id: str) -> Path:
        """将上传目录固定到隔离空间。"""
        return tmp_path / username / session_id / "uploads"

    monkeypatch.setattr(context_mod, "user_chat_uploads_dir", uploads)
    monkeypatch.setattr(service, "MAX_UPLOAD_FILES_PER_REQUEST", 2)
    files = [save_upload(filename=f"{i}.txt", content=b"text", username="alice", session_id="s1") for i in range(4)]
    inp = AgentInput(user_id=1, username="alice", session_id="s1", attachments=[AttachmentInput(**file) for file in files])
    with pytest.raises(ValueError, match="最多添加 2"):
        service._validate_attachments(inp)
    inp.attachments = inp.attachments[-2:]
    assert len(service._validate_attachments(inp)) == 2
    inp.attachments[0].url = "/static/bob/chat/s1/uploads/secret.txt"
    with pytest.raises(ValueError, match="不属于当前会话"):
        service._validate_attachments(inp)
