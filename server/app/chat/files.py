"""聊天附件上传、路径校验与文档读取。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from app.chat.schemas import AttachmentInput
from app.config import WORKPLACE_DIR, chat_upload_url, user_chat_uploads_dir
from app.infra.logging import get_logger

logger = get_logger(__name__)

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_DOC_EXT = {".pdf", ".docx", ".txt", ".md", ".log", ".xlsx", ".xls", ".csv", ".tsv"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOC_SIZE = 10 * 1024 * 1024
MAX_FILE_CONTENT_CHARS = 15000


def _guess_mime_type(suffix: str) -> str:
    """根据文件扩展名推断 MIME 类型。"""
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".log": "text/plain",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
    }
    return mapping.get(suffix, "application/octet-stream")


def save_upload(
    *,
    filename: str,
    content: bytes,
    username: str,
    session_id: str,
) -> dict[str, Any]:
    """校验并将用户上传文件写入会话 uploads 目录，返回 AttachmentInput 字典。"""
    if not filename:
        raise ValueError("文件名不能为空")
    suffix = Path(filename).suffix.lower()
    if suffix in ALLOWED_IMAGE_EXT:
        file_type, max_size = "image", MAX_IMAGE_SIZE
    elif suffix in ALLOWED_DOC_EXT:
        file_type, max_size = "document", MAX_DOC_SIZE
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")

    if len(content) > max_size:
        raise ValueError(f"文件大小超过限制（{max_size // (1024 * 1024)}MB）")
    uploads_dir = user_chat_uploads_dir(username, session_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(filename)
    if not safe_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}{suffix}"

    file_path = uploads_dir / safe_name
    if file_path.exists():
        file_path = uploads_dir / f"{file_path.stem}-{uuid4().hex[:8]}{file_path.suffix}"
        safe_name = file_path.name
    file_path.write_bytes(content)
    logger.info(
        "[ChatFiles] 附件已保存: user=%s session=%s file=%s type=%s size=%d",
        username, session_id, safe_name, file_type, len(content),
    )

    return AttachmentInput(
        url=chat_upload_url(username, session_id, safe_name),
        file_type=file_type,
        original_name=filename,
        size_bytes=len(content),
        mime_type=_guess_mime_type(suffix),
    ).model_dump()


def _safe_filename(filename: str) -> str:
    """过滤文件名中的非法路径字符并限制最大长度。"""
    safe = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
    if len(safe) > 100:
        name, ext = Path(safe).stem, Path(safe).suffix
        safe = f"{name[: 100 - len(ext)]}{ext}"
    return safe


def resolve_user_file(
    *,
    username: str,
    session_id: str,
    filename: str,
) -> Path:
    """校验归属与路径越界后解析会话上传文件的本地绝对路径。"""
    filename_path = Path(filename)
    if ".." in filename_path.parts or filename_path.name != filename:
        raise ValueError("非法文件名")
    uploads_dir = user_chat_uploads_dir(username, session_id).resolve()
    file_path = (uploads_dir / filename).resolve()
    if not file_path.is_relative_to(uploads_dir):
        raise ValueError("非法文件路径")
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError("文件不存在")
    return file_path


def resolve_uploaded_path(file_url: str) -> tuple[str, str] | None:
    """将 /static/ 上传 URL 或本地路径安全解析为 (username, absolute_path)。"""
    if file_url.startswith("/static/"):
        relative = file_url.removeprefix("/static/")
        parts = [p for p in relative.split("/") if p]
        if len(parts) >= 5 and parts[1] == "chat" and parts[3] == "uploads":
            username = parts[0]
            session_id = parts[2]
            filename = "/".join(parts[4:])
            if session_id and Path(session_id).name != session_id:
                return None
            user_dir = (WORKPLACE_DIR / username).resolve()
            file_path = (user_dir / "chat" / session_id / "uploads" / filename).resolve()
            if not file_path.is_relative_to(user_dir) or not file_path.exists():
                return None
            return username, str(file_path)
        return None

    try:
        local_path = Path(file_url).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not local_path.exists():
        return None
    try:
        relative_parts = local_path.relative_to(WORKPLACE_DIR).parts
        if len(relative_parts) >= 3 and relative_parts[1] == "chat":
            return relative_parts[0], str(local_path)
    except ValueError:
        pass
    return None


def read_uploaded_file_content(
    absolute_path: str,
    *,
    max_content_chars: int = MAX_FILE_CONTENT_CHARS,
) -> str:
    """读取 PDF、Word、Excel、CSV 或纯文本文档内容并按字符上限截断。"""
    path = Path(absolute_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {absolute_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {absolute_path}")

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
        content = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    elif suffix in {".txt", ".md", ".log"}:
        content = path.read_text(encoding="utf-8", errors="replace")
    elif suffix in {".xlsx", ".xls"}:
        import pandas as pd

        df = pd.read_excel(str(path), dtype=str, nrows=500)
        content = df.to_string(index=False)
    elif suffix in {".csv", ".tsv"}:
        import pandas as pd

        sep = "\t" if suffix == ".tsv" else ","
        df = pd.read_csv(str(path), sep=sep, dtype=str, nrows=500)
        content = df.to_string(index=False)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")

    if not content or not content.strip():
        logger.warning("[ChatFiles] 文档解析结果为空: path=%s", absolute_path)
        return "文件内容为空"
    truncated = len(content) > max_content_chars
    if truncated:
        content = content[:max_content_chars] + "\n\n[...文档内容过长，已截断...]"
    logger.info(
        "[ChatFiles] 文档已解析: file=%s suffix=%s chars=%d truncated=%s",
        path.name, suffix, len(content), truncated,
    )
    return content
