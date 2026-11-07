"""聊天服务层 — 运行入口、记忆管理、文件上传。

核心函数：
  run_chat()  — 构建历史与摘要上下文 → ChatRun 驱动 harness → 返回 run_id

ChatUseCases 保留会话管理、文件上传、历史查询等辅助功能，对话核心逻辑在
``app.chat.harness`` 中。
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.attachment import LocalFileStore
from app.chat.context import ChatContextBuilder, build_user_content
from app.chat.harness.events import load_run_state
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import ChatMessageItem, DiagramMode
from app.config import MAX_UPLOAD_FILES_PER_REQUEST
from app.evaluation.event_types import CHAT_DIALOGUE, MODULE_CHAT
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.logging import get_logger
from app.infra.models import ChatSessionSummaryBlock

logger = get_logger(__name__)


async def record_dialogue_event(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    summary_text: str | None = None,
    turn_count: int = 1,
) -> None:
    """记录一次辅导对话埋点事件。"""
    if summary_text is None:
        stmt = (
            select(ChatSessionSummaryBlock.summary_markdown)
            .where(ChatSessionSummaryBlock.session_id == session_id)
            .order_by(ChatSessionSummaryBlock.created_at.desc())
            .limit(1)
        )
        summary_text = (await db.exec(stmt)).first() or ""

    payload = LearningEventCreate(
        module=MODULE_CHAT,
        entity_id=session_id,
        event_type=CHAT_DIALOGUE,
        event_metadata={
            "summary_length": len(summary_text or ""),
            "turn_count": turn_count,
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)

# 共享实例：上下文构建器（模块级复用）
_context_builder = ChatContextBuilder()


async def run_chat(
    *,
    run_id: str,
    user_id: int,
    username: str,
    session_id: str,
    user_message_id: int,
    user_input: str,
    attachments: list[str] | None = None,
    diagram_mode: DiagramMode = "auto",
    video_mode: bool = False,
) -> None:
    """构建上下文并驱动一次 harness 运行。"""
    from app.chat.harness import ChatRun

    uc = get_chat_usecases()
    memory_svc = get_chat_memory_service()
    current_message = (user_input or "").strip() or "请分析我上传的附件，并解答其中的问题。"
    merged_attachments = list(dict.fromkeys(attachments or []))

    # 首条消息异步生成会话标题
    if await memory_svc.count_messages(user_id=user_id, session_id=session_id) <= 1:
        uc._spawn_background(
            memory_svc.generate_session_title(
                user_id=user_id,
                session_id=session_id,
                first_message=current_message,
            ),
            label="generate_title",
        )

    history, session_summary = await asyncio.gather(
        _context_builder.build_history(
            user_id, session_id, exclude_message_id=user_message_id,
        ),
        memory_svc.get_session_summary_context(
            user_id=user_id,
            session_id=session_id,
        ),
    )

    run = ChatRun.build(
        run_id=run_id,
        user_id=user_id,
        username=username,
        session_id=session_id,
        user_message_id=user_message_id,
        question=current_message,
        attachments=merged_attachments,
        diagram_mode=diagram_mode,
        video_mode=video_mode,
        session_summary=session_summary,
        history=history,
    )
    await run.run()


# ChatUseCases：聊天服务核心类（附件上传、文件解析、对话流编排、后台任务）
class ChatUseCases:
    """聊天服务核心类 — 负责附件上传、文件解析和对话流编排。

    职责：
    1. 附件上传、存储和分析
    2. 流式对话（SSE 事件流）
    3. 安全过滤（敏感词检测）
    4. 消息持久化（通过 memory_service）
    5. 后台任务（记忆管线、画像更新）

    会话 CRUD 等简单操作直接通过 get_chat_memory_service() 调用，
    不需要再经过此层转发。
    """

    # 初始化文件存储、后台任务集合与记忆服务
    def __init__(self) -> None:
        # 本地文件存储：用户上传文件的磁盘读写
        self.file_store: LocalFileStore = LocalFileStore()
        # 后台任务集合：防止未等待的协程被 GC 回收
        self._background_tasks: set[asyncio.Task] = set()
        self._memory_service = get_chat_memory_service()

    # 生成与 PostgreSQL UUID 列一致的新会话 ID
    def default_session_id(self, user_id: int) -> str:
        """生成与 PostgreSQL UUID 列一致的新会话 ID。"""
        return str(uuid4())

    # 将文字与原始附件快照写入 UserMessage（带 URL 校验与文件类型识别）
    async def create_user_message(
        self,
        *,
        user_id: int,
        username: str,
        session_id: str,
        text: str,
        attachments: list[dict[str, Any]],
    ) -> Any:
        """把文字和原始附件快照直接写入 UserMessage。"""
        # 校验并归一化每个附件（URL 前缀 + 去重）
        normalized_attachments: list[dict[str, Any]] = []
        prefix = f"/static/{username}/chat/{session_id}/uploads/"
        seen_urls: set[str] = set()
        for attachment in attachments:
            url = str(attachment.get("url") or "").strip()
            if not url.startswith(prefix) or url in seen_urls:
                raise ValueError("附件地址无效或不属于当前会话")
            filename = url.removeprefix(prefix)
            path = self.file_store.resolve_user_file(
                current_username=username,
                owner_username=username,
                session_id=session_id,
                filename=filename,
            )
            suffix = path.suffix.lower()
            file_type = "image" if suffix in self.file_store.allowed_image_ext else "document"
            normalized_attachments.append({
                "url": url,
                "file_type": file_type,
                "original_name": str(attachment.get("original_name") or filename),
                "mime_type": str(attachment.get("mime_type") or "") or None,
                "size_bytes": path.stat().st_size,
            })
            seen_urls.add(url)
        # 持久化最终归一化的用户消息
        return await self._memory_service.save_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=build_user_content(text, normalized_attachments),
        )

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        """获取会话历史，按 run 快照组装为 ChatMessageItem 列表。"""
        memory_svc = get_chat_memory_service()
        if not session_id:
            sessions = await memory_svc.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        raw_messages = await memory_svc.list_messages(
            user_id=user_id, session_id=session_id, limit=limit,
        )
        analyses = await memory_svc.list_attachment_analyses(
            user_id=user_id, session_id=session_id,
        )
        runs = {}
        for run in await memory_svc.list_runs(user_id=user_id, session_id=session_id):
            state = await load_run_state(run.id)
            if state is None:
                continue
            snapshot = state.model_dump()
            snapshot["user_message_id"] = run.user_message_id
            snapshot["created_at"] = run.created_at.isoformat() if run.created_at else None
            runs[run.id] = snapshot

        # 附件分析按 run_id 归组
        analyses_by_run: dict[str, list[dict[str, Any]]] = {}
        for analysis in analyses:
            analyses_by_run.setdefault(analysis.run_id, []).append({
                "id": str(analysis.id),
                "analysis_type": analysis.analysis_type,
                "status": analysis.status,
                "content": analysis.content,
                "error": analysis.error_message,
            })

        # 只有最终回答（无 tool_calls 的 assistant 消息）才携带 run 快照
        final_runs = {
            message.run_id
            for message in raw_messages
            if message.role == "assistant" and not message.tool_calls and message.run_id
        }

        result: list[ChatMessageItem] = []
        for message in raw_messages:
            content = (
                list(message.content)
                if isinstance(message.content, list)
                else [{"type": "text", "text": str(message.content)}]
            )
            show_run = message.run_id in final_runs
            result.append(
                ChatMessageItem(
                    id=message.id or 0,
                    role=message.role,
                    content=content,
                    run_id=message.run_id,
                    run=runs.get(message.run_id) if show_run else None,
                    tool_calls=message.tool_calls if isinstance(message.tool_calls, list) else None,
                    tool_call_id=message.tool_call_id,
                    attachment_analyses=analyses_by_run.get(message.run_id, []) if show_run else [],
                    created_at=message.created_at,
                )
            )

        # 只产生活动、没有最终回答的运行补一条空回答项，避免前端丢进度
        answered = {message.run_id for message in raw_messages if message.run_id in final_runs}
        for run_id, snapshot in runs.items():
            if run_id in answered:
                continue
            result.append(
                ChatMessageItem(
                    id=-int(snapshot.get("user_message_id") or 0),
                    role="assistant",
                    content=[],
                    run_id=run_id,
                    run=snapshot,
                    attachment_analyses=analyses_by_run.get(run_id, []),
                    created_at=snapshot.get("created_at"),
                )
            )

        result.sort(key=lambda item: (str(item.created_at or ""), item.id))
        return result

    # 保存用户上传文件：校验后写入磁盘并返回附件快照
    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        username: str,
        session_id: str,
    ) -> dict[str, Any]:
        """保存用户上传的文件。

        流程：
        1. 校验文件名非空
        2. 检查单次上传文件数是否超限
        3. 调用 LocalFileStore 写入磁盘
        4. 返回附件快照，随 UserMessage 一起提交
        """
        # 校验文件名非空
        if not filename:
            raise ValueError("文件名不能为空")
        # 检查文件数上限
        existing = self.file_store.list_files(username=username, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
        # 写入磁盘并返回快照
        payload = await self.file_store.save_upload(
            filename=filename,
            content=content,
            username=username,
            session_id=session_id,
        )
        return payload

    # 安全地启动后台协程任务，避免被 GC 回收并记录异常
    def _spawn_background(self, coro, *, label: str = "") -> None:
        """安全地启动后台协程任务。

        关键设计：
        1. 任务加入 _background_tasks 集合，防止被 GC 回收
        2. 完成回调自动从集合移除，避免内存泄漏
        3. 异常被 catch 并记录日志，不会影响主流程
        4. 若当前不在事件循环中（极端情况），记录警告而非崩溃
        """
        # 包装协程，捕获并记录异常
        async def _run() -> None:
            try:
                await coro
            except Exception as exc:
                logger.error("[ChatUseCases] 后台任务失败 label=%s err=%s", label, exc)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # 确保任务被引用，不会被垃圾回收
            task = asyncio.ensure_future(_run())
            self._background_tasks.add(task)
            # 完成后自动从集合移除
            task.add_done_callback(self._background_tasks.discard)
        else:
            logger.warning("[ChatUseCases] 无法在非事件循环中启动后台任务 label=%s", label)


# ── 单例管理 ──
_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    """获取 ChatUseCases 单例。"""
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases
