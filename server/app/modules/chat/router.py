"""Chat 路由：辅导对话 + 会话管理 + 聊天历史 + 文件上传。

- /chat/stream: TutorAgent 前台辅导答疑（后处理链路由 TutorAgent 内部触发）
- /chat/upload: 文件上传（图片/文档）
- /chat/sessions, /chat/history: 会话与历史查询
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from app.core.logging import get_logger
from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.models.user import User
from app.services.memory import memory_service
from app.modules.chat.agent import tutor_agent
from app.modules.chat.schemas import MentorChatRequest, ChatMessageItem, UploadResponse, AttachmentInfo, ToolCallRecord
from app.utils.paths import WORKPLACE_DIR

logger = get_logger(__name__)
router = APIRouter()

UPLOAD_DIR = WORKPLACE_DIR / "chat-uploads"
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_DOC_EXT = {".pdf", ".docx", ".txt", ".md", ".log"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5MB
MAX_DOC_SIZE = 10 * 1024 * 1024     # 10MB

def _default_session_id(user_id: int) -> str:
    """按用户隔离默认会话，避免共享固定全局会话。"""
    return f"user-{user_id}-default-mentor"


@router.post("/chat/stream")
async def mentor_chat_stream(
    req: MentorChatRequest,
    current_user: User = Depends(get_current_user),
):
    """TutorAgent 辅导答疑（主功能）。"""
    effective_session = req.session_id or _default_session_id(current_user.id)

    generator = tutor_agent.chat_stream(
        user_id=current_user.id,
        user_message=req.message,
        session_id=effective_session,
        image_url=req.image_url,
        file_urls=req.file_urls,
    )

    async def stream_with_post_jobs():
        async for chunk in generator:
            yield chunk

    return StreamingResponse(stream_with_post_jobs(), media_type="text/event-stream")


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

    file_id = uuid.uuid4().hex
    safe_name = f"{file_id}{suffix}"
    file_path = user_dir / safe_name

    file_path.write_bytes(content)
    url = f"/api/v1/ai/chat/uploads/{current_user.id}/{safe_name}"

    logger.info(f"[Upload] User {current_user.id} uploaded {file.filename} -> {url}")
    return HttpResponse.success(data=UploadResponse(
        url=url,
        file_type=file_type,
        original_name=file.filename,
        size_bytes=len(content),
    ).model_dump())


@router.get("/chat/uploads/{owner_id}/{filename}")
async def get_uploaded_file(
    owner_id: int,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """鉴权读取上传文件（仅允许本人访问）。"""
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该文件")

    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    user_dir = (UPLOAD_DIR / str(owner_id)).resolve()
    file_path = (user_dir / filename).resolve()
    if not str(file_path).startswith(str(user_dir)):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(path=str(file_path), filename=filename)


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
    session_id: str | None = Query(default=None, description="指定会话ID（不传则取最近会话）"),
    limit: int = Query(default=50, ge=1, le=200, description="返回的消息条数"),
    current_user: User = Depends(get_current_user),
):
    """获取聊天历史。"""
    target_session = session_id
    if not target_session:
        sessions = await memory_service.get_user_chat_sessions(
            current_user.id,
            module=tutor_agent.module_name,
            limit=1,
        )
        if not sessions:
            return HttpResponse.success(data=[])
        target_session = sessions[0].id

    messages = await memory_service.get_recent_messages(
        user_id=current_user.id,
        session_id=target_session,
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
