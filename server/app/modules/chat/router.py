"""Chat 路由：辅导对话 + 会话管理 + 聊天历史 + 文件上传。

- /chat/stream: TutorAgent 前台辅导答疑，后台异步触发画像构建
- /chat/upload: 文件上传（图片/文档）
- /chat/sessions, /chat/history: 会话与历史查询
"""

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.models.user import User
from app.services.memory import memory_service
from app.modules.chat.agent import tutor_agent
from app.modules.chat.schemas import MentorChatRequest, ChatMessageItem, UploadResponse, AttachmentInfo, ToolCallRecord
from app.modules.profile.profile_agent import profile_agent
from app.modules.profile.fact_agent import fact_agent

logger = get_logger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("workplace/chat-uploads")
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_DOC_EXT = {".pdf", ".doc", ".docx", ".txt"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5MB
MAX_DOC_SIZE = 10 * 1024 * 1024     # 10MB

# 画像更新触发阈值
PROFILE_THRESHOLD = 2
EARLY_TRIGGER = 2


@router.post("/chat/stream")
async def mentor_chat_stream(
    req: MentorChatRequest,
    current_user: User = Depends(get_current_user),
):
    """TutorAgent 辅导答疑（主功能），后台异步触发画像构建。"""
    effective_session = req.session_id or tutor_agent.global_session_id

    generator = tutor_agent.chat_stream(
        user_id=current_user.id,
        user_message=req.message,
        session_id=effective_session,
        image_url=req.image_url,
        file_urls=req.file_urls,
    )

    # 判断是否触发后台画像更新
    msg_count = await memory_service.get_message_count(
        user_id=current_user.id,
        session_id=effective_session,
        module=tutor_agent.module_name,
    )

    should_trigger = (
        msg_count == EARLY_TRIGGER
        or (msg_count > 0 and msg_count % PROFILE_THRESHOLD == 0)
    )
    if should_trigger:
        asyncio.create_task(profile_agent.build_profile(user_id=current_user.id, session_id=effective_session))

    # 每次对话都尝试提炼事实偏好（因为只看最近2条）
    asyncio.create_task(fact_agent.extract_and_save_fact(user_id=current_user.id, session_id=effective_session))

    # 短期→长期记忆压缩（消息过多时触发）
    asyncio.create_task(memory_service.summarize_and_compress(
        user_id=current_user.id,
        session_id=effective_session,
        module=tutor_agent.module_name,
    ))

    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传图片或文档，返回可访问的 URL。"""
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix in ALLOWED_IMAGE_EXT:
        file_type = "image"
        max_size = MAX_IMAGE_SIZE
    elif suffix in ALLOWED_DOC_EXT:
        file_type = "document"
        max_size = MAX_DOC_SIZE
    else:
        return HttpResponse.error(
            code=400,
            message=f"不支持的文件类型: {suffix}，支持: {', '.join(ALLOWED_IMAGE_EXT | ALLOWED_DOC_EXT)}",
        )

    content = await file.read()
    if len(content) > max_size:
        max_mb = max_size // (1024 * 1024)
        return HttpResponse.error(code=400, message=f"文件大小超过限制（{max_mb}MB）")

    user_dir = UPLOAD_DIR / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}{suffix}"
    file_path = user_dir / safe_name

    file_path.write_bytes(content)
    url = f"/uploads/{current_user.id}/{safe_name}"

    logger.info(f"[Upload] User {current_user.id} uploaded {file.filename} -> {url}")
    return HttpResponse.success(data=UploadResponse(
        url=url,
        file_type=file_type,
        original_name=file.filename,
        size_bytes=len(content),
    ).model_dump())


@router.get("/chat/sessions")
async def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取会话列表（不含已归档）"""
    sessions = await memory_service.get_user_chat_sessions(current_user.id, module=tutor_agent.module_name, limit=limit)
    return HttpResponse.success(data=[{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions])


@router.post("/chat/sessions")
async def create_session(
    current_user: User = Depends(get_current_user),
):
    """创建新会话，返回会话 ID"""
    session = await memory_service.create_chat_session(
        user_id=current_user.id,
        module=tutor_agent.module_name,
        title="新对话",
    )
    return HttpResponse.success(data={"id": session.id, "title": session.title})


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """归档（软删除）一个会话"""
    success = await memory_service.archive_chat_session(session_id, current_user.id)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.get("/chat/history")
async def get_chat_history(
    session_id: str = Query(default=tutor_agent.global_session_id, description="指定会话ID"),
    limit: int = Query(default=50, ge=1, le=200, description="返回的消息条数"),
    current_user: User = Depends(get_current_user),
):
    """获取聊天历史。"""
    messages = await memory_service.get_recent_messages(
        user_id=current_user.id,
        session_id=session_id,
        module=tutor_agent.module_name,
        limit=limit,
    )

    items = []
    for msg in messages:
        # 解析 attachments JSON
        attachments = None
        if msg.attachments:
            try:
                raw = json.loads(msg.attachments)
                attachments = [AttachmentInfo(**a) for a in raw]
            except (json.JSONDecodeError, TypeError):
                attachments = None

        # 解析 tool_calls JSON
        tool_calls = None
        if msg.tool_calls:
            try:
                raw_tc = json.loads(msg.tool_calls)
                tool_calls = [ToolCallRecord(**tc) for tc in raw_tc]
            except (json.JSONDecodeError, TypeError):
                tool_calls = None

        items.append(ChatMessageItem(
            role=msg.role,
            content=msg.content,
            attachments=attachments,
            tool_calls=tool_calls,
            created_at=msg.created_at,
        ))
    return HttpResponse.success(data=items)
