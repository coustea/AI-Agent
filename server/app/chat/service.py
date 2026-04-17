"""Chat application service boundary.

集中保留 chat 的应用层编排，明确主链路为：api -> service -> agent
- 文件/图片处理接口
- ConversationStore: 会话/历史持久化
- ChatUseCases: 路由入口与 agent 调用
- get_chat_usecases: 模块装配
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.memory.short_term import short_term_service
from app.memory.session import session_service
from app.shared.storage import local_file_store
from app.shared.paths import WORKPLACE_DIR
from app.shared.spark_image import spark_image_service
from app.infra.logging import get_logger

from app.chat.context import chat_runtime_context
from app.chat.schemas import AttachmentInfo, ChatMessageItem, ToolCallRecord

CHAT_MODULE_NAME = "mentor"
logger = get_logger(__name__)
UPLOAD_DIR = WORKPLACE_DIR / "chat-uploads"
MAX_FILE_CONTENT_CHARS = 15000


def format_sse(event: str, data: Any) -> str:
    """Encode a single SSE frame."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    lines = payload.splitlines() or [""]
    body = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{body}\n\n"


def resolve_uploaded_path(file_url: str) -> tuple[int, str] | None:
    relative: str
    if file_url.startswith("/api/v1/ai/chat/uploads/"):
        relative = file_url.removeprefix("/api/v1/ai/chat/uploads/")
    elif file_url.startswith("/uploads/"):
        relative = file_url.removeprefix("/uploads/")
    else:
        # 支持直接传本地绝对路径（chat-uploads/<user>/<session>/<file>）
        try:
            local_path = Path(file_url).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            return None
        upload_root = UPLOAD_DIR.resolve()
        if not str(local_path).startswith(str(upload_root)):
            return None
        if not local_path.exists():
            return None
        relative_parts = local_path.relative_to(upload_root).parts
        if len(relative_parts) == 3:
            owner_part, session_id, filename = relative_parts
        elif len(relative_parts) == 2:
            owner_part, filename = relative_parts
            session_id = ""
        else:
            return None
        if not owner_part.isdigit():
            return None
        if session_id and Path(session_id).name != session_id:
            return None
        if Path(filename).name != filename:
            return None
        return int(owner_part), str(local_path)

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
    resolved = resolve_uploaded_path(image_url)
    if resolved is None:
        return None
    _, absolute_path = resolved
    path = Path(absolute_path)
    return path if path.is_file() else None


def read_uploaded_file_content(absolute_path: str) -> str:
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
        content = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
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


async def analyze_documents(*, current_user_id: int, file_urls: list[str], question: str) -> dict:
    documents: list[dict[str, str]] = []
    snippets: list[str] = []

    for file_url in file_urls:
        resolved = resolve_uploaded_path(file_url)
        if resolved is None:
            logger.warning("[DocumentAnalysis] failed to resolve %s", file_url)
            continue

        owner_id, absolute_path = resolved
        if owner_id != current_user_id:
            logger.warning("[DocumentAnalysis] forbidden file access user=%s owner=%s", current_user_id, owner_id)
            continue

        content = read_uploaded_file_content(absolute_path)
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

    analysis_text = (
        f"用户问题：{question or '请分析这些文档'}\n\n"
        "以下是已提取的文档内容，请基于它们回答用户问题，并在回答中尽量提炼知识点：\n\n"
        + "\n\n".join(snippets)
    )
    return {
        "success": True,
        "documents": documents,
        "analysis_text": analysis_text,
        "error": None,
    }


class VisionService:
    def __init__(self, glm_vision_llm):
        self.glm_vision_llm = glm_vision_llm

    async def analyze_images(self, image_urls: list[str], question: str) -> dict:

        if spark_image_service.configured and image_urls:
            spark_results: list[str] = []
            spark_ok = True
            for url in image_urls:
                image_path = resolve_uploaded_image_path(url)
                if not image_path:
                    spark_ok = False
                    break
                try:
                    image_bytes = image_path.read_bytes()
                    result = await spark_image_service.analyze(image_bytes, question)
                    if result:
                        spark_results.append(result)
                    else:
                        spark_ok = False
                        break
                except Exception as exc:
                    logger.warning("[VisionService] spark failed, fallback to glm: %s", exc)
                    spark_ok = False
                    break

            if spark_ok and spark_results:
                combined = "\n\n".join(spark_results) if len(spark_results) > 1 else spark_results[0]
                return {
                    "success": True,
                    "mode": "spark",
                    "analysis_text": combined,
                    "messages": None,
                    "error": None,
                }

        content_blocks: list[dict] = [{"type": "text", "text": question or "请描述这些图片"}]
        for url in image_urls:
            content_blocks.append({"type": "image_url", "image_url": {"url": url}})
        response = await self.glm_vision_llm.ainvoke([HumanMessage(content=content_blocks)])
        return {
            "success": True,
            "mode": "glm",
            "analysis_text": response.content if isinstance(response.content, str) else str(response.content),
            "messages": [SystemMessage(content=""), response],
            "error": None,
        }


