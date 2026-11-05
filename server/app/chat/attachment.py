"""Chat 附件全生命周期处理 —— 上传存储、安全路径解析、文档读取、视觉图片理解与预处理编排。"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
from mimetypes import guess_type
from pathlib import Path
import re
from typing import Any, Awaitable, Callable
from uuid import uuid4

from app.chat.schemas import UploadResponse
from app.chat.stream import build_attachment_status_payload
from app.config import (
    IMAGE_EXTENSIONS,
    WORKPLACE_DIR,
    chat_upload_url,
    user_chat_uploads_dir,
)
from app.infra.llm import HumanMessage, LLM
from app.infra.logging import get_logger

logger = get_logger(__name__)

MAX_FILE_CONTENT_CHARS = 15000
_MAX_ATTACHMENTS = 5


# ── 1. 本地文件上传存储 ───────────────────────────────────────────────────────


class LocalFileStore:
    """用户上传文件的本地磁盘存储（按用户/会话隔离）。

    目录结构: static/{username}/chat/{session_id}/uploads/{filename}
    """

    def __init__(self) -> None:
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.allowed_doc_ext = {
            ".pdf", ".docx", ".txt", ".md", ".log",
            ".xlsx", ".xls", ".csv", ".tsv",
        }
        self.max_image_size = 5 * 1024 * 1024
        self.max_doc_size = 10 * 1024 * 1024

    def list_files(self, *, username: str, session_id: str) -> list[Path]:
        uploads_dir = user_chat_uploads_dir(username, session_id)
        if not uploads_dir.exists():
            return []
        return [path for path in uploads_dir.iterdir() if path.is_file()]

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        username: str,
        session_id: str,
    ) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower()
        if suffix in self.allowed_image_ext:
            file_type, max_size = "image", self.max_image_size
        elif suffix in self.allowed_doc_ext:
            file_type, max_size = "document", self.max_doc_size
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")

        if len(content) > max_size:
            raise ValueError(f"文件大小超过限制（{max_size // (1024 * 1024)}MB）")

        uploads_dir = user_chat_uploads_dir(username, session_id)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_filename(filename)
        if not safe_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = f"{timestamp}{suffix}"

        file_path = uploads_dir / safe_name
        if file_path.exists():
            file_path = uploads_dir / f"{file_path.stem}-{uuid4().hex[:8]}{file_path.suffix}"
            safe_name = file_path.name
        file_path.write_bytes(content)

        return UploadResponse(
            url=chat_upload_url(username, session_id, safe_name),
            file_type=file_type,
            original_name=filename,
            size_bytes=len(content),
            mime_type=_guess_mime_type(suffix),
        ).model_dump()

    def _safe_filename(self, filename: str) -> str:
        safe = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        if len(safe) > 100:
            name, ext = Path(safe).stem, Path(safe).suffix
            safe = f"{name[: 100 - len(ext)]}{ext}"
        return safe

    def resolve_user_file(
        self,
        *,
        current_username: str,
        owner_username: str,
        session_id: str,
        filename: str,
    ) -> Path:
        if owner_username != current_username:
            raise PermissionError("无权访问该文件")

        filename_path = Path(filename)
        if ".." in filename_path.parts or filename_path.name != filename:
            raise ValueError("非法文件名")

        uploads_dir = user_chat_uploads_dir(owner_username, session_id).resolve()
        file_path = (uploads_dir / filename).resolve()
        if not str(file_path).startswith(str(uploads_dir)):
            raise ValueError("非法文件路径")
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("文件不存在")
        return file_path


def _guess_mime_type(suffix: str) -> str:
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


# ── 2. 上传路径安全解析与文档读取 ─────────────────────────────────────────────


def resolve_uploaded_path(file_url: str) -> tuple[str, str] | None:
    """将 URL 路径解析为 (username, absolute_path)，校验路径安全性与文件存在性。

    标准格式: /static/{username}/chat/{session_id}/uploads/{filename}
    """
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
            if not str(file_path).startswith(str(user_dir)) or not file_path.exists():
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


def resolve_uploaded_image_path(image_url: str) -> Path | None:
    """解析图片 URL 为本地 Path。"""
    resolved = resolve_uploaded_path(image_url)
    if resolved is None:
        return None
    _, absolute_path = resolved
    path = Path(absolute_path)
    return path if path.is_file() else None


def read_uploaded_file_content(
    absolute_path: str,
    *,
    max_content_chars: int = MAX_FILE_CONTENT_CHARS,
    max_pdf_pages: int | None = None,
    max_docx_paragraphs: int | None = None,
) -> str:
    """读取上传文档内容并按字符上限截断。"""
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
            pages = doc if max_pdf_pages is None else list(doc)[:max_pdf_pages]
            for page in pages:
                text_parts.append(page.get_text())
        content = "\n".join(text_parts)
    elif suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        paragraphs = doc.paragraphs if max_docx_paragraphs is None else doc.paragraphs[:max_docx_paragraphs]
        content = "\n".join(para.text for para in paragraphs if para.text.strip())
    elif suffix in {".txt", ".md", ".log"}:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
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
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md, .log, .xlsx, .xls, .csv, .tsv）"

    if not content or not content.strip():
        return "文件内容为空"
    if len(content) > max_content_chars:
        content = content[:max_content_chars] + "\n\n[...文档内容过长，已截断...]"
    return content


async def analyze_documents(
    *,
    current_username: str,
    file_urls: list[str],
    question: str,
    max_total_chars: int = 40000,
    max_file_content_chars: int = MAX_FILE_CONTENT_CHARS,
    max_pdf_pages: int | None = None,
    max_docx_paragraphs: int | None = None,
) -> dict[str, Any]:
    """批量读取用户上传的文档内容并拼接为分析上下文。"""
    documents: list[dict[str, str]] = []
    snippets: list[str] = []

    for file_url in file_urls:
        resolved = resolve_uploaded_path(file_url)
        if resolved is None:
            continue
        owner_username, absolute_path = resolved
        if owner_username != current_username:
            continue

        content = read_uploaded_file_content(
            absolute_path,
            max_content_chars=max_file_content_chars,
            max_pdf_pages=max_pdf_pages,
            max_docx_paragraphs=max_docx_paragraphs,
        )
        documents.append({
            "url": file_url,
            "name": Path(absolute_path).name,
            "absolute_path": absolute_path,
            "content": content,
        })
        snippets.append(f"文件《{Path(absolute_path).name}》内容如下：\n{content}")

    if not documents:
        return {
            "success": False,
            "documents": [],
            "analysis_text": "未能读取可分析的文档内容。",
            "error": "未找到可访问的文档。",
        }

    joined = "\n\n".join(snippets)
    if len(joined) > max_total_chars:
        joined = joined[:max_total_chars] + "\n\n[...文档总内容过长，已截断...]"

    analysis_text = (
        f"用户问题：{question or '请分析这些文档'}\n\n"
        "以下是已提取的文档内容，请基于它们回答用户问题，并在回答中尽量提炼知识点：\n\n"
        + joined
    )
    return {
        "success": True,
        "documents": documents,
        "analysis_text": analysis_text,
        "error": None,
    }


# ── 3. 视觉模型图片分析 ───────────────────────────────────────────────────────


def _build_image_input(url: str) -> dict[str, Any] | None:
    """将图片 URL 构造为视觉模型可识别的 image_url content block。"""
    image_path = resolve_uploaded_image_path(url)
    if image_path and image_path.is_file():
        mime_type = guess_type(image_path.name)[0] or "image/png"
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
    if not url:
        return None
    return {"type": "image_url", "image_url": {"url": url}}


async def analyze_images(image_urls: list[str], question: str) -> str:
    """调用系统视觉模型 (vision) 分析上传的图片列表。"""
    content_blocks: list[dict[str, Any]] = [
        {"type": "text", "text": question or "请描述这些图片"}
    ]
    for url in image_urls:
        block = _build_image_input(url)
        if block:
            content_blocks.append(block)
    llm = LLM(provider="vision", temperature=0.7)
    return (await llm.vision([HumanMessage(content=content_blocks)])).strip()


# ── 4. 对话轮前附件预处理编排 ─────────────────────────────────────────────────


@dataclass(slots=True)
class AttachmentContext:
    """附件分析产出的上下文与错误列表。"""

    text: str = ""
    errors: list[str] = field(default_factory=list)


async def analyze_attachments(
    *,
    attachments: list[str],
    user_id: int,
    username: str,
    session_id: str,
    user_message_id: int,
    memory_service: Any,
    emit: Callable[[dict[str, Any]], Awaitable[None]],
) -> AttachmentContext:
    """分析本轮上传的图片与文档，持久化分析记录并推送状态事件。"""
    result = AttachmentContext()
    if not attachments:
        return result

    image_urls: list[str] = []
    file_urls: list[str] = []
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            file_urls.append(url)

    groups = (("image", image_urls), ("document", file_urls))
    records: dict[str, Any] = {}
    analysis_results: dict[str, str] = {}
    analysis_errors: dict[str, str] = {}

    for index, (kind, urls) in enumerate(groups):
        if not urls:
            continue
        records[kind] = await memory_service.create_attachment_analysis(
            user_id=user_id,
            session_id=session_id,
            user_message_id=user_message_id,
            analysis_type=kind,
        )
        await emit({
            "event": "agent_status",
            "data": build_attachment_status_payload(
                activity_id=f"attachment-{kind}-{index}",
                status="running",
                file_names=[u.split("/")[-1] for u in urls],
                analysis_type=kind,
            ),
        })

    if image_urls:
        try:
            text = await analyze_images(
                image_urls[:_MAX_ATTACHMENTS],
                "请详细分析这些图片中的文字、题目、图表和关键信息，并用中文总结。",
            )
            if text:
                analysis_results["image"] = text
                await memory_service.finish_attachment_analysis(
                    analysis_id=str(records["image"].id), content=text,
                )
            else:
                analysis_errors["image"] = "未提取到可用内容"
        except Exception as exc:
            logger.warning("[Attachment] 图片分析失败: %s", exc)
            analysis_errors["image"] = str(exc)
        if "image" in analysis_errors:
            await memory_service.finish_attachment_analysis(
                analysis_id=str(records["image"].id),
                content="",
                error_message=analysis_errors["image"],
            )

    if file_urls:
        try:
            analysis = await analyze_documents(
                current_username=username,
                file_urls=file_urls[:_MAX_ATTACHMENTS],
                question="请分析这些文档",
            )
            summary = str(analysis.get("analysis_text") or "").strip()
            if analysis.get("success") and summary:
                analysis_results["document"] = summary
                await memory_service.finish_attachment_analysis(
                    analysis_id=str(records["document"].id), content=summary,
                )
            else:
                analysis_errors["document"] = str(analysis.get("error") or "未提取到可用内容")
        except Exception as exc:
            logger.warning("[Attachment] 文档分析失败: %s", exc)
            analysis_errors["document"] = str(exc)
        if "document" in analysis_errors:
            await memory_service.finish_attachment_analysis(
                analysis_id=str(records["document"].id),
                content="",
                error_message=analysis_errors["document"],
            )

    result.text = "\n".join(
        f"[{'图片' if kind == 'image' else '文档'}] {content}"
        for kind, content in analysis_results.items()
    )
    result.errors = [f"{k}: {v}" for k, v in analysis_errors.items()]

    for index, (kind, urls) in enumerate(groups):
        if not urls:
            continue
        ok = kind in analysis_results
        await emit({
            "event": "agent_status",
            "data": build_attachment_status_payload(
                activity_id=f"attachment-{kind}-{index}",
                status="done" if ok else "failed",
                file_names=[str(u).split("/")[-1] for u in urls],
                analysis_type=kind,
                summary=analysis_results.get(kind, "") if ok else "",
                error=analysis_errors.get(kind, "未提取到可用内容") if not ok else "",
            ),
        })

    return result


__all__ = [
    "AttachmentContext",
    "LocalFileStore",
    "MAX_FILE_CONTENT_CHARS",
    "analyze_attachments",
    "analyze_documents",
    "analyze_images",
    "read_uploaded_file_content",
    "resolve_uploaded_image_path",
    "resolve_uploaded_path",
]
