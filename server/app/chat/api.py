"""Chat HTTP 与 SSE 路由端点 —— 统一挂载在 /api/v1/ai/chat/ 下。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth.security import get_current_user
from app.chat.files import save_upload
from app.chat.schemas import (
    TERMINAL_STATUSES,
    AgentInput,
    ChatRequest,
    encode_chat_sse,
)
from app.chat.service import (
    RunAlreadyActive,
    archive_session,
    cancel_run,
    create_session,
    execute_chat_run,
    get_active_run,
    get_history,
    get_run_state,
    list_sessions,
    prepare_chat_run,
)
from app.infra.logging import get_logger
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
    payload: ChatRequest,
) -> JSONResponse:
    """接收前端提交的 AgentInput，落库运行记录并异步启动 Agent 循环。"""
    try:
        if not payload.question.strip() and not payload.attachments:
            raise ValueError("请输入问题或上传附件")
        agent_input = AgentInput(**payload.model_dump(), user=get_current_user())
        await prepare_chat_run(agent_input)
    except RunAlreadyActive as exc:
        return HttpResponse.error(code=409, message=str(exc))
    except PermissionError as exc:
        return HttpResponse.error(code=403, message=str(exc))
    except (ValueError, FileNotFoundError) as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except Exception as exc:
        logger.exception("[ChatAPI] 保存用户消息失败")
        return HttpResponse.error(code=500, message=f"保存用户消息失败: {exc}")

    background_tasks.add_task(execute_chat_run, agent_input)
    logger.info(
        "[ChatAPI] 收到消息并调度运行: user={} session={} run_id={} 附件={}",
        agent_input.username, agent_input.session_id, agent_input.run_id, len(payload.attachments),
    )
    return HttpResponse.success(
        data={
            "run_id": agent_input.run_id,
            "message_id": agent_input.user_message_id,
            "session_id": agent_input.session_id,
        },
        status_code=202,
    )


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
) -> JSONResponse:
    """上传聊天附件（图片或文档），返回静态访问 URL 与文件元数据。"""
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    content = await file.read()
    try:
        user = get_current_user()
        saved = await asyncio.to_thread(
            save_upload,
            filename=file.filename,
            content=content,
            username=user.username,
            session_id=session_id,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=saved)


@router.get("/chat/runs/{run_id}/events", response_model=None)
async def stream_chat_run_events(run_id: str) -> JSONResponse | StreamingResponse:
    """发送最新运行快照，合并高频更新，并在终态或断开时释放订阅。"""
    user = get_current_user()
    state = await get_run_state(user.id, run_id)
    if state is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    hooks = get_active_run(run_id)
    logger.info(
        "[ChatAPI] SSE 订阅: user={} run_id={} status={} 活跃={}",
        user.username, run_id, state.status, hooks is not None,
    )

    async def events() -> AsyncGenerator[str, None]:
        """订阅后先读取快照，再按通知推送；重连无需回放旧事件。"""
        queue = hooks.subscribe() if hooks is not None else None
        try:
            current = hooks.snapshot() if hooks is not None else state
            while True:
                yield encode_chat_sse(current)
                if current.status in TERMINAL_STATUSES or queue is None:
                    return
                try:
                    await asyncio.wait_for(queue.get(), timeout=25)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                else:
                    # 每秒最多约 10 次快照；队列只保存一个更新通知。
                    await asyncio.sleep(0.1)
                    if not queue.empty():
                        queue.get_nowait()
                current = hooks.snapshot()
        finally:
            if hooks is not None and queue is not None:
                hooks.unsubscribe(queue)

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat/runs/{run_id}/cancel")
async def cancel_chat_run(run_id: str) -> JSONResponse:
    """请求取消指定运行及其正在执行的模型或工具任务。"""
    user = get_current_user()
    status = await cancel_run(user.id, run_id)
    if status is None:
        return HttpResponse.error(code=404, message="运行不存在或无权限")
    logger.info("[ChatAPI] 请求取消运行: user={} run_id={} phase={}", user.username, run_id, status)
    return HttpResponse.success(data={"run_id": run_id, "status": status})


@router.get("/chat/sessions")
async def get_sessions_endpoint(limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
    """获取当前用户的活跃会话列表。"""
    user = get_current_user()
    sessions = await list_sessions(user_id=user.id, limit=limit)
    return HttpResponse.success(
        data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]
    )


@router.post("/chat/sessions")
async def create_session_endpoint() -> JSONResponse:
    """创建一条新的辅导会话。"""
    user = get_current_user()
    chat_session = await create_session(user_id=user.id)
    return HttpResponse.success(
        data={"id": chat_session.id, "title": chat_session.title},
        status_code=201,
    )


@router.delete("/chat/sessions/{session_id}")
async def delete_session_endpoint(session_id: str) -> JSONResponse:
    """归档（删除）指定会话。"""
    user = get_current_user()
    ok = await archive_session(user_id=user.id, session_id=session_id)
    if not ok:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.get("/chat/history")
async def chat_history_endpoint(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    """获取会话历史消息（附带每次运行的完整步骤快照）。"""
    user = get_current_user()
    items = await get_history(
        user_id=user.id,
        session_id=session_id,
        limit=limit,
    )
    return HttpResponse.success(data=[item.model_dump() for item in items])
