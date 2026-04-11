import json
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.utils.paths import WORKPLACE_DIR

UPLOAD_DIR = WORKPLACE_DIR / "chat-uploads"
MAX_FILE_CONTENT_CHARS = 15000


def _resolve_upload_path(file_url: str) -> Optional[str]:
    """将前端 URL 转换为服务器绝对路径。"""
    if not file_url.startswith("/uploads/"):
        return None
    relative = file_url.removeprefix("/uploads/")
    path = (UPLOAD_DIR / relative).resolve()
    if not str(path).startswith(str(UPLOAD_DIR.resolve())):
        return None
    return str(path) if path.exists() else None


def _read_file_impl(absolute_path: str) -> str:
    """底层文件读取，支持 PDF、DOCX、TXT。"""
    path = Path(absolute_path)
    if not path.exists():
        return f"文件不存在: {absolute_path}"
    if not path.is_file():
        return f"路径不是文件: {absolute_path}"

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
            para.text for para in doc.paragraphs if para.text.strip()
        )
    elif suffix in {".txt", ".md", ".log"}:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    else:
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md）"

    if not content or not content.strip():
        return "文件内容为空"
    if len(content) > MAX_FILE_CONTENT_CHARS:
        content = content[:MAX_FILE_CONTENT_CHARS] + "\n\n[...文档内容过长，已截断...]"
    return content


@tool("read_uploaded_file")
def read_uploaded_file(file_url: str) -> str:
    """读取用户上传的文档内容（PDF、Word、TXT 等）。

    Args:
        file_url: 前端上传后返回的文件 URL，格式如 /uploads/{user_id}/{filename}
    """
    absolute_path = _resolve_upload_path(file_url)
    if absolute_path is None:
        return f"无法解析文件路径: {file_url}。请确认文件 URL 格式正确且文件存在。"
    return _read_file_impl(absolute_path)


@tool("list_uploaded_files")
def list_uploaded_files(user_id: int) -> str:
    """列出用户上传的所有文件。"""
    user_dir = UPLOAD_DIR / str(user_id)
    if not user_dir.exists():
        return "用户暂无上传文件。"
    files = [f for f in user_dir.iterdir() if f.is_file()]
    if not files:
        return "用户暂无上传文件。"
    return "用户上传的文件列表:\n" + "\n".join(
        f"- {f.name} ({f.stat().st_size} bytes)" for f in files
    )
