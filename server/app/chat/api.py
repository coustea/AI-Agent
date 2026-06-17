"""聊天 HTTP 路由 — 组合各子路由。

所有端点挂载在 /api/v1/ai/chat/ 下，由 routes.py 统一注册到 FastAPI。
子路由按职责拆分到 routers/ 目录：
  - chat_router:    SSE 流式对话、文件上传/读取
  - session_router: 会话 CRUD、历史记录
  - profile_router: 画像 CRUD
  - school_router:   学校搜索
"""

from __future__ import annotations

from fastapi import APIRouter

from app.chat.routers.chat_router import register_chat_routes
from app.chat.routers.profile_router import register_profile_routes
from app.chat.routers.school_router import register_school_routes
from app.chat.routers.session_router import register_session_routes

router = APIRouter()

register_chat_routes(router)
register_session_routes(router)
register_profile_routes(router)
register_school_routes(router)