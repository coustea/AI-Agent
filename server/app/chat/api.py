"""聊天 HTTP 路由 — 所有端点集中在一个文件。

所有端点挂载在 /api/v1/ai/chat/ 下，由 routes.py 统一注册到 FastAPI。
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.security import get_current_user_flexible
from app.chat.emitter import (
    ChatEvents,
    encode_chat_sse,
    get_chat_channel,
    has_active_chat_channel,
)
from app.chat.memory.service import get_chat_memory_service
from app.chat.video import get_chat_video_service
from app.chat.diagram_image_renderer import render_teaching_diagram_png
from app.chat.service import get_chat_usecases, run_chat_agent
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, School, User
from app.infra.response import HttpResponse

logger = get_logger(__name__)

# 聊天路由集合，统一挂载在 /api/v1/ai/chat/ 下
router = APIRouter()


@router.post("/chat/videos")
async def create_chat_video(
    background_tasks: BackgroundTasks,
    topic: str = Form(...),
    session_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user_flexible),
):
    """Create a cartoon task only after an explicit user action in chat."""
    normalized_topic = topic.strip()
    if not normalized_topic:
        return HttpResponse.error(code=400, message="请输入视频主题")

    effective_session = session_id or get_chat_usecases().default_session_id(current_user.id)
    service = get_chat_video_service()
    try:
        task = await service.create_task(
            user_id=current_user.id,
            session_id=effective_session,
            topic=normalized_topic,
        )
    except (ValueError, PermissionError) as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except Exception:
        logger.exception("[ChatAPI] 创建视频任务失败")
        return HttpResponse.error(code=500, message="视频任务创建失败，请稍后重试")

    background_tasks.add_task(
        service.run_task,
        user_id=current_user.id,
        username=current_user.username,
        session_id=effective_session,
        user_message_id=task["user_message_id"],
        topic=normalized_topic,
    )
    return HttpResponse.success(data=task, status_code=202)


@router.get("/chat/sessions/{session_id}/videos/{user_message_id}")
async def get_chat_video(
    session_id: str,
    user_message_id: int,
    current_user: User = Depends(get_current_user_flexible),
):
    """Poll a persisted explicit video task; this is independent of chat SSE."""
    video = await get_chat_video_service().get_task(
        user_id=current_user.id,
        session_id=session_id,
        user_message_id=user_message_id,
    )
    if video is None:
        return HttpResponse.error(code=404, message="视频任务不存在或无权限")
    return HttpResponse.success(data={"user_message_id": user_message_id, "video": video})


async def _get_owned_assistant_message(
    session: AsyncSession,
    user_id: int,
    message_id: int,
) -> ChatMessage | None:
    """Return an assistant message only when its session belongs to the caller."""
    result = await session.exec(
        select(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(
            ChatMessage.id == message_id,
            ChatMessage.role == "assistant",
            ChatSession.user_id == user_id,
        )
    )
    return result.first()


@router.post("/chat/messages/{message_id}/diagram-image/retry")
async def retry_diagram_image(
    message_id: int,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """Retry PNG rendering for the caller's persisted fallback diagram."""
    message = await _get_owned_assistant_message(session, current_user.id, message_id)
    if message is None:
        return HttpResponse.error(code=404, message="找不到图解消息")

    fallback = (message.usage_metadata or {}).get("diagram")
    if not isinstance(fallback, dict) or fallback.get("kind") != "fallback":
        return HttpResponse.error(code=409, message="当前图解无需重新生成")

    diagram = fallback.get("diagram")
    if not isinstance(diagram, dict):
        return HttpResponse.error(code=404, message="找不到可重试的图解")

    try:
        image = await render_teaching_diagram_png(
            diagram,
            username=current_user.username,
            session_id=message.session_id,
        )
    except Exception:
        logger.exception("[ChatAPI] 图解图片重试渲染失败: message_id=%s", message_id)
        return HttpResponse.error(code=503, message="图片生成暂时失败，请稍后重试")

    message.usage_metadata = {**(message.usage_metadata or {}), "diagram": image}
    session.add(message)
    await session.commit()
    return HttpResponse.success(data={"diagram": image})


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
    need_teaching_diagram: bool = Form(default=False),
    enable_web_search: bool = Form(default=False),
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
        return HttpResponse.error(code=400, message="请输入问题或上传附件")

    # 纯附件场景：填充默认引导语
    if not effective_message and parsed_attachments:
        effective_message = "请分析我上传的附件，并解答其中的问题。"

    # 同一会话若已有进行中的回答则拒绝并发请求
    if await has_active_chat_channel(current_user.id, effective_session):
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
        return HttpResponse.error(code=400, message=str(exc))
    except Exception as exc:
        logger.exception("[ChatAPI] 保存用户消息失败")
        return HttpResponse.error(code=500, message=f"保存用户消息失败: {exc}")
    user_message_id = user_message.id
    if user_message_id is None:
        return HttpResponse.error(code=500, message="保存用户消息失败")

    # 为该条用户消息创建事件频道供前端 SSE 订阅
    events = ChatEvents(
        user_id=current_user.id,
        session_id=effective_session,
        user_message_id=user_message_id,
    )
    await events.open()

    # 将对话 Agent 处理作为后台任务调度
    background_tasks.add_task(
        run_chat_agent,
        user_message_id=user_message_id,
        user_id=current_user.id,
        username=current_user.username,
        session_id=effective_session,
        user_input=effective_message,
        attachments=[str(item.get("url") or "") for item in parsed_attachments],
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )

    logger.info(
        "[ChatAPI] 开始处理用户消息: user_message_id=%s user_id=%s session_id=%s msg_len=%d attachments=%d",
        user_message_id,
        current_user.id, effective_session, len(effective_message), len(parsed_attachments),
    )
    # 立即返回 202，表示已受理由后台任务异步处理
    return HttpResponse.success(
        data={"message_id": user_message_id, "session_id": effective_session},
        status_code=202,
    )


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


