"""聊天 HTTP 路由 — 所有端点集中在一个文件。

所有端点挂载在 /api/v1/ai/chat/ 下，由 routes.py 统一注册到 FastAPI。
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.security import get_current_user_flexible
from app.chat.harness import (
    ChatRunEvents,
    encode_chat_sse,
    has_active_run,
    load_run_state,
)
from app.chat.harness.events import TERMINAL_EVENTS
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import DiagramMode
from app.chat.service import get_chat_usecases, run_chat
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import ChatRun, User
from app.response import HttpResponse

logger = get_logger(__name__)

# 聊天路由集合，统一挂载在 /api/v1/ai/chat/ 下
router = APIRouter()


# ---------------------------------------------------------------------------
# 聊天路由
# ---------------------------------------------------------------------------


# 创建一条辅导对话消息：解析附件、确保会话、保存用户消息并调度后台 Agent 任务
@router.post("/chat/messages")
async def create_mentor_chat_message(
    background_tasks: BackgroundTasks,
    user_input: str = Form(default=""),
    session_id: str | None = Form(default=None),
    attachments: str | None = Form(default=None),
    diagram_mode: DiagramMode = Form(default="auto"),
    video_mode: bool = Form(default=False),
    current_user: User = Depends(get_current_user_flexible),
):
    # 获取用例层并解析附件 JSON 参数
    uc = get_chat_usecases()
    try:
        parsed_attachments = json.loads(attachments) if attachments else []
    except json.JSONDecodeError:
        return HttpResponse.error(code=400, message="附件参数格式错误")
    if not isinstance(parsed_attachments, list) or not all(
        isinstance(item, dict) for item in parsed_attachments
    ):
        return HttpResponse.error(code=400, message="附件参数格式错误")
    # 确定会话 ID（未提供则使用默认会话）与有效消息文本
    effective_session = session_id or uc.default_session_id(current_user.id)
    effective_message = (user_input or "").strip()

    # 支持纯附件上传（无文字输入）
    if not effective_message and not parsed_attachments:
        logger.debug("[ChatAPI] 空消息请求: user_id=%s", current_user.id)
        return HttpResponse.error(code=400, message="请输入问题或上传附件")

    # 纯附件场景：填充默认引导语
    if not effective_message and parsed_attachments:
        effective_message = "请分析我上传的附件，并解答其中的问题。"

    # 同一会话若已有进行中的回答则拒绝并发请求
    if await has_active_run(current_user.id, effective_session):
        logger.info("[ChatAPI] 并发请求被拒绝: user_id=%s session_id=%s", current_user.id, effective_session)
        return HttpResponse.error(code=409, message="当前回答尚未完成，请稍候")

    # 确保会话已存在，避免 SSE 订阅 404
    memory_svc = get_chat_memory_service()
    try:
        await memory_svc.get_or_create_session(
            user_id=current_user.id,
            session_id=effective_session,
        )
    except Exception as exc:
        logger.warning("[ChatAPI] 确保会话存在失败: %s", exc)

    # 持久化用户消息（含附件），失败返回错误
    try:
        user_message = await uc.create_user_message(
            user_id=current_user.id,
            username=current_user.username,
            session_id=effective_session,
            text=effective_message,
            attachments=parsed_attachments,
        )
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("[ChatAPI] 保存用户消息失败(参数错误): user_id=%s err=%s", current_user.id, exc)
        return HttpResponse.error(code=400, message=str(exc))
    except Exception as exc:
        logger.exception("[ChatAPI] 保存用户消息失败")
        return HttpResponse.error(code=500, message=f"保存用户消息失败: {exc}")
    user_message_id = user_message.id
    if user_message_id is None:
        return HttpResponse.error(code=500, message="保存用户消息失败")

    # 创建运行记录并交给后台任务驱动 harness
    run_id = await _create_run(
        user_id=current_user.id,
        session_id=effective_session,
        user_message_id=user_message_id,
    )
    background_tasks.add_task(
        run_chat,
        run_id=run_id,
        user_message_id=user_message_id,
        user_id=current_user.id,
        username=current_user.username,
        session_id=effective_session,
        user_input=effective_message,
        attachments=[str(item.get("url") or "") for item in parsed_attachments],
        diagram_mode=diagram_mode,
        video_mode=video_mode,
    )

    logger.info(
        "[ChatAPI] 开始处理用户消息: run_id=%s user_id=%s session_id=%s msg_len=%d attachments=%d",
        run_id,
        current_user.id, effective_session, len(effective_message), len(parsed_attachments),
    )
    # 立即返回 202，运行事件通过 /chat/runs/{run_id}/events 订阅
    return HttpResponse.success(
        data={
            "run_id": run_id,
            "message_id": user_message_id,
            "session_id": effective_session,
        },
        status_code=202,
    )


# 登记运行行，保证前端拿到 run_id 后能立即订阅事件
async def _create_run(
    *,
    user_id: int,
    session_id: str,
    user_message_id: int,
) -> str:
    """生成并登记 run_id，返回给前端用于订阅事件流。"""
    from uuid import uuid4

    from app.chat.harness import ChatRun

    run_id = str(uuid4())
    await ChatRun.reserve(
        run_id=run_id,
        user_id=user_id,
        session_id=session_id,
        user_message_id=user_message_id,
    )
    return run_id


# 上传附件文件，返回可访问的文件元信息
@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user_flexible),
):
    # 校验文件名并读取文件内容
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    uc = get_chat_usecases()
    content = await file.read()
    logger.info("[ChatAPI] 文件上传: username=%s session_id=%s filename=%s size=%d", current_user.username, session_id, file.filename, len(content))
    try:
        saved = await uc.save_upload(
            filename=file.filename,
            content=content,
            username=current_user.username,
            session_id=session_id,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=saved)


# SSE 响应头：禁用缓存与代理缓冲，保证实时推送
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# 读取一次运行的当前快照（刷新页面后恢复渲染）
@router.get("/chat/runs/{run_id}")
async def get_chat_run(
    run_id: str,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """返回指定运行的完整快照。"""
    run = (
        await session.exec(
            select(ChatRun).where(
                ChatRun.id == run_id,
                ChatRun.user_id == current_user.id,
            )
        )
    ).first()
    if run is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    state = await load_run_state(run_id)
    if state is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    return HttpResponse.success(data=state.model_dump())


# 订阅一次运行的实时事件流（支持 after_sequence 断点续传）
@router.get("/chat/runs/{run_id}/events")
async def stream_chat_run_events(
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """以 SSE 推送运行事件，先回放再实时转发。"""
    run = (
        await session.exec(
            select(ChatRun).where(
                ChatRun.id == run_id,
                ChatRun.user_id == current_user.id,
            )
        )
    ).first()
    if run is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")

    events = ChatRunEvents(run_id)
    queue, replay = await events.subscribe(after_sequence)

    async def event_stream():
        try:
            for event in replay:
                yield encode_chat_sse(event)
            if replay and replay[-1].event in TERMINAL_EVENTS:
                return
            if run.status not in {"queued", "running"}:
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield encode_chat_sse(event)
                if event.event in TERMINAL_EVENTS:
                    return
        finally:
            await events.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# 请求取消一次运行
@router.post("/chat/runs/{run_id}/cancel")
async def cancel_chat_run(
    run_id: str,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """把运行标记为取消，循环在下一个检查点退出。"""
    run = (
        await session.exec(
            select(ChatRun).where(
                ChatRun.id == run_id,
                ChatRun.user_id == current_user.id,
            )
        )
    ).first()
    if run is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    if run.status not in {"queued", "running"}:
        return HttpResponse.success(data={"run_id": run_id, "status": run.status})
    # 优先打断进程内的活跃运行，循环会在下一个检查点退出
    from app.chat.harness import ChatRun

    if ChatRun.request_cancel(run_id):
        return HttpResponse.success(data={"run_id": run_id, "status": "cancelling"})
    run.status = "cancelled"
    run.error = "用户取消运行"
    session.add(run)
    await session.commit()
    return HttpResponse.success(data={"run_id": run_id, "status": "cancelled"})




# ---------------------------------------------------------------------------
# 会话路由
# ---------------------------------------------------------------------------

# 获取当前用户的会话列表（含摘要信息）
@router.get("/chat/sessions")
async def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user_flexible),
):
    svc = get_chat_memory_service()
    sessions = await svc.list_sessions(user_id=current_user.id, limit=limit)
    return HttpResponse.success(data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions])


# 创建新会话
@router.post("/chat/sessions")
async def create_session(
    current_user: User = Depends(get_current_user_flexible),
):
    svc = get_chat_memory_service()
    session = await svc.create_session(user_id=current_user.id)
    return HttpResponse.success(data={"id": session.id, "title": session.title}, status_code=201)


# 归档（删除）指定会话
@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user_flexible),
):
    svc = get_chat_memory_service()
    success = await svc.archive_session(user_id=current_user.id, session_id=session_id)
    if not success:
        logger.warning("[ChatAPI] 归档会话失败(不存在或无权限): user_id=%s session_id=%s", current_user.id, session_id)
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    logger.info("[ChatAPI] 会话已归档: user_id=%s session_id=%s", current_user.id, session_id)
    return HttpResponse.success(message="会话已归档")


# 更新会话标题
@router.patch("/chat/sessions/{session_id}")
async def update_session(
    session_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user_flexible),
):
    # 校验标题非空后更新会话标题
    title = (payload.get("title") or "").strip()
    if not title:
        return HttpResponse.error(code=400, message="标题不能为空")
    svc = get_chat_memory_service()
    success = await svc.update_session_title(user_id=current_user.id, session_id=session_id, title=title)
    if not success:
        logger.warning("[ChatAPI] 更新会话标题失败: user_id=%s session_id=%s", current_user.id, session_id)
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="标题已更新")


# 获取会话历史消息
@router.get("/chat/history")
async def chat_history(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    items = await uc.get_history(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
    )
    return HttpResponse.success(data=[item.model_dump() for item in items])

