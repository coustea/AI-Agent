"""会话 CRUD + 历史记录路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.security import get_current_user
from app.chat.service import get_chat_usecases
from app.infra.logging import get_logger
from app.infra.models import User
from app.infra.response import HttpResponse

logger = get_logger(__name__)


def register_session_routes(router: APIRouter) -> None:
    """将会话管理端点注册到给定 router。"""

    @router.get("/chat/sessions")
    async def get_sessions(
        limit: int = Query(default=20, ge=1, le=100),
        current_user: User = Depends(get_current_user),
    ):
        uc = get_chat_usecases()
        return HttpResponse.success(data=await uc.list_sessions(current_user.id, limit))

    @router.post("/chat/sessions")
    async def create_session(
        current_user: User = Depends(get_current_user),
    ):
        uc = get_chat_usecases()
        return HttpResponse.success(data=await uc.create_session(current_user.id), status_code=201)

    @router.delete("/chat/sessions/{session_id}")
    async def delete_session(
        session_id: str,
        current_user: User = Depends(get_current_user),
    ):
        uc = get_chat_usecases()
        success = await uc.archive_session(current_user.id, session_id)
        if not success:
            return HttpResponse.error(code=404, message="会话不存在或无权操作")
        return HttpResponse.success(message="会话已归档")

    @router.patch("/chat/sessions/{session_id}")
    async def update_session(
        session_id: str,
        payload: dict,
        current_user: User = Depends(get_current_user),
    ):
        title = (payload.get("title") or "").strip()
        if not title:
            return HttpResponse.error(code=400, message="标题不能为空")
        uc = get_chat_usecases()
        success = await uc.update_session_title(current_user.id, session_id, title)
        if not success:
            return HttpResponse.error(code=404, message="会话不存在或无权操作")
        return HttpResponse.success(message="标题已更新")

    @router.get("/chat/history")
    async def chat_history(
        session_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        current_user: User = Depends(get_current_user),
    ):
        uc = get_chat_usecases()
        items = await uc.get_history(
            user_id=current_user.id,
            session_id=session_id,
            limit=limit,
        )
        return HttpResponse.success(data=[item.model_dump() for item in items])