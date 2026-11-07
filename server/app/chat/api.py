"""Chat HTTP 与 SSE 路由端点 —— 统一挂载在 /api/v1/ai/chat/ 下。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.schemas import UserClaims
from app.auth.security import get_current_user
from app.chat.agent import (
    TERMINAL_STATUSES,
    get_active_stream,
    has_active_run,
    request_cancel_run,
    reserve_run,
    row_to_run_state,
)
from app.chat.schemas import DiagramMode, RunEvent, encode_chat_sse
from app.chat.service import (
    archive_session,
    create_session,
    create_user_message,
    default_session_id,
    get_history,
    get_or_create_session,
    list_sessions,
    save_upload,
    start_chat_run,
    update_session_title,
)
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import ChatRun as ChatRunRow
from app.response import HttpResponse

logger = get_logger(__name__)

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/chat/messages")
async def create_mentor_chat_message(
    background_tasks: BackgroundTasks,
    user_input: str = Form(default=""),
    session_id: str | None = Form(default=None),
    attachments: str | None = Form(default=None),
    diagram_mode: DiagramMode = Form(default="auto"),
    video_mode: bool = Form(default=False),
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """接收用户提问与附件，登记运行记录并异步启动 Tutor Agent 循环。"""
    try:
        parsed_attachments = json.loads(attachments) if attachments else []
    except json.JSONDecodeError:
        return HttpResponse.error(code=400, message="附件参数格式错误")
    if not isinstance(parsed_attachments, list) or not all(
        isinstance(item, dict) for item in parsed_attachments
    ):
        return HttpResponse.error(code=400, message="附件参数格式错误")

    effective_session = session_id or default_session_id()
    effective_message = (user_input or "").strip()

    if not effective_message and not parsed_attachments:
        return HttpResponse.error(code=400, message="请输入问题或上传附件")
    if not effective_message and parsed_attachments:
        effective_message = "请分析我上传的附件，并解答其中的问题。"

    if await has_active_run(current_user.id, effective_session):
        return HttpResponse.error(code=409, message="当前回答尚未完成，请稍候")

    try:
        await get_or_create_session(user_id=current_user.id, session_id=effective_session)
    except PermissionError as exc:
        return HttpResponse.error(code=403, message=str(exc))

    try:
        user_message = await create_user_message(
            user_id=current_user.id,
            username=current_user.username,
            session_id=effective_session,
            text=effective_message,
            attachments=parsed_attachments,
        )
    except (ValueError, FileNotFoundError) as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except Exception as exc:
        logger.exception("[ChatAPI] 保存用户消息失败")
        return HttpResponse.error(code=500, message=f"保存用户消息失败: {exc}")

    if user_message.id is None:
        return HttpResponse.error(code=500, message="保存用户消息失败")

    run_id = str(uuid4())
    await reserve_run(
        run_id=run_id,
        user_id=current_user.id,
        session_id=effective_session,
        user_message_id=user_message.id,
    )
    background_tasks.add_task(
        start_chat_run,
        run_id=run_id,
        user_id=current_user.id,
        username=current_user.username,
        session_id=effective_session,
        user_message_id=user_message.id,
        user_input=effective_message,
        attachments=[str(item.get("url") or "") for item in parsed_attachments],
        diagram_mode=diagram_mode,
        video_mode=video_mode,
    )
    return HttpResponse.success(
        data={
            "run_id": run_id,
            "message_id": user_message.id,
            "session_id": effective_session,
        },
        status_code=202,
    )


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """上传聊天附件（图片或文档），返回静态访问 URL 与文件元数据。"""
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    content = await file.read()
    try:
        saved = await save_upload(
            filename=file.filename,
            content=content,
            username=current_user.username,
            session_id=session_id,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=saved)


@router.get("/chat/runs/{run_id}")
async def get_chat_run(
    run_id: str,
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """读取指定运行的完整状态快照（支持页面刷新恢复）。"""
    run = (
        await session.exec(
            select(ChatRunRow).where(
                ChatRunRow.id == run_id,
                ChatRunRow.user_id == current_user.id,
            )
        )
    ).first()
    if run is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    state = row_to_run_state(run)
    return HttpResponse.success(data=state.model_dump())


@router.get("/chat/runs/{run_id}/events")
async def stream_chat_run_events(
    run_id: str,
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """订阅运行的实时 SSE 事件流：首帧推送 run.snapshot 完整快照，后续推送增量阶段与步骤更新。"""
    run = (
        await session.exec(
            select(ChatRunRow).where(
                ChatRunRow.id == run_id,
                ChatRunRow.user_id == current_user.id,
            )
        )
    ).first()
    if run is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")

    active_stream = get_active_stream(run_id)
    if active_stream is None:
        state = row_to_run_state(run)

        async def _completed_stream() -> AsyncGenerator[str, None]:
            """对已结束运行直接推送快照与终态帧后关闭流。"""
            snap = RunEvent(
                run_id=run_id,
                sequence=state.sequence,
                event="run.snapshot",
                data=state.model_dump(),
            )
            yield encode_chat_sse(snap)
            done = RunEvent(
                run_id=run_id,
                sequence=state.sequence + 1,
                event="run.finished",
                data=state.model_dump(),
            )
            yield encode_chat_sse(done)

        return StreamingResponse(
            _completed_stream(),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    queue, snapshot = await active_stream.subscribe()

    async def _live_stream() -> AsyncGenerator[str, None]:
        """先发送首帧快照，再实时推送后续队列事件直至终态。"""
        try:
            yield encode_chat_sse(snapshot)
            if str(snapshot.data.get("status") or "") in TERMINAL_STATUSES:
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield encode_chat_sse(event)
                if event.event == "run.finished":
                    return
        finally:
            await active_stream.unsubscribe(queue)

    return StreamingResponse(
        _live_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/chat/runs/{run_id}/cancel")
async def cancel_chat_run(
    run_id: str,
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """请求停止指定运行，使 Agent 循环在下一个检查点优雅退出。"""
    run = (
        await session.exec(
            select(ChatRunRow).where(
                ChatRunRow.id == run_id,
                ChatRunRow.user_id == current_user.id,
            )
        )
    ).first()
    if run is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    if run.status not in {"queued", "running"}:
        return HttpResponse.success(data={"run_id": run_id, "status": run.status})
    if request_cancel_run(run_id):
        return HttpResponse.success(data={"run_id": run_id, "status": "cancelling"})

    run.status = "cancelled"
    run.phase = "cancelled"
    run.phase_label = "已停止生成"
    run.error = "用户停止生成"
    session.add(run)
    await session.commit()
    return HttpResponse.success(data={"run_id": run_id, "status": "cancelled"})


@router.get("/chat/sessions")
async def get_sessions_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """获取当前用户的活跃会话列表。"""
    sessions = await list_sessions(user_id=current_user.id, limit=limit)
    return HttpResponse.success(
        data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]
    )


@router.post("/chat/sessions")
async def create_session_endpoint(
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """创建一条新的辅导会话。"""
    chat_session = await create_session(user_id=current_user.id)
    return HttpResponse.success(
        data={"id": chat_session.id, "title": chat_session.title},
        status_code=201,
    )


@router.delete("/chat/sessions/{session_id}")
async def delete_session_endpoint(
    session_id: str,
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """归档（删除）指定会话。"""
    ok = await archive_session(user_id=current_user.id, session_id=session_id)
    if not ok:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.patch("/chat/sessions/{session_id}")
async def update_session_endpoint(
    session_id: str,
    payload: dict[str, Any],
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """修改指定会话的标题。"""
    title = str(payload.get("title") or "").strip()
    if not title:
        return HttpResponse.error(code=400, message="标题不能为空")
    ok = await update_session_title(
        user_id=current_user.id,
        session_id=session_id,
        title=title,
    )
    if not ok:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="标题已更新")


@router.get("/chat/history")
async def chat_history_endpoint(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: UserClaims = Depends(get_current_user),
) -> JSONResponse:
    """获取会话历史消息（附带每次运行的完整步骤快照）。"""
    items = await get_history(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
    )
    return HttpResponse.success(data=[item.model_dump() for item in items])
