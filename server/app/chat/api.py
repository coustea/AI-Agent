"""聊天 HTTP 路由 — 所有端点集中在一个文件。

所有端点挂载在 /api/v1/ai/chat/ 下，由 routes.py 统一注册到 FastAPI。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.security import get_current_user_flexible
from app.chat.emitter import ChatEvents, encode_chat_sse, get_chat_channel
from app.chat.memory.service import get_chat_memory_service
from app.chat.service import get_chat_usecases, run_chat_agent
from app.config import CHAT_DIR
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import ChatSession, School, User
from app.infra.response import HttpResponse

if TYPE_CHECKING:
    from app.chat.memory.service import ChatMemoryService

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Chat routes
# ---------------------------------------------------------------------------

def _get_chat_memory_service() -> "ChatMemoryService":
    return get_chat_usecases()._memory_service


@router.post("/chat/runs")
async def create_mentor_chat_run(
    background_tasks: BackgroundTasks,
    user_input: str = Form(default=""),
    session_id: str | None = Form(default=None),
    attachments: str | None = Form(default=None),
    need_teaching_diagram: bool = Form(default=False),
    enable_web_search: bool = Form(default=False),
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    parsed_attachments = [u.strip() for u in attachments.split(",") if u.strip()] if attachments else []
    effective_session = session_id or uc.default_session_id(current_user.id)
    effective_message = (user_input or "").strip()

    # 支持纯附件上传（无文字输入）
    if not effective_message and not parsed_attachments:
        return HttpResponse.error(code=400, message="请输入问题或上传附件")

    if not effective_message and parsed_attachments:
        effective_message = "请分析我上传的附件，并解答其中的问题。"

    # 确保会话已存在，避免 SSE 订阅 404
    memory_svc = get_chat_memory_service()
    try:
        await memory_svc.get_or_create_session(
            user_id=current_user.id,
            session_id=effective_session,
        )
    except Exception as exc:
        logger.warning("[ChatAPI] 确保会话存在失败: %s", exc)

    run_id = str(uuid4())
    events = ChatEvents(user_id=current_user.id, session_id=effective_session, run_id=run_id)
    await events.open()

    background_tasks.add_task(
        run_chat_agent,
        run_id=run_id,
        user_id=current_user.id,
        session_id=effective_session,
        user_input=effective_message,
        attachments=parsed_attachments,
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )

    logger.info(
        "[ChatAPI] 创建辅导运行: run_id=%s user_id=%s session_id=%s msg_len=%d attachments=%d",
        run_id,
        current_user.id, effective_session, len(effective_message), len(parsed_attachments),
    )
    return HttpResponse.success(
        data={"run_id": run_id, "session_id": effective_session, "status": "pending"},
        status_code=202,
    )


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user_flexible),
):
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    uc = get_chat_usecases()
    content = await file.read()
    logger.info("[ChatAPI] 文件上传: user_id=%s session_id=%s filename=%s size=%d", current_user.id, session_id, file.filename, len(content))
    try:
        saved = await uc.save_upload(
            filename=file.filename,
            content=content,
            user_id=current_user.id,
            session_id=session_id,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=saved)


@router.get("/chat/uploads/{owner_id}/{session_id}/{filename}")
async def get_uploaded_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_user_id=current_user.id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )
    except PermissionError as exc:
        return HttpResponse.error(code=403, message=str(exc))
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except FileNotFoundError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/uploads/{owner_id}/{session_id}/diagrams/{filename}")
async def get_diagram_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_user_id=current_user.id,
            owner_id=owner_id,
            session_id=session_id,
            filename=f"diagrams/{filename}",
        )
    except PermissionError as exc:
        return HttpResponse.error(code=403, message=str(exc))
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except FileNotFoundError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/files/{owner_id}/{session_id}/{filename}")
async def get_chat_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_flexible),
):
    if current_user.id != owner_id:
        return HttpResponse.error(code=403, message="无权访问此文件")
    file_path = (CHAT_DIR / str(owner_id) / str(session_id) / filename).resolve()
    base_dir = (CHAT_DIR / str(owner_id) / str(session_id)).resolve()
    if not str(file_path).startswith(str(base_dir)):
        return HttpResponse.error(code=400, message="非法文件路径")
    if not file_path.exists():
        return HttpResponse.error(code=404, message="文件不存在")
    return FileResponse(path=str(file_path), filename=filename)


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/chat/sessions/{session_id}/runs/{run_id}/events")
async def stream_chat_run_events(
    session_id: str,
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """订阅 Chat run 的实时事件流。"""
    result = await session.exec(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    chat_session = result.first()
    if chat_session is None:
        return HttpResponse.error(code=404, message="会话不存在或无权限")

    events = await get_chat_channel(current_user.id, session_id, run_id)
    if events is None:
        return HttpResponse.error(code=410, message="事件流已过期或不存在")

    async def event_stream():
        queue, replay = await events.subscribe(after_sequence)
        try:
            for event in replay:
                yield encode_chat_sse(event)
            if replay and replay[-1].event in {"run.completed", "run.failed"}:
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield encode_chat_sse(event)
                if event.event in {"run.completed", "run.failed"}:
                    return
        finally:
            await events.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# ---------------------------------------------------------------------------
# Session routes
# ---------------------------------------------------------------------------

@router.get("/chat/sessions")
async def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user_flexible),
):
    svc = get_chat_memory_service()
    sessions = await svc.list_sessions(user_id=current_user.id, limit=limit)
    return HttpResponse.success(data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions])


@router.post("/chat/sessions")
async def create_session(
    current_user: User = Depends(get_current_user_flexible),
):
    svc = get_chat_memory_service()
    session = await svc.create_session(user_id=current_user.id)
    return HttpResponse.success(data={"id": session.id, "title": session.title}, status_code=201)


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user_flexible),
):
    svc = get_chat_memory_service()
    success = await svc.archive_session(user_id=current_user.id, session_id=session_id)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.patch("/chat/sessions/{session_id}")
async def update_session(
    session_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user_flexible),
):
    title = (payload.get("title") or "").strip()
    if not title:
        return HttpResponse.error(code=400, message="标题不能为空")
    svc = get_chat_memory_service()
    success = await svc.update_session_title(user_id=current_user.id, session_id=session_id, title=title)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="标题已更新")


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


# ---------------------------------------------------------------------------
# School routes
# ---------------------------------------------------------------------------

@router.get("/schools/search")
async def search_schools(
    keyword: str = Query(default="", min_length=0, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    if keyword:
        stmt = (
            select(School)
            .where(School.name.contains(keyword))
            .order_by(School.name)
            .limit(limit)
        )
    else:
        stmt = select(School).order_by(School.id.desc()).limit(limit)

    schools = (await db.exec(stmt)).scalars().all()

    return HttpResponse.success(data=[
        {
            "id": school.id,
            "name": school.name,
            "level": school.tier or school.level,
            "tier": school.tier,
        }
        for school in schools
    ])
