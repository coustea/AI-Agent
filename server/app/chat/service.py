"""Chat 业务服务层 —— 会话管理、文件上传、消息落盘、无 N+1 历史组装与 Agent 启动编排。"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from sqlmodel import func, select

from app.chat.agent import row_to_run_state, run_tutor_agent
from app.chat.context import LocalFileStore, build_user_content
from app.chat.memory import (
    DEFAULT_SESSION_TITLE,
    TITLE_MAX_LENGTH,
    estimate_token_count,
    extract_content_text,
    generate_session_title,
    now_utc,
)
from app.chat.schemas import ChatMessageItem, DiagramMode
from app.config import MAX_UPLOAD_FILES_PER_REQUEST
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatRun as ChatRunRow, ChatSession

logger = get_logger(__name__)

_file_store = LocalFileStore()
_background_tasks: set[asyncio.Task[Any]] = set()


def _spawn_background(coro: Any, *, label: str = "") -> None:
    """安全启动后台协程任务并持有强引用，防止被 GC 回收。"""

    async def _runner() -> None:
        """包装执行后台协程并捕获记录异常。"""
        try:
            await coro
        except Exception as exc:
            logger.warning("[ChatService] 后台任务异常 label=%s err=%s", label, exc)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(_runner())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# ===========================================================================
# 1. 会话 CRUD
# ===========================================================================


def default_session_id() -> str:
    """生成标准 UUID 格式的新会话 ID。"""
    return str(uuid4())


async def list_sessions(user_id: int, limit: int = 20) -> list[ChatSession]:
    """按最后更新时间倒序查询用户的活跃会话列表。"""
    async with session_scope() as db:
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.is_archived == False,  # noqa: E712
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        return list((await db.exec(stmt)).all())


async def create_session(user_id: int, title: str = DEFAULT_SESSION_TITLE) -> ChatSession:
    """为用户创建一条新会话并立即持久化。"""
    async with session_scope() as db:
        chat_session = ChatSession(
            id=default_session_id(),
            user_id=user_id,
            title=(title or DEFAULT_SESSION_TITLE)[:TITLE_MAX_LENGTH],
        )
        db.add(chat_session)
        await db.flush()
        await db.refresh(chat_session)
        return chat_session


async def get_or_create_session(user_id: int, session_id: str) -> ChatSession:
    """查询指定会话，若不存在则自动创建（校验归属权防止越权）。"""
    async with session_scope() as db:
        existing = (
            await db.exec(select(ChatSession).where(ChatSession.id == session_id))
        ).first()
        if existing is not None:
            if existing.user_id != user_id:
                raise PermissionError("无权访问该会话")
            return existing
        chat_session = ChatSession(
            id=session_id,
            user_id=user_id,
            title=DEFAULT_SESSION_TITLE,
        )
        db.add(chat_session)
        await db.flush()
        await db.refresh(chat_session)
        return chat_session


async def archive_session(user_id: int, session_id: str) -> bool:
    """将指定会话标记为已归档。"""
    async with session_scope() as db:
        chat_session = (
            await db.exec(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
        ).first()
        if chat_session is None:
            return False
        chat_session.is_archived = True
        chat_session.updated_at = now_utc()
        db.add(chat_session)
        return True


async def update_session_title(user_id: int, session_id: str, title: str) -> bool:
    """更新指定会话的标题。"""
    cleaned = (title or "").strip()[:TITLE_MAX_LENGTH]
    if not cleaned:
        return False
    async with session_scope() as db:
        chat_session = (
            await db.exec(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
        ).first()
        if chat_session is None:
            return False
        chat_session.title = cleaned
        chat_session.updated_at = now_utc()
        db.add(chat_session)
        return True


async def count_user_messages(user_id: int, session_id: str) -> int:
    """统计指定会话中用户消息条数，用于判断是否为首轮对话。"""
    async with session_scope() as db:
        stmt = (
            select(func.count())
            .select_from(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
            )
        )
        return int((await db.exec(stmt)).one() or 0)


# ===========================================================================
# 2. 文件上传与用户消息创建
# ===========================================================================


async def save_upload(
    *,
    filename: str,
    content: bytes,
    username: str,
    session_id: str,
) -> dict[str, Any]:
    """校验上传文件数量与合法性后写入会话目录，返回附件元数据字典。"""
    if not filename:
        raise ValueError("文件名不能为空")
    existing = _file_store.list_files(username=username, session_id=session_id)
    if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
        raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
    return await _file_store.save_upload(
        filename=filename,
        content=content,
        username=username,
        session_id=session_id,
    )


async def create_user_message(
    *,
    user_id: int,
    username: str,
    session_id: str,
    text: str,
    attachments: list[dict[str, Any]],
) -> ChatMessage:
    """校验附件归属与物理文件后，将用户文本与附件快照写入 chat_messages 表。"""
    normalized_attachments: list[dict[str, Any]] = []
    prefix = f"/static/{username}/chat/{session_id}/uploads/"
    seen_urls: set[str] = set()

    for attachment in attachments:
        url = str(attachment.get("url") or "").strip()
        if not url.startswith(prefix) or url in seen_urls:
            raise ValueError("附件地址无效或不属于当前会话")
        filename = url.removeprefix(prefix)
        path = _file_store.resolve_user_file(
            current_username=username,
            owner_username=username,
            session_id=session_id,
            filename=filename,
        )
        suffix = path.suffix.lower()
        file_type = "image" if suffix in _file_store.allowed_image_ext else "document"
        normalized_attachments.append(
            {
                "url": url,
                "file_type": file_type,
                "original_name": str(attachment.get("original_name") or filename),
                "mime_type": str(attachment.get("mime_type") or "") or None,
                "size_bytes": path.stat().st_size,
            }
        )
        seen_urls.add(url)

    content_blocks = build_user_content(text, normalized_attachments)
    async with session_scope() as db:
        chat_session = await get_or_create_session(user_id=user_id, session_id=session_id)
        db_session = await db.get(ChatSession, chat_session.id)
        msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=content_blocks,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)

        if db_session is not None:
            tokens = estimate_token_count(extract_content_text(content_blocks))
            db_session.summary_token_count = int(db_session.summary_token_count or 0) + tokens
            db_session.ltm_token_count = int(db_session.ltm_token_count or 0) + tokens
            db_session.ltm_message_count = int(db_session.ltm_message_count or 0) + 1
            db_session.updated_at = now_utc()
            db.add(db_session)
        return msg


# ===========================================================================
# 3. 历史消息组装（消除 N+1 查询，过滤中间 tool / tool_calls 消息）
# ===========================================================================


async def get_history(
    *,
    user_id: int,
    session_id: str | None = None,
    limit: int = 50,
) -> list[ChatMessageItem]:
    """查询会话历史并附带对应的 Agent 运行快照，仅返回面向用户展示的 user 与最终 assistant 消息。"""
    target_session_id = session_id
    if not target_session_id:
        recent = await list_sessions(user_id=user_id, limit=1)
        if not recent:
            return []
        target_session_id = recent[0].id

    async with session_scope() as db:
        msg_stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.is_archived == False,  # noqa: E712
                ChatMessage.session_id == target_session_id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(limit * 3)
        )
        raw_messages = list(reversed((await db.exec(msg_stmt)).all()))

        run_stmt = (
            select(ChatRunRow)
            .where(
                ChatRunRow.user_id == user_id,
                ChatRunRow.session_id == target_session_id,
            )
            .order_by(ChatRunRow.created_at.asc())
        )
        raw_runs = list((await db.exec(run_stmt)).all())

    runs_by_id: dict[str, dict[str, Any]] = {}
    for run_row in raw_runs:
        state = row_to_run_state(run_row)
        snapshot = state.model_dump()
        snapshot["user_message_id"] = run_row.user_message_id
        snapshot["created_at"] = run_row.created_at.isoformat() if run_row.created_at else None
        runs_by_id[run_row.id] = snapshot

    # 仅保留 user 消息与不带 tool_calls 的最终 assistant 回答
    visible_messages = [
        m
        for m in raw_messages
        if m.role == "user" or (m.role == "assistant" and not m.tool_calls)
    ]
    if len(visible_messages) > limit:
        visible_messages = visible_messages[-limit:]

    answered_run_ids: set[str] = set()
    result: list[ChatMessageItem] = []

    for message in visible_messages:
        content = (
            list(message.content)
            if isinstance(message.content, list)
            else [{"type": "text", "text": str(message.content or "")}]
        )
        run_snapshot = None
        if message.role == "assistant" and message.run_id:
            run_snapshot = runs_by_id.get(message.run_id)
            answered_run_ids.add(message.run_id)

        result.append(
            ChatMessageItem(
                id=message.id or 0,
                role="user" if message.role == "user" else "assistant",
                content=content,
                run_id=message.run_id,
                run=run_snapshot,
                created_at=message.created_at,
            )
        )

    # 对于正在运行或未产生最终文本回答的运行，补一条占位 assistant 消息以展示实时/中断步骤面板
    for run_id, snapshot in runs_by_id.items():
        if run_id in answered_run_ids:
            continue
        result.append(
            ChatMessageItem(
                id=-int(snapshot.get("user_message_id") or 0),
                role="assistant",
                content=[],
                run_id=run_id,
                run=snapshot,
                created_at=snapshot.get("created_at"),
            )
        )

    result.sort(key=lambda item: (str(item.created_at or ""), item.id))
    return result


# ===========================================================================
# 4. 启动对话运行
# ===========================================================================


async def start_chat_run(
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
    """触发首轮会话标题生成并调用 run_tutor_agent 执行本轮辅导对话。"""
    question = (user_input or "").strip() or "请分析我上传的附件，并解答其中的问题。"
    dedup_attachments = list(dict.fromkeys(a for a in (attachments or []) if a))

    if await count_user_messages(user_id=user_id, session_id=session_id) <= 1:
        _spawn_background(
            generate_session_title(
                user_id=user_id,
                session_id=session_id,
                first_message=question,
            ),
            label="generate_title",
        )

    await run_tutor_agent(
        run_id=run_id,
        user_id=user_id,
        username=username,
        session_id=session_id,
        user_message_id=user_message_id,
        question=question,
        attachments=dedup_attachments,
        diagram_mode=diagram_mode,
        video_mode=video_mode,
    )


__all__ = [
    "archive_session",
    "count_user_messages",
    "create_session",
    "create_user_message",
    "default_session_id",
    "get_history",
    "get_or_create_session",
    "list_sessions",
    "save_upload",
    "start_chat_run",
    "update_session_title",
]