class ConversationStore:
    """对话会话与历史持久化。"""

    async def list_sessions(self, user_id: int, limit: int = 30) -> list[dict]:
        sessions = await session_service.get_user_chat_sessions(
            user_id=user_id,
            module=CHAT_MODULE_NAME,
            limit=limit,
        )
        return [{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict:
        session = await session_service.create_chat_session(
            user_id=user_id,
            module=CHAT_MODULE_NAME,
            title=title,
        )
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        return await session_service.archive_chat_session(session_id, user_id)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        target_session = session_id
        if not target_session:
            sessions = await session_service.get_user_chat_sessions(
                user_id=user_id,
                module=CHAT_MODULE_NAME,
                limit=1,
            )
            if not sessions:
                return []
            target_session = sessions[0].id

        messages = await short_term_service.get_recent_messages(
            user_id=user_id,
            session_id=target_session,
            module=CHAT_MODULE_NAME,
            limit=limit,
        )

        items: list[ChatMessageItem] = []
        for msg in messages:
            attachments = None
            if msg.attachments:
                try:
                    attachments = [AttachmentInfo(**v) for v in json.loads(msg.attachments)]
                except (json.JSONDecodeError, TypeError):
                    attachments = None

            tool_calls = None
            if msg.tool_calls:
                try:
                    tool_calls = [ToolCallRecord(**v) for v in json.loads(msg.tool_calls)]
                except (json.JSONDecodeError, TypeError):
                    tool_calls = None

            items.append(
                ChatMessageItem(
                    role=msg.role,
                    content=msg.content,
                    attachments=attachments,
                    tool_calls=tool_calls,
                    created_at=msg.created_at,
                )
            )
        return items


class ChatUseCases:
    """路由层可调用的 chat 应用入口。"""

    def __init__(
        self,
        *,
        conversation_store: ConversationStore,
        file_store=local_file_store,
    ) -> None:
        self.conversation_store = conversation_store
        self.file_store = file_store

    @staticmethod
    def default_session_id(user_id: int) -> str:
        return f"user-{user_id}-default-{CHAT_MODULE_NAME}"

    async def prepare_uploads(
        self,
        *,
        files: list[tuple[str, bytes]],
        user_id: int,
        session_id: str | None = None,
    ) -> tuple[str, list[str], list[str]]:
        effective_session = session_id or self.default_session_id(user_id)
        image_urls: list[str] = []
        file_urls: list[str] = []

        for filename, content in files:
            if not filename:
                raise ValueError("文件名不能为空")
            saved = await self.save_upload(
                filename=filename,
                content=content,
                user_id=user_id,
                session_id=effective_session,
            )
            if saved["file_type"] == "image":
                image_urls.append(saved["url"])
            else:
                file_urls.append(saved["url"])

        return effective_session, image_urls, file_urls

    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ):

        effective_session = session_id or self.default_session_id(user_id)
        # Delay import to avoid the service <-> agent circular import at module load time.
        from app.chat.agent import TutorAgent

        agent = TutorAgent.get_shared()
        with chat_runtime_context(user_id, effective_session):
            async for event in agent.chat_stream(
                user_id=user_id,
                user_message=user_message,
                session_id=effective_session,
                image_urls=image_urls,
                file_urls=file_urls,
            ):
                yield format_sse(event["event"], event["data"])

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict:
        return await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ):
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self.conversation_store.list_sessions(user_id, limit)

    async def create_session(self, user_id: int, title: str = "新对话") -> dict:
        return await self.conversation_store.create_session(user_id, title)

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        return await self.conversation_store.archive_session(user_id, session_id)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ):
        return await self.conversation_store.get_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )


def build_vision_service(glm_vision_llm):
    return VisionService(glm_vision_llm)


conversation_store = ConversationStore()
chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    global chat_usecases
    if chat_usecases is None:
        chat_usecases = ChatUseCases(
            conversation_store=conversation_store,
        )
    return chat_usecases


__all__ = [
    "CHAT_MODULE_NAME",
    "ChatUseCases",
    "ConversationStore",
    "format_sse",
    "chat_usecases",
    "conversation_store",
    "get_chat_usecases",
    "resolve_uploaded_path",
    "resolve_uploaded_image_path",
    "read_uploaded_file_content",
    "analyze_documents",
    "build_vision_service",
]
