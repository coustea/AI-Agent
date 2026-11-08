"""聊天业务编排 —— 负责接收 AgentInput、构建上下文、调度 Agent 循环、单事务落库结果与管理会话历史。"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from uuid import uuid4

from sqlmodel import func, select

from app.chat.agent import run_tutor_agent
from app.chat.context import build_turn_messages, build_user_content
from app.chat.files import ALLOWED_IMAGE_EXT, resolve_user_file
from app.chat.hooks import RunHooks
from app.chat.memory import (
    estimate_token_count,
    extract_content_text,
    now_utc,
    compress_session,
    update_long_term_memory,
)
from app.chat.schemas import AgentInput, AttachmentInput, ChatMessageItem, RunState, TerminalStatus
from app.chat.tools import build_tutor_tools
from app.evaluation.event_types import CHAT_DIALOGUE, MODULE_CHAT
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.config import MAX_UPLOAD_FILES_PER_REQUEST
from app.infra.database import session_scope
from app.infra.llm import LLM, Message, HumanMessage, SystemMessage
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatRun as ChatRunRow, ChatSession, ChatSessionSummaryBlock
from app.shared.tools import ToolRegistry

logger = get_logger(__name__)

DEFAULT_SESSION_TITLE = "新对话"
TITLE_MAX_LENGTH = 100


class RunAlreadyActive(ValueError):
    """当前会话已有尚未结束的运行。"""


_active_runs: dict[str, RunHooks] = {}


def _validate_attachments(inp: AgentInput) -> list[AttachmentInput]:
    """校验本轮上传附件归属与本地文件存在性，并补齐真实文件类型与字节大小。"""
    if len(inp.attachments) > MAX_UPLOAD_FILES_PER_REQUEST:
        raise ValueError(f"每次最多添加 {MAX_UPLOAD_FILES_PER_REQUEST} 个附件")
    prefix = f"/static/{inp.username}/chat/{inp.session_id}/uploads/"
    seen_urls: set[str] = set()
    validated: list[AttachmentInput] = []

    for item in inp.attachments:
        url = item.url.strip()
        if not url.startswith(prefix) or url in seen_urls:
            raise ValueError("附件地址无效或不属于当前会话")
        filename = url.removeprefix(prefix)
        path = resolve_user_file(
            username=inp.username,
            session_id=inp.session_id,
            filename=filename,
        )
        file_type = "image" if path.suffix.lower() in ALLOWED_IMAGE_EXT else "document"
        validated.append(
            AttachmentInput(
                url=url,
                file_type=file_type,
                original_name=item.original_name or filename,
                mime_type=item.mime_type or None,
                size_bytes=path.stat().st_size,
            )
        )
        seen_urls.add(url)
    return validated


async def prepare_chat_run(inp: AgentInput) -> RunHooks:
    """校验 AgentInput，在同一事务中落库用户消息与运行记录，并注册内存流对象。"""
    inp.attachments = _validate_attachments(inp)
    content_blocks = build_user_content(inp.effective_question, inp.attachments)

    async with session_scope() as db:
        db_session = (
            await db.exec(
                select(ChatSession).where(ChatSession.id == inp.session_id).with_for_update()
            )
        ).first()
        if db_session is None:
            db_session = ChatSession(
                id=inp.session_id,
                user_id=inp.user_id,
                title=DEFAULT_SESSION_TITLE,
            )
            db.add(db_session)
            await db.flush()
        elif db_session.user_id != inp.user_id or db_session.is_archived:
            raise PermissionError("无权访问该会话")

        unfinished = (await db.exec(select(ChatRunRow).where(
            ChatRunRow.session_id == inp.session_id,
            ChatRunRow.status.in_(["queued", "running"]),
        ))).all()
        recovered: list[str] = []
        for row in unfinished:
            hooks = _active_runs.get(row.id)
            if hooks is None or hooks.state.status in {"queued", "running"}:
                raise RunAlreadyActive("当前回答尚未完成，请稍候")
            # 上次写库失败但进程已结束：数据库恢复后先补写失败终态。
            row.sqlmodel_update(hooks.state.model_dump(exclude={"run_id"}))
            row.finished_at = now_utc()
            db.add(row)
            recovered.append(row.id)

        prior_count = int(
            (
                await db.exec(
                    select(func.count())
                    .select_from(ChatMessage)
                    .where(
                        ChatMessage.session_id == inp.session_id,
                        ChatMessage.role == "user",
                    )
                )
            ).one()
            or 0
        )
        inp.is_first_turn = prior_count == 0

        msg = ChatMessage(
            session_id=inp.session_id,
            role="user",
            content=content_blocks,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        inp.user_message_id = int(msg.id or 0)

        tokens = estimate_token_count(extract_content_text(content_blocks))
        db_session.summary_token_count += tokens
        db_session.ltm_token_count += tokens
        db_session.ltm_message_count += 1
        db_session.updated_at = now_utc()
        db.add(db_session)

        db.add(
            ChatRunRow(
                id=inp.run_id,
                session_id=inp.session_id,
                user_id=inp.user_id,
                user_message_id=inp.user_message_id,
                status="queued",
                phase="queued",
                phase_label="等待处理",
            )
        )

    for run_id in recovered:
        _active_runs.pop(run_id, None)
    hooks = RunHooks(inp.run_id)
    _active_runs[inp.run_id] = hooks
    return hooks


async def save_run_result(
    inp: AgentInput,
    state: RunState,
    new_messages: Sequence[Message] = (),
) -> None:
    """在单个数据库事务中一次性写入本轮新增消息链、会话记忆水位与运行终态快照。"""
    async with session_scope() as db:
        session = await db.get(ChatSession, inp.session_id)
        if session is not None and session.user_id == inp.user_id and new_messages:
            added_tokens = 0
            for m in new_messages:
                text = (m.content or "").strip()
                content = [{"type": "text", "text": text}] if text else []
                db.add(ChatMessage(
                    session_id=inp.session_id,
                    run_id=inp.run_id,
                    role=m.role,
                    content=content,
                    tool_calls=[
                        {"id": call.id, "name": call.name, "args": dict(call.args)}
                        for call in m.tool_calls
                    ] or None,
                    tool_call_id=m.tool_call_id,
                ))
                added_tokens += estimate_token_count(text)

            session.summary_token_count += added_tokens
            session.ltm_token_count += added_tokens
            session.ltm_message_count += len(new_messages)
            session.updated_at = now_utc()
            db.add(session)

        row = await db.get(ChatRunRow, inp.run_id)
        if row is not None:
            row.sqlmodel_update(state.model_dump(exclude={"run_id"}))
            row.finished_at = now_utc()
            db.add(row)


async def execute_chat_run(inp: AgentInput) -> None:
    """准备依赖、执行循环、保存结果，最后发布终态并更新会话记忆。"""
    hooks = _active_runs[inp.run_id]
    hooks.task = asyncio.current_task()
    new_messages: list[Message] = []
    answer = ""
    status: TerminalStatus = "completed"
    error = ""
    try:
        if hooks.cancel_requested:
            raise asyncio.CancelledError
        async with asyncio.timeout(1800):
            hooks.set_phase("preparing", "正在准备上下文")
            messages = await build_turn_messages(inp)
            tools = ToolRegistry(tools=build_tutor_tools(
                user_id=inp.user_id,
                username=inp.username,
                session_id=inp.session_id,
                on_subagent_progress=hooks.on_subagent_progress,
            ))
            result = await run_tutor_agent(
                messages=messages,
                llm=LLM(provider="text", temperature=0.7, max_tokens=8192),
                registry=tools,
                hooks=hooks,
            )
            answer = result.answer
            new_messages = result.new_messages
    except asyncio.CancelledError:
        status, error = "cancelled", "用户停止生成"
    except TimeoutError:
        status, error = "failed", "运行超过 1800 秒"
    except Exception as exc:
        logger.exception("[ChatService] 运行失败 run_id=%s", inp.run_id)
        status, error = "failed", str(exc)

    # 保存期间继续显示运行状态，提交完成后才能宣布结束。
    final_state = hooks.result_state(status, error)
    hooks.state.steps = final_state.steps
    hooks.set_phase("saving", "正在保存回答")
    saved = False
    try:
        await save_run_result(inp, final_state, new_messages)
        saved = True
    except Exception as exc:
        logger.exception("[ChatService] 保存终态失败 run_id=%s", inp.run_id)
        final_state = hooks.result_state("failed", f"保存回答失败：{exc}")
    finally:
        hooks.state = final_state
        hooks.publish()
        hooks.task = None
        # 保存失败时保留内存终态，避免重连后又看到数据库中的 queued。
        if saved:
            _active_runs.pop(inp.run_id, None)

    if hooks.state.status == "completed":
        post_jobs = [
            compress_session(inp.user_id, inp.session_id),
            update_long_term_memory(inp.user_id, inp.session_id, inp.effective_question, answer),
            record_dialogue_event(inp.user_id, inp.session_id),
        ]
        if inp.is_first_turn:
            post_jobs.append(generate_session_title(
                user_id=inp.user_id,
                session_id=inp.session_id,
                first_message=inp.effective_question,
            ))
        for result in await asyncio.gather(*post_jobs, return_exceptions=True):
            if isinstance(result, BaseException):
                logger.warning("[ChatService] 回答后任务失败: %s", result)


def get_active_run(run_id: str) -> RunHooks | None:
    """获取当前进程内正在活跃执行的 RunHooks。"""
    return _active_runs.get(run_id)


def run_state(row: ChatRunRow) -> RunState:
    """将数据库 ChatRun 行（或活跃内存流）转换为前端所需的 RunState 快照。"""
    active = _active_runs.get(row.id)
    if active is not None:
        return active.snapshot()

    return RunState(
        run_id=row.id,
        status=row.status,
        phase=row.phase,
        phase_label=row.phase_label,
        content=row.content,
        error=row.error,
        total_elapsed_ms=row.total_elapsed_ms,
        steps=row.steps,
        artifacts=row.artifacts,
        sources=row.sources,
    )


async def get_run_state(user_id: int, run_id: str) -> RunState | None:
    """按用户权限读取指定运行的完整状态快照。"""
    async with session_scope() as db:
        row = (
            await db.exec(
                select(ChatRunRow).where(
                    ChatRunRow.id == run_id,
                    ChatRunRow.user_id == user_id,
                )
            )
        ).first()
    if row is None:
        return None
    return run_state(row)


async def cancel_run(user_id: int, run_id: str) -> str | None:
    """校验归属后请求取消；保存结果期间不再打断任务。"""
    state = await get_run_state(user_id, run_id)
    if state is None:
        return None
    hooks = _active_runs.get(run_id)
    if hooks is None or state.status not in {"queued", "running"}:
        return state.status
    if state.phase == "saving":
        return "saving"
    if not hooks.cancel_requested:
        hooks.cancel_requested = True
        hooks.set_phase("cancelling", "正在停止")
        if hooks.task is not None:
            hooks.task.cancel()
    return "cancelling"


async def mark_interrupted_runs() -> int:
    """服务启动时将上次进程遗留的 queued/running 运行标记为 interrupted。"""
    async with session_scope() as db:
        result = await db.execute(
            select(ChatRunRow).where(ChatRunRow.status.in_(["queued", "running"]))
        )
        runs = list(result.scalars().all())
        for run in runs:
            run.status = "interrupted"
            run.phase = "interrupted"
            run.phase_label = "服务重启，运行已中断"
            run.error = "服务重启，运行已中断"
            db.add(run)
        return len(runs)


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
            id=str(uuid4()),
            user_id=user_id,
            title=(title or DEFAULT_SESSION_TITLE)[:TITLE_MAX_LENGTH],
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


async def get_history(
    *,
    user_id: int,
    session_id: str | None = None,
    limit: int = 50,
) -> list[ChatMessageItem]:
    """查询会话历史并附带对应的 Agent 运行快照，仅返回 user 与最终 assistant 消息。"""
    target_session_id = session_id
    if not target_session_id:
        recent = await list_sessions(user_id=user_id, limit=1)
        if not recent:
            return []
        target_session_id = recent[0].id

    async with session_scope() as db:
        messages = list(
            reversed(
                (
                    await db.exec(
                        select(ChatMessage)
                        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                        .where(
                            ChatSession.user_id == user_id,
                            ChatSession.is_archived == False,  # noqa: E712
                            ChatMessage.session_id == target_session_id,
                            ChatMessage.role == "user",
                        )
                        .order_by(ChatMessage.id.desc())
                        .limit((limit + 1) // 2)
                    )
                ).all()
            )
        )
        if not messages:
            return []
        runs = (
            await db.exec(
                select(ChatRunRow).where(
                    ChatRunRow.user_id == user_id,
                    ChatRunRow.user_message_id.in_([message.id for message in messages]),
                )
            )
        ).all()

    runs_by_message = {run.user_message_id: run for run in runs}
    result: list[ChatMessageItem] = []
    for message in messages:
        result.append(
            ChatMessageItem(
                id=message.id,
                role="user",
                content=message.content,
                created_at=message.created_at,
            )
        )
        run = runs_by_message.get(message.id)
        if run is not None:
            state = run_state(run)
            result.append(
                ChatMessageItem(
                    id=-message.id,
                    role="assistant",
                    content=[{"type": "text", "text": state.content}] if state.content else [],
                    run=state.model_dump(),
                    created_at=run.created_at,
                )
            )
    return result[-limit:]


def clean_session_title(value: str) -> str:
    """清理会话标题中的换行、引号与首尾标点并截断长度。"""
    title = re.sub(r"[\r\n\t]+", " ", value or "").strip()
    title = title.strip("`'\"“”‘’《》[]（）()，。！？!?：:；;、 ")
    title = re.sub(r"\s+", " ", title)
    return title[:TITLE_MAX_LENGTH]


async def generate_session_title(user_id: int, session_id: str, first_message: str) -> bool:
    """根据首条用户消息调用 LLM 生成简短中文会话标题。"""
    fallback = clean_session_title(first_message) or DEFAULT_SESSION_TITLE
    title = fallback
    try:
        llm = LLM(temperature=0.7, max_tokens=32)
        resp = await llm.text(
            [
                SystemMessage(content="你是会话标题生成器。只输出一个简短中文标题，不要标点、引号或解释。"),
                HumanMessage(content=f"为这段学习辅导对话生成标题，最多12个中文字符：\n{first_message}"),
            ],
            max_tokens=32,
        )
        title = clean_session_title(resp) or fallback
    except Exception as exc:
        logger.warning("[ChatService] 生成标题失败: user_id=%s session_id=%s err=%s", user_id, session_id, exc)

    async with session_scope() as db:
        chat_session = (
            await db.exec(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
        ).first()
        if not chat_session:
            return False
        chat_session.title = title[:TITLE_MAX_LENGTH]
        chat_session.updated_at = now_utc()
        db.add(chat_session)
    return True


async def record_dialogue_event(user_id: int, session_id: str) -> None:
    """记录本轮辅导学习事件，供画像与评估更新使用。"""
    async with session_scope() as db:
        summary = (await db.exec(select(ChatSessionSummaryBlock.summary_markdown).where(
            ChatSessionSummaryBlock.session_id == session_id,
        ).order_by(ChatSessionSummaryBlock.block_index.desc()).limit(1))).first()
        await EvaluationService().record_event(db, user_id=user_id, payload=LearningEventCreate(
            module=MODULE_CHAT, entity_id=session_id, event_type=CHAT_DIALOGUE,
            event_metadata={"summary_length": len(summary or ""), "turn_count": 1},
        ))
