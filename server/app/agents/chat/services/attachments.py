"""Helpers for resolving and reading uploaded chat attachments."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.utils.paths import WORKPLACE_DIR

UPLOAD_DIR = WORKPLACE_DIR / "chat-uploads"
MAX_FILE_CONTENT_CHARS = 15000


def resolve_uploaded_path(file_url: str) -> Optional[tuple[int, str]]:
    """将前端 URL 转换为 (owner_id, 服务器绝对路径)。"""
    relative: str
    if file_url.startswith("/api/v1/ai/chat/uploads/"):
        relative = file_url.removeprefix("/api/v1/ai/chat/uploads/")
    elif file_url.startswith("/uploads/"):
        relative = file_url.removeprefix("/uploads/")
    else:
        return None

    parts = [p for p in relative.split("/") if p]
    if len(parts) == 3:
        owner_part, session_id, filename = parts
    elif len(parts) == 2:
        owner_part, filename = parts
        session_id = ""
    else:
        return None

    if not owner_part.isdigit():
        return None
    if session_id and Path(session_id).name != session_id:
        return None
    if Path(filename).name != filename:
        return None

    user_dir = (UPLOAD_DIR / owner_part).resolve()
    path = (user_dir / session_id / filename).resolve() if session_id else (user_dir / filename).resolve()
    if not str(path).startswith(str(user_dir)):
        return None
    if not path.exists():
        return None

    return int(owner_part), str(path)


def resolve_uploaded_image_path(image_url: str) -> Path | None:
    """解析图片上传 URL 为本地绝对路径。"""
    resolved = resolve_uploaded_path(image_url)
    if resolved is None:
        return None
    _, absolute_path = resolved
    path = Path(absolute_path)
    return path if path.is_file() else None


def read_uploaded_file_content(absolute_path: str) -> str:
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
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md, .log）"

    if not content or not content.strip():
        return "文件内容为空"
    if len(content) > MAX_FILE_CONTENT_CHARS:
        content = content[:MAX_FILE_CONTENT_CHARS] + "\n\n[...文档内容过长，已截断...]"
    return content
