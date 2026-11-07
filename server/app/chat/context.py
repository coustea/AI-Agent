"""Chat 上下文与附件存储 —— 负责上传文件落盘、历史消息清洗、s06 微压缩与本轮 Prompt 组装。"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from sqlmodel import select

from app.chat.memory import (
    extract_content_text,
    get_session_summary_context,
)
from app.chat.schemas import UploadResponse
from app.config import (
    CHAT_HISTORY_LIMIT,
    IMAGE_EXTENSIONS,
    MAX_UPLOAD_FILES_PER_REQUEST,
    WORKPLACE_DIR,
    chat_upload_url,
    user_chat_uploads_dir,
)
from app.evaluation.guidance import get_effective_guidance_strategy
from app.infra.database import session_scope
from app.infra.llm import (
    AIMessage,
    HumanMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    load_prompt,
)
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock, UserProfile

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "tutor_agent.md"
MAX_FILE_CONTENT_CHARS = 15000


# ===========================================================================
# 1. 本地文件上传存储与文档解析
# ===========================================================================


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


class LocalFileStore:
    """用户会话上传文件的本地沙箱存储（static/{username}/chat/{session_id}/uploads/）。"""

    def __init__(self) -> None:
        """初始化允许上传的图片/文档扩展名与大小限制。"""
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.allowed_doc_ext = {
            ".pdf", ".docx", ".txt", ".md", ".log",
            ".xlsx", ".xls", ".csv", ".tsv",
        }
        self.max_image_size = 5 * 1024 * 1024
        self.max_doc_size = 10 * 1024 * 1024

    def list_files(self, *, username: str, session_id: str) -> list[Path]:
        """列出指定用户与会话下已上传的全部文件。"""
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
        """校验并将用户上传文件写入会话 uploads 目录，返回 UploadResponse 字典。"""
        if not filename:
            raise ValueError("文件名不能为空")
        existing = self.list_files(username=username, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")

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
        """过滤文件名中的非法路径字符并限制最大长度。"""
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
        """校验归属与路径越界后解析会话上传文件的本地绝对路径。"""
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


def read_uploaded_file_content(
    absolute_path: str,
    *,
    max_content_chars: int = MAX_FILE_CONTENT_CHARS,
    max_pdf_pages: int | None = None,
    max_docx_paragraphs: int | None = None,
) -> str:
    """读取 PDF、Word、Excel、CSV 或纯文本文档内容并按字符上限截断。"""
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
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md, .log, .xlsx, .xls, .csv, .tsv）"

    if not content or not content.strip():
        return "文件内容为空"
    if len(content) > max_content_chars:
        content = content[:max_content_chars] + "\n\n[...文档内容过长，已截断...]"
    return content


# ===========================================================================
# 2. 消息格式转换、工具链清洗与 s06 Micro-compact
# ===========================================================================


def build_user_content(text: str, attachments: list[Any]) -> list[dict[str, Any]]:
    """构建用户消息的持久化 content 列表（含文本段与原始附件元信息段）。"""
    content: list[dict[str, Any]] = []
    if text.strip():
        content.append({"type": "text", "text": text.strip()})
    for attachment in attachments:
        def _val(name: str, default: Any = None) -> Any:
            """从字典或对象属性中提取字段值。"""
            if isinstance(attachment, dict):
                return attachment.get(name, default)
            return getattr(attachment, name, default)

        url = str(_val("url", "") or "")
        file_type = str(_val("file_type", "") or "")
        item: dict[str, Any] = {
            "type": "image_url" if file_type == "image" else "file",
            "url": url,
            "file_type": file_type,
            "original_name": str(_val("original_name", "") or url.rsplit("/", 1)[-1]),
            "mime_type": _val("mime_type"),
            "size_bytes": int(_val("size_bytes", 0) or 0),
        }
        if file_type == "image":
            item["image_url"] = {"url": url}
        else:
            item["file"] = {"filename": item["original_name"], "file_id": url}
        content.append(item)
    return content


def normalize_tool_calls(tool_calls: list[dict[str, Any]] | None) -> list[ToolCall]:
    """将数据库存储的 tool_calls 列表标准化为 ToolCall 对象列表。"""
    normalized: list[ToolCall] = []
    for tc in tool_calls or []:
        if not isinstance(tc, dict):
            continue
        tool_id = str(tc.get("id", ""))
        tool_name = str(tc.get("name", ""))
        if not tool_id or not tool_name:
            continue
        raw_args = tc.get("args", {})
        args_dict = raw_args if isinstance(raw_args, dict) else {}
        normalized.append(
            ToolCall(
                id=tool_id,
                name=tool_name,
                args=args_dict,
                raw_arguments=json.dumps(args_dict, ensure_ascii=False),
            )
        )
    return normalized


def convert_stored_message(message: Any) -> Message | None:
    """将单条数据库 ChatMessage 转换为发往 LLM 的 Message 对象。"""
    role = getattr(message, "role", "")
    raw_content = getattr(message, "content", "")
    tool_calls = getattr(message, "tool_calls", None)
    tool_call_id = getattr(message, "tool_call_id", None)

    if role == "user":
        if isinstance(raw_content, list) and raw_content:
            text_parts: list[str] = []
            attachment_notes: list[str] = []
            for part in raw_content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype == "text":
                    t = str(part.get("text") or "").strip()
                    if t:
                        text_parts.append(t)
                elif ptype in {"image_url", "file"}:
                    url = str(part.get("url") or "")
                    name = str(part.get("original_name") or url.rsplit("/", 1)[-1])
                    if url:
                        attachment_notes.append(f"[历史上传文件: {name} ({url})]")
            combined = "\n".join([*text_parts, *attachment_notes]).strip()
            return HumanMessage(content=combined) if combined else None
        text = str(raw_content or "").strip()
        return HumanMessage(content=text) if text else None

    if role in {"assistant", "ai"}:
        text_content = extract_content_text(raw_content).strip()
        if tool_calls:
            normalized_tc = normalize_tool_calls(tool_calls)
            if normalized_tc:
                return AIMessage(content=text_content, tool_calls=normalized_tc)
        return AIMessage(content=text_content) if text_content else None

    if role == "system":
        text_content = extract_content_text(raw_content).strip()
        return SystemMessage(content=text_content) if text_content else None

    if role == "tool" and tool_call_id:
        text_content = extract_content_text(raw_content).strip()
        return ToolMessage(content=text_content or "", tool_call_id=str(tool_call_id))
    return None


def sanitize_tool_message_chain(messages: list[Message]) -> list[Message]:
    """校验并清理孤立的 tool_calls 与 ToolMessage，确保满足 OpenAI 消息配对约束。"""
    result: list[Message] = []
    valid_tool_call_ids: set[str] = set()

    for msg in messages:
        if msg.role == "assistant" and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.id and tc.name:
                    valid_tool_call_ids.add(tc.id)
            valid_tc = tuple(tc for tc in msg.tool_calls if tc.id in valid_tool_call_ids)
            if valid_tc or msg.content:
                result.append(AIMessage(msg.content or "", tool_calls=valid_tc))
        elif msg.role == "tool":
            if msg.tool_call_id in valid_tool_call_ids:
                result.append(msg)
        else:
            result.append(msg)
    return result


def prune_tool_messages(
    messages: list[Message],
    *,
    keep_recent_turns: int = 2,
    max_chars: int = 300,
) -> list[Message]:
    """执行 s06 Micro-compact：裁剪早期轮次中冗长的 ToolMessage 输出，防止撑爆上下文窗口。"""
    turn_indices = [i for i, m in enumerate(messages) if m.role == "user"]
    recent_turn_start = turn_indices[-keep_recent_turns] if len(turn_indices) >= keep_recent_turns else 0

    pruned: list[Message] = []
    for i, m in enumerate(messages):
        if m.role == "tool" and i < recent_turn_start:
            content_str = str(m.content or "")
            if len(content_str) > max_chars:
                pruned.append(
                    ToolMessage(
                        content=f"[Tool output pruned: 原始长 {len(content_str)} 字符]\n{content_str[:max_chars]}...",
                        tool_call_id=m.tool_call_id or "",
                    )
                )
                continue
        pruned.append(m)
    return pruned


# ===========================================================================
# 3. 历史加载与本轮完整消息链构建
# ===========================================================================


async def build_history_messages(
    user_id: int,
    session_id: str,
    *,
    exclude_message_id: int | None = None,
) -> list[Message]:
    """从数据库读取未压缩的历史消息，执行工具链清洗与 s06 Micro-compact 裁剪。"""
    async with session_scope() as db:
        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        summarized_through_id = int(latest_block.end_message_id or 0) if latest_block else 0

        stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.id > summarized_through_id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(CHAT_HISTORY_LIMIT)
        )
        raw_messages = list(reversed((await db.exec(stmt)).all()))

    if exclude_message_id is not None:
        raw_messages = [m for m in raw_messages if getattr(m, "id", None) != exclude_message_id]

    if raw_messages and getattr(raw_messages[0], "role", "") != "user":
        first_user_idx = next(
            (i for i, m in enumerate(raw_messages) if getattr(m, "role", "") == "user"),
            len(raw_messages),
        )
        raw_messages = raw_messages[first_user_idx:]

    converted = [m for msg in raw_messages if (m := convert_stored_message(msg)) is not None]
    sanitized = sanitize_tool_message_chain(converted)
    return prune_tool_messages(sanitized)


async def _load_agent_md(user_id: int) -> str:
    """读取用户的 AGENT.md 学习档案文本。"""
    try:
        async with session_scope() as db:
            result = await db.execute(
                select(UserProfile.agent_md).where(UserProfile.user_id == user_id)
            )
            return (result.scalar_one_or_none() or "").strip()
    except Exception:
        return ""


async def _load_guidance_strategy(user_id: int) -> dict[str, Any] | None:
    """读取用户当前生效的个性化辅导策略。"""
    try:
        async with session_scope() as db:
            return await get_effective_guidance_strategy(db, user_id)
    except Exception:
        return None


def _format_attachment_manifest(attachments: list[str]) -> str:
    """生成本轮上传附件的路径与类型清单，引导 Agent 自主调用对应工具。"""
    if not attachments:
        return ""
    lines = [f"[上传附件]\n学生本轮上传了 {len(attachments)} 个文件："]
    has_image = False
    has_doc = False
    for url in attachments:
        filename = url.rsplit("/", 1)[-1]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in IMAGE_EXTENSIONS:
            has_image = True
            lines.append(f"- 图片: `{url}` (文件名: `{filename}`)")
        else:
            has_doc = True
            lines.append(f"- 文档: `{url}` (文件名: `{filename}`)")
    if has_image:
        lines.append("请调用 `view_image(path=..., question=...)` 查看图片，并结合学生提问写出你想从图片中获取的具体信息。")
    if has_doc:
        lines.append("请调用 `read_document(path=...)` 读取文档内容。")
    return "\n".join(lines)


async def build_turn_messages(
    *,
    user_id: int,
    session_id: str,
    user_message_id: int,
    question: str,
    attachments: list[str],
    diagram_mode: str = "auto",
    video_mode: bool = False,
) -> list[Message]:
    """并行加载历史、会话摘要、辅导策略与学习档案，组装本轮完整 Message 列表。"""
    history, session_summary, strategy, agent_md = await asyncio.gather(
        build_history_messages(user_id, session_id, exclude_message_id=user_message_id),
        get_session_summary_context(user_id, session_id),
        _load_guidance_strategy(user_id),
        _load_agent_md(user_id),
    )

    blocks: list[str] = [f"[当前日期]\n{datetime.now().date().isoformat()}"]
    if session_summary:
        blocks.append(f"[会话摘要]\n{session_summary}")
    if attachments:
        blocks.append(_format_attachment_manifest(attachments))
    if video_mode:
        blocks.append(
            "[本轮必须生成视频]\n"
            "学生已在前端勾选视频，本轮必须调用 `generate_teaching_video` 工具产出一个教学视频。\n"
            "视频生成成功后，用 2-3 句话简要说明视频讲了什么，不要再长篇复述内容。"
        )
    elif diagram_mode == "required":
        blocks.append(
            "[本轮必须生成图解]\n"
            "学生已在前端勾选图解，本轮回答必须包含一个 ```mermaid 代码块。\n"
            "图解放在回答开头或紧接结论之后，正文用 2-4 句话简要说明关键点，不要长篇展开。"
        )
    if strategy:
        blocks.append(
            "[辅导策略]\n"
            f"本期结论: {strategy.get('conclusion')}\n"
            f"推荐单次时长: {strategy.get('recommended_session_minutes')} 分钟\n"
            f"辅导风格: {strategy.get('tutoring_style')}\n"
            f"重点关注主题: {'、'.join(strategy.get('focus_topics', [])) or '无'}\n"
            f"策略依据: {strategy.get('reason')}"
        )
    if agent_md:
        blocks.append(f"[我的学习档案]\n{agent_md}")

    dynamic_context = "\n\n".join(blocks)
    human_text = f"{question}\n\n{dynamic_context}" if dynamic_context else question

    return [
        SystemMessage(load_prompt(_PROMPT_PATH)),
        *history,
        HumanMessage(human_text),
    ]


__all__ = [
    "LocalFileStore",
    "MAX_FILE_CONTENT_CHARS",
    "build_history_messages",
    "build_turn_messages",
    "build_user_content",
    "convert_stored_message",
    "normalize_tool_calls",
    "prune_tool_messages",
    "read_uploaded_file_content",
    "resolve_uploaded_path",
    "sanitize_tool_message_chain",
]