# 按归属用户/会话/文件名解析并返回已上传的附件文件
@router.get("/chat/uploads/{owner_username}/{session_id}/{filename}")
async def get_uploaded_file(
    owner_username: str,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_username=current_user.username,
            owner_username=owner_username,
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


# 返回已生成的图解图片文件
@router.get("/chat/uploads/{owner_username}/{session_id}/diagrams/{filename}")
async def get_diagram_file(
    owner_username: str,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_username=current_user.username,
            owner_username=owner_username,
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


# 返回会话内的任意聊天文件（与上传文件共用解析逻辑）
@router.get("/chat/files/{owner_username}/{session_id}/{filename}")
async def get_chat_file(
    owner_username: str,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_flexible),
):
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_username=current_user.username,
            owner_username=owner_username,
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


# SSE 响应头：禁用缓存与代理缓冲，保证实时推送
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# 订阅某条用户消息的实时处理事件，以 SSE 长连接推送
@router.get("/chat/sessions/{session_id}/messages/{user_message_id}/events")
async def stream_chat_message_events(
    session_id: str,
    user_message_id: int,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """订阅某条 UserMessage 的实时处理事件。"""
    # 校验会话归属
    result = await session.exec(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    chat_session = result.first()
    if chat_session is None:
        return HttpResponse.error(code=404, message="会话不存在或无权限")

    # 获取事件频道，不存在则返回 410
    events = await get_chat_channel(current_user.id, session_id, user_message_id)
    if events is None:
        return HttpResponse.error(code=410, message="事件流已过期或不存在")

    # SSE 生成器：先回放历史事件，再实时推送队列事件，终态后关闭
    async def event_stream():
        queue, replay = await events.subscribe(after_sequence)
        try:
            # 先回放错过的事件
            for event in replay:
                yield encode_chat_sse(event)
            # 若回放已包含终态事件，直接结束
            if replay and replay[-1].event in {"message.completed", "message.failed"}:
                return

            # 持续监听队列，30s 超时发送心跳保活
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield encode_chat_sse(event)
                # 遇到终态事件即结束流
                if event.event in {"message.completed", "message.failed"}:
                    return
        finally:
            await events.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


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
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
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


# ---------------------------------------------------------------------------
# 学校路由
# ---------------------------------------------------------------------------

# 按关键词搜索学校（无关键词则返回最近学校）
@router.get("/schools/search")
async def search_schools(
    keyword: str = Query(default="", min_length=0, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    # 有关键词则模糊匹配学校名称，否则按 ID 倒序取最近
    if keyword:
        stmt = (
            select(School)
            .where(School.name.contains(keyword))
            .order_by(School.name)
            .limit(limit)
        )
    else:
        stmt = select(School).order_by(School.id.desc()).limit(limit)

    # 执行查询并序列化结果
    schools = list((await db.exec(stmt)).all())

    return HttpResponse.success(data=[
        {
            "id": school.id,
            "name": school.name,
            "level": school.tier or school.level,
            "tier": school.tier,
        }
        for school in schools
    ])
