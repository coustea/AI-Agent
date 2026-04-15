"""
Chat 上传文件工具。

只保留 chat 业务专属能力：
- 解析 chat-uploads 下的用户/会话文件路径
- 读取用户上传文档
- 列出用户上传文件
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.chat.context import get_current_user_id
from app.shared.paths import WORKPLACE_DIR

UPLOAD_DIR = WORKPLACE_DIR / "chat-uploads"
MAX_FILE_CONTENT_CHARS = 15000


def _resolve_upload_path(file_url: str) -> Optional[tuple[int, Path]]:
    """将前端 URL 转换为 (owner_id, 服务器绝对路径)。"""
    relative: str
    if file_url.startswith("/api/v1/ai/chat/uploads/"):
        relative = file_url.removeprefix("/api/v1/ai/chat/uploads/")
    elif file_url.startswith("/uploads/"):
        relative = file_url.removeprefix("/uploads/")
    else:
        return None

    parts = [part for part in relative.split("/") if part]
    if len(parts) != 3:
        return None

    owner_part = parts[0]
    if not owner_part.isdigit():
        return None

    user_dir = (UPLOAD_DIR / owner_part).resolve()
    session_part, filename = parts[1], parts[2]
    if Path(session_part).name != session_part:
        return None
    if Path(filename).name != filename:
        return None

    session_dir = (user_dir / session_part).resolve()
    path = (session_dir / filename).resolve()
    if not str(session_dir).startswith(str(user_dir)):
        return None
    if not str(path).startswith(str(session_dir)):
        return None
    if not path.exists():
        return None

    return int(owner_part), path


def _read_uploaded_file_impl(path: Path) -> str:
    """底层文件读取，支持 PDF、DOCX、TXT、MD、LOG。"""
    if not path.exists():
        return f"文件不存在: {path}"
    if not path.is_file():
        return f"路径不是文件: {path}"

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pymupdf import open as pdf_open

        text_parts = []
        with pdf_open(str(path)) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        content = "\n".join(text_parts)
    elif suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        content = "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
            if paragraph.text.strip()
        )
    elif suffix in {".txt", ".md", ".log"}:
        content = path.read_text(encoding="utf-8", errors="replace")
    else:
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md, .log）"

    if not content or not content.strip():
        return "文件内容为空"
    if len(content) > MAX_FILE_CONTENT_CHARS:
        content = content[:MAX_FILE_CONTENT_CHARS] + "\n\n[...文档内容过长，已截断...]"
    return content


@tool("read_uploaded_file")
def read_uploaded_file(file_url: str) -> str:
    """读取当前用户上传的文档内容（PDF、DOCX、TXT、MD、LOG）。"""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return "读取失败：缺少用户上下文。"

    resolved = _resolve_upload_path(file_url)
    if resolved is None:
        return f"无法解析文件路径: {file_url}。请确认文件 URL 格式正确且文件存在。"

    owner_id, absolute_path = resolved
    if owner_id != current_user_id:
        return "无权限读取该文件。"

    return _read_uploaded_file_impl(absolute_path)


@tool("list_uploaded_files")
def list_uploaded_files() -> str:
    """列出当前用户上传的所有文件。"""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return "读取失败：缺少用户上下文。"

    user_dir = UPLOAD_DIR / str(current_user_id)
    if not user_dir.exists():
        return "用户暂无上传文件。"

    files = [file for file in user_dir.rglob("*") if file.is_file()]
    if not files:
        return "用户暂无上传文件。"

    return "用户上传的文件列表:\n" + "\n".join(
        f"- {file.relative_to(user_dir)} ({file.stat().st_size} bytes)" for file in files
    )
