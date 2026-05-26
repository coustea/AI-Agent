"""聊天服务层：对话流、记忆管理、附件分析、文件上传。

统一入口：所有聊天相关业务逻辑通过 ChatUseCases 调用，
记忆操作直接委托 MemoryService，不再经过 ConversationStore 中转。
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator

from app.chat.agent import chat_stream
from app.chat.request import ChatHistoryMessage
from app.chat.runtime import (
    PreparedTutorTurn,
    _classify_attachments,
    build_user_message_record,
    prepare_tutor_turn,
)
from app.chat.schemas import TutorAgentContext, TutorState
from app.config import (
    MAX_ANALYZE_FILE_COUNT,
    MAX_ANALYZE_TOTAL_CHARS,
    MAX_DOCX_PARAGRAPHS_TO_READ,
    MAX_FILE_CONTENT_CHARS,
    MAX_IMAGE_ANALYZE_COUNT,
    MAX_PDF_PAGES_TO_READ,
    MAX_UPLOAD_FILES_PER_REQUEST,
)
from app.infra.logging import get_logger
from app.memory.service import MemoryService, get_memory_service
from app.chat.utils.files import FileStore, LocalFileStore
from app.chat.utils.vision import VisionService

logger = get_logger(__name__)


# ── 附件分析结果 ──


class AttachmentAnalysisResult:
    """附件分析结果。"""

    def __init__(self, *, images: list[dict[str, Any]], documents: list[dict[str, Any]]) -> None:
        self.images = images
        self.documents = documents

    @property
    def analysis_context(self) -> str:
        parts: list[str] = []
        for img in self.images:
            if desc := img.get("description", ""):
                parts.append(f"[图片] {desc}")
        for doc in self.documents:
            if summary := doc.get("summary", ""):
                parts.append(f"[文档] {summary}")
        return "\n".join(parts)


# ── 聊天消息 DTO ──


class AttachmentInfo:
    """附件信息。"""

    def __init__(self, *, url: str, type: str, name: str) -> None:
        self.url = url
        self.type = type
        self.name = name

    def model_dump(self) -> dict[str, Any]:
        return {"url": self.url, "type": self.type, "name": self.name}


class ChatMessageItem:
    """聊天消息 DTO。"""

    def __init__(self, *, id: int, role: str, content: str, attachments: list[AttachmentInfo] | None = None, tool_calls: list[dict[str, Any]] | None = None, teaching_diagram: dict[str, Any] | None = None, created_at: Any = None) -> None:
        self.id = id
        self.role = role
        self.content = content
        self.attachments = attachments
        self.tool_calls = tool_calls
        self.teaching_diagram = teaching_diagram
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "role": self.role, "content": self.content, "created_at": self.created_at}
        if self.attachments:
            d["attachments"] = [a.model_dump() for a in self.attachments]
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.teaching_diagram:
            d["teaching_diagram"] = self.teaching_diagram
        return d


# ── ChatUseCases ──


class ChatUseCases:
    """聊天用例：对话流、记忆管理、附件分析、文件上传。"""

    def __init__(self) -> None:
        self._memory_service = get_memory_service()
        self.file_store: FileStore = LocalFileStore()
        self._stream_runner = None
        self._bg_semaphore = asyncio.Semaphore(20)

    # ── 会话 ──

    def default_session_id(self, user_id: int) -> str:
        """生成默认会话ID。"""
        return f"user-{user_id}-default-mentor"

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """获取用户会话列表。"""
        sessions = await self._memory_service.list_sessions(user_id=user_id, limit=limit)
        return [
            {"id": s.id, "title": s.title, "updated_at": s.updated_at}
            for s in sessions
        ]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict[str, Any]:
        """创建新会话。"""
        session = await self._memory_service.create_session(user_id=user_id, title=title)
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        """归档会话。"""
        return await self._memory_service.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(self, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题。"""
        return await self._memory_service.update_session_title(user_id=user_id, session_id=session_id, title=title)

    # ── 消息 ──

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        """获取聊天历史。"""
        if not session_id:
            sessions = await self._memory_service.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        raw_messages = await self._memory_service.list_messages(user_id=user_id, session_id=session_id, limit=limit)
        result: list[ChatMessageItem] = []
        for m in raw_messages:
            parsed_attachments = None
            if m.attachments:
                try:
                    raw = m.attachments if isinstance(m.attachments, list) else json.loads(m.attachments)
                    parsed_attachments = [
                        AttachmentInfo(url=a.get("url", ""), type=a.get("type", ""), name=a.get("name", ""))
                        for a in raw
                    ]
                except Exception:
                    pass
            result.append(ChatMessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                attachments=parsed_attachments,
                tool_calls=m.tool_calls if isinstance(m.tool_calls, list) else None,
                teaching_diagram=m.teaching_diagram if isinstance(m.teaching_diagram, dict) else None,
                created_at=m.created_at,
            ))
        return result

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
    ) -> None:
        """保存消息到短期记忆。"""
        await self._memory_service.save_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            teaching_diagram=teaching_diagram,
        )

    async def count_messages(self, user_id: int, session_id: str) -> int:
        """统计会话消息数。"""
        return await self._memory_service.count_messages(user_id=user_id, session_id=session_id)

    # ── 附件分析 ──

    async def analyze_attachments_parallel(
        self,
        attachments: list[str],
        *,
        user_id: int,
        session_id: str,
    ) -> AttachmentAnalysisResult:
        """并行分析图片和文档附件。"""
        image_urls, file_urls = _classify_attachments(attachments)

        image_results: list[dict[str, Any]] = []
        document_results: list[dict[str, Any]] = []

        async def _analyze_images() -> None:
            nonlocal image_results
            if not image_urls:
                return
            vision = VisionService()
            try:
                image_results = await vision.analyze_images(
                    image_urls[:MAX_IMAGE_ANALYZE_COUNT],
                    session_id=session_id,
                    user_id=user_id,
                )
            except Exception as exc:
                logger.warning("[ChatUseCases] 图片分析失败: %s", exc)

        async def _analyze_documents() -> None:
            nonlocal document_results
            if not file_urls:
                return
            try:
                from app.chat.utils.files import analyze_documents
                document_results = await analyze_documents(
                    file_urls[:MAX_ANALYZE_FILE_COUNT],
                    max_total_chars=MAX_ANALYZE_TOTAL_CHARS,
                    max_file_content_chars=MAX_FILE_CONTENT_CHARS,
                    max_pdf_pages=MAX_PDF_PAGES_TO_READ,
                    max_docx_paragraphs=MAX_DOCX_PARAGRAPHS_TO_READ,
                )
            except Exception as exc:
                logger.warning("[ChatUseCases] 文档分析失败: %s", exc)

        await asyncio.gather(_analyze_images(), _analyze_documents())
        return AttachmentAnalysisResult(images=image_results, documents=document_results)

    async def _build_attachment_analysis(
        self,
        *,
        user_id: int,
        session_id: str,
        attachments: list[str],
    ) -> dict[str, Any] | None:
        """构建附件分析结果，用于 TutorAgent 上下文，并持久化到会话。"""
        if not attachments:
            return None
        try:
            result = await self.analyze_attachments_parallel(
                attachments,
                user_id=user_id,
                session_id=session_id,
            )
            ctx = result.analysis_context
            if not ctx.strip():
                return None
            analysis_data = {"analysis_context": ctx, "image_count": len(result.images), "document_count": len(result.documents)}
            # 持久化到会话
            self._spawn_background(
                self._memory_service.update_attachment_analyses(
                    user_id=user_id,
                    session_id=session_id,
                    analyses=analysis_data,
                ),
                label="persist_attachment_analyses",
            )
            return analysis_data
        except Exception as exc:
            logger.warning("[ChatUseCases] 附件分析失败: %s", exc)
            return None

    # ── 上下文构建 ──

    async def build_tutor_agent_context(
        self,
        *,
        user_id: int,
        user_message: str | None,
        session_id: str | None,
        attachments: list[str],
        enable_search: bool = False,
        enable_long_term_memory: bool = False,
        need_teaching_diagram: bool = False,
        history: list[ChatHistoryMessage] | None = None,
    ) -> TutorAgentContext:
        """构建 TutorAgent 所需的完整上下文。"""
        effective_session = session_id or self.default_session_id(user_id)

        # 附件分析
        attachment_analysis = await self._build_attachment_analysis(
            user_id=user_id,
            session_id=effective_session,
            attachments=attachments,
        )

        # 构建上下文
        file_info_str = self._memory_service.build_file_context(attachments)
        initial_messages, recent_chat_context = await self._memory_service.build_recent_chat_context(
            user_id=user_id,
            session_id=effective_session,
            user_message=user_message or "",
            attachments=attachments,
        )

        # 附件预分析上下文
        attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()

        # 拼接系统提示词
        from app.prompts import registry
        analysis_hint = (
            f"\n\n### 附件并行预分析结果\n{attachment_analysis_context}\n"
            if attachment_analysis_context
            else ""
        )
        system_prompt = registry.get("chat/tutor_system").format(
            recent_chat_context=recent_chat_context,
        ) + analysis_hint

        return TutorAgentContext(
            user_id=user_id,
            session_id=effective_session,
            attachments=attachments,
            enable_search=enable_search,
            enable_long_term_memory=enable_long_term_memory,
            need_teaching_diagram=need_teaching_diagram,
            file_context=file_info_str,
            recent_chat_context=recent_chat_context,
            attachment_analysis_context=attachment_analysis_context,
            attachment_analysis=attachment_analysis or {},
            system_prompt=system_prompt,
        )

    # ── 对话流 ──

    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str | None = None,
        history: list[ChatHistoryMessage] | None = None,
        session_id: str | None = None,
        attachments: list[str] | None = None,
        need_teaching_diagram: bool = False,
        generate_video: bool = False,
        enable_search: bool = False,
        enable_long_term_memory: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """SSE 流式对话主入口。"""
        effective_session = session_id or self.default_session_id(user_id)
        merged_attachments = list(dict.fromkeys(attachments or []))

        # 如果没有传 history，从记忆中构建上下文
        if history is not None:
            context = await self.build_tutor_agent_context(
                user_id=user_id,
                user_message=user_message,
                session_id=effective_session,
                attachments=merged_attachments,
                enable_search=enable_search,
                enable_long_term_memory=enable_long_term_memory,
                need_teaching_diagram=need_teaching_diagram,
                history=history,
            )
            state = prepare_tutor_state(context, history)
        else:
            context = await self.build_tutor_agent_context(
                user_id=user_id,
                user_message=user_message,
                session_id=effective_session,
                attachments=merged_attachments,
                enable_search=enable_search,
                enable_long_term_memory=enable_long_term_memory,
                need_teaching_diagram=need_teaching_diagram,
            )
            turn = prepare_tutor_turn(
                ctx_service=self._memory_service,
                user_id=user_id,
                user_message=user_message or "",
                session_id=effective_session,
                attachments=merged_attachments,
                enable_search=enable_search,
                enable_long_term_memory=enable_long_term_memory,
                need_teaching_diagram=need_teaching_diagram,
                attachment_analysis=context.attachment_analysis,
            )
            state = turn.initial_state

        # 保存用户消息
        user_record = build_user_message_record(
            user_message or "",
            attachments=merged_attachments,
        )
        await self.save_message(
            user_id=user_id,
            session_id=effective_session,
            role="user",
            content=user_record.content,
            attachments=user_record.attachments,
        )

        # 首条消息时自动生成标题
        msg_count = await self.count_messages(user_id, effective_session)
        if msg_count <= 1 and user_message:
            self._spawn_background(
                self._memory_service.generate_session_title(
                    user_id=user_id,
                    session_id=effective_session,
                    first_message=user_message,
                ),
                label="generate_title",
            )

        # 流式输出
        full_answer = ""
        async for event in chat_stream(state):
            if event.get("type") == "answer_delta":
                full_answer += event.get("text", "")
            yield event

        # 保存助手消息
        await self.save_message(
            user_id=user_id,
            session_id=effective_session,
            role="assistant",
            content=full_answer,
        )

        # 后台记忆管线
        if enable_long_term_memory and user_message:
            self._spawn_background(
                self._memory_service.after_turn(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=user_message,
                    assistant_reply=full_answer,
                    enable_long_term_memory=True,
                ),
                label="memory_pipeline",
            )

    # ── 文件上传 ──

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict[str, Any]:
        """保存上传文件并返回可访问信息。"""
        if not filename:
            raise ValueError("文件名不能为空")

        # 检查上传文件数限制
        existing = self.file_store.list_files(user_id=user_id, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")

        saved_path = await self.file_store.save(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )

        owner_id = user_id
        url = f"/api/v1/ai/chat/uploads/{owner_id}/{session_id}/{filename}"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        is_image = ext in {"png", "jpg", "jpeg", "gif", "webp"}
        return {
            "url": url,
            "type": "image" if is_image else "document",
            "name": filename,
            "size": len(content),
        }

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        """解析上传文件路径，带权限校验。"""
        if current_user_id != owner_id:
            raise PermissionError("无权访问此文件")
        return self.file_store.resolve(user_id=owner_id, session_id=session_id, filename=filename)

    # ── 后台任务 ──

    def _spawn_background(self, coro, *, label: str = "") -> None:
        """启动后台任务，受信号量控制。"""

        async def _run() -> None:
            async with self._bg_semaphore:
                try:
                    await coro
                except Exception as exc:
                    logger.error("[ChatUseCases] 后台任务失败 label=%s err=%s", label, exc)
                    # 最多重试 1 次
                    try:
                        await coro
                    except Exception as retry_exc:
                        logger.error("[ChatUseCases] 后台任务重试失败 label=%s err=%s", label, retry_exc)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.ensure_future(_run())
        else:
            logger.warning("[ChatUseCases] 无法在非事件循环中启动后台任务 label=%s", label)


# ── 模块级单例 ──

_chat_usecases: ChatUseCases | None = None
_avatar_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    """获取聊天用例单例。"""
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases


def get_avatar_chat_usecases() -> ChatUseCases:
    """获取数字人聊天用例单例。"""
    global _avatar_chat_usecases
    if _avatar_chat_usecases is None:
        _avatar_chat_usecases = ChatUseCases()
    return _avatar_chat_usecases


def prepare_tutor_state(context: TutorAgentContext, history: list[ChatHistoryMessage]) -> TutorState:
    """从上下文和历史构建 LangGraph 状态。"""
    from app.chat.runtime import prepare_tutor_state as _prepare
    return _prepare(context, history)
