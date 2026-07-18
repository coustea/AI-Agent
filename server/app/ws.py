"""WebSocket 路由模块。

提供数字人语音对话的 WebSocket 端点。
"""

# 本模块提供数字人语音对话的 WebSocket 端点，处理鉴权、桥接与资源清理
from __future__ import annotations

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.auth.security import AuthError, _resolve_current_user_from_token
from app.avatar.bridge.manager import avatar_bridge_manager
from app.infra.database import session_scope
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 创建 WebSocket 路由实例
router = APIRouter()


# WebSocket 端点：数字人语音对话
# WebSocket 端点：数字人语音对话，负责鉴权、连接桥接与断开清理
@router.websocket("/ws/avatar")
async def avatar_websocket(websocket: WebSocket) -> None:
    """数字人语音对话 WebSocket 端点。

    连接流程：
    1. 从 URL query 参数中提取 JWT Token（WebSocket 不支持自定义 header）
    2. 验证 Token 有效性，解析出用户信息
    3. 接受 WebSocket 连接
    4. 创建或复用数字人桥接实例，处理双向语音流
    5. 连接断开时清理资源
    """
    # 从 query 参数提取 JWT Token（WebSocket 不支持自定义 header）
    token = websocket.query_params.get("token", "").strip()
    if not token:
        # 1008 = Policy Violation
        logger.warning("[AvatarWS] WebSocket 连接缺少 token")
        await websocket.close(code=1008, reason="missing token")
        return

    try:
        # 验证 Token 并解析用户信息（WebSocket 无法使用 DI，需要手动创建 session）
        async with session_scope() as session:
            user = await _resolve_current_user_from_token(token, session)
    except AuthError:
        # Token 无效或已过期
        logger.warning("[AvatarWS] WebSocket token 验证失败")
        await websocket.close(code=1008, reason="invalid token")
        return

    # 接受 WebSocket 连接
    await websocket.accept()
    logger.info("[AvatarWS] WebSocket 连接建立: user_id=%s username=%s", user.id, user.username)
    # 获取或创建当前用户的数字人桥接实例
    bridge, owner = await avatar_bridge_manager.attach_frontend(
        user.id,
        websocket,
        username=user.username,
    )
    try:
        # 进入消息循环，处理前端语音数据并转发到 TTS/ASR 服务
        await bridge.handle_frontend(websocket, owner)
    except WebSocketDisconnect:
        # 客户端正常断开连接，静默处理
        pass
    finally:
        # 清理桥接资源（音频流、连接池等）
        await avatar_bridge_manager.cleanup(user.id, bridge, owner)
        logger.info("[AvatarWS] WebSocket 连接断开: user_id=%s", user.id)
