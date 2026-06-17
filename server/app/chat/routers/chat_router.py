"""SSE 流式对话 + 文件上传/读取路由。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, AsyncIterator

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.auth.security import get_current_user
from app.chat.service import chat, get_chat_usecases
from app.config import CHAT_DIR
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse

if TYPE_CHECKING:
    from app.chat.memory.service import ChatMemoryService

logger = get_logger(__name__)


def _get_chat_memory_service() -> "ChatMemoryService":
    return get_chat_usecases()._memory_service


async def _sse_wrap(events: AsyncIterator) -> AsyncIterator[str]:
    async for ev in events:
        etype = ev.get("event", "message")
        data = ev.get("data")
        data_str = json.dumps(data, ensure_ascii=False) if data is not None else ""
        yield f"event: {etype}\ndata: {data_str}\n\n"


def register_chat_routes(router: APIRouter) -> None:
    """将聊天核心端点注册到给定 router。"""

    @router.post("/chat/stream")
    async def mentor_chat_stream(
        user_input: str = Form(default=""),
        session_id: str | None = Form(default=None),
        attachments: str | None = Form(default=None),
        need_teaching_diagram: bool = Form(default=False),
        enable_web_search: bool = Form(default=False),
        current_user: User = Depends(get_current_user),
    ):
        uc = get_chat_usecases()
        parsed_attachments = [u.strip() for u in attachments.split(",") if u.strip()] if attachments else []
        effective_session = session_id or uc.default_session_id(current_user.id)
        effective_message = (user_input or "").strip()

        if not effective_message:
            return HttpResponse.error(code=400, message="请输入您的问题")

        logger.info(
            "[ChatAPI] 流式对话请求: user_id=%s session_id=%s msg_len=%d attachments=%d",
            current_user.id, effective_session, len(effective_message), len(parsed_attachments),
        )

        return StreamingResponse(
            _sse_wrap(chat(
                user_id=current_user.id,
                session_id=effective_session,
                user_input=effective_message,
                attachments=parsed_attachments or None,
                enable_web_search=enable_web_search,
                need_teaching_diagram=need_teaching_diagram,
            )),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/chat/upload")
    async def upload_file(
        file: UploadFile = File(...),
        session_id: str = Form(...),
        current_user: User = Depends(get_current_user),
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
        current_user: User = Depends(get_current_user),
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
        current_user: User = Depends(get_current_user),
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
        current_user: User = Depends(get_current_user),
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