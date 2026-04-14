"""Chat 路由：辅导对话 + 会话管理 + 聊天历史 + 文件上传。

- /chat/stream: TutorAgent 前台辅导答疑（后处理链路由 TutorAgent 内部触发）
- /chat/upload: 文件上传（图片/文档）
- /chat/sessions, /chat/history: 会话与历史查询
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from app.core.logging import get_logger
from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.models.user import User
from app.services.memory import memory_service
from app.modules.chat.agent import tutor_agent
from app.modules.chat.resource_cards import build_resource_cards_from_tool_calls
from app.modules.chat.schemas import MentorChatRequest, ChatMessageItem, UploadResponse, AttachmentInfo, ToolCallRecord, ResourceCard
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


async def _save_upload(file: UploadFile, user_id: int, session_id: str) -> tuple[str, str]:
    """保存上传文件并返回 (url, file_type)。"""
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix in ALLOWED_IMAGE_EXT:
        file_type = "image"
        max_size = MAX_IMAGE_SIZE
    elif suffix in ALLOWED_DOC_EXT:
        file_type = "document"
        max_size = MAX_DOC_SIZE
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（{max_size // (1024 * 1024)}MB）")

    session_dir = UPLOAD_DIR / str(user_id) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    safe_name = f"{file_id}{suffix}"
    (session_dir / safe_name).write_bytes(content)

    url = f"/api/v1/ai/chat/uploads/{user_id}/{session_id}/{safe_name}"
    return url, file_type


@router.post("/chat/stream")
async def mentor_chat_stream(
    message: str = Form(...),
    session_id: str = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
):
    """TutorAgent 辅导答疑（主功能），支持表单上传文件。"""
    effective_session = session_id or _default_session_id(current_user.id)

    image_urls: list[str] = []
    file_urls: list[str] = []
    for f in files:
        url, file_type = await _save_upload(f, current_user.id, effective_session)
        if file_type == "image":
            image_urls.append(url)
        else:
            file_urls.append(url)

    generator = tutor_agent.chat_stream(
        user_id=current_user.id,
        user_message=message,
        session_id=effective_session,
        image_urls=image_urls or None,
        file_urls=file_urls or None,
    )

    async def stream_with_post_jobs():
        async for chunk in generator:
            yield chunk

    return StreamingResponse(stream_with_post_jobs(), media_type="text/event-stream")


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """上传图片或文档，按 userId/sessionId 存储并返回可访问的 URL。"""
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

    session_dir = UPLOAD_DIR / str(current_user.id) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    safe_name = f"{file_id}{suffix}"
    file_path = session_dir / safe_name

    file_path.write_bytes(content)
    url = f"/api/v1/ai/chat/uploads/{current_user.id}/{session_id}/{safe_name}"

    logger.info(f"[Upload] User {current_user.id} session {session_id} uploaded {file.filename} -> {url}")
    return HttpResponse.success(data=UploadResponse(
        url=url,
        file_type=file_type,
        original_name=file.filename,
        size_bytes=len(content),
    ).model_dump())


@router.get("/chat/uploads/{owner_id}/{session_id}/{filename}")
async def get_uploaded_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """鉴权读取上传文件（仅允许本人访问）。"""
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该文件")

    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    session_dir = (UPLOAD_DIR / str(owner_id) / session_id).resolve()
    file_path = (session_dir / filename).resolve()
    if not str(file_path).startswith(str(session_dir)):
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

        # 解析 tool_calls JSON（仅供后端调试与兼容回退）
        tool_calls = None
        raw_tc = None
        if msg.tool_calls:
            try:
                raw_tc = json.loads(msg.tool_calls)
                tool_calls = [ToolCallRecord(**tc) for tc in raw_tc]
            except (json.JSONDecodeError, TypeError):
                tool_calls = None
                raw_tc = None

        resource_cards = None
        if msg.resource_cards:
            try:
                raw_cards = json.loads(msg.resource_cards)
                resource_cards = [ResourceCard(**card) for card in raw_cards]
            except (json.JSONDecodeError, TypeError):
                resource_cards = None
        elif raw_tc:
            derived_cards = build_resource_cards_from_tool_calls(raw_tc)
            if derived_cards:
                resource_cards = [ResourceCard(**card) for card in derived_cards]

        items.append(ChatMessageItem(
            role=msg.role,
            content=msg.content,
            attachments=attachments,
            tool_calls=None,
            resource_cards=resource_cards,
            created_at=msg.created_at,
        ))
    return HttpResponse.success(data=items)
