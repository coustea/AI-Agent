"""Application websocket routes."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.auth.security import AuthError, _resolve_current_user_from_token
from app.avatar.bridge.manager import avatar_bridge_manager

router = APIRouter()


@router.websocket("/ws/avatar")  # WebSocket 端点：数字人语音对话
async def avatar_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "").strip()  # 从 query 参数提取 JWT Token（WebSocket 不支持自定义 header）
    if not token:
        await websocket.close(code=1008, reason="missing token")  # 1008 = Policy Violation
        return

    try:
        user = await _resolve_current_user_from_token(token)  # 验证 Token 并解析用户
    except AuthError:
        await websocket.close(code=1008, reason="invalid token")  # Token 无效或已过期
        return

    await websocket.accept()  # 接受 WebSocket 连接
    bridge = await avatar_bridge_manager.get_or_create_bridge(user.id)  # 获取或创建数字人桥接实例
    try:
        await bridge.handle_frontend(websocket)  # 进入消息循环，转发前端语音到 TTS/ASR
    except WebSocketDisconnect:
        pass  # 客户端正常断开，静默处理
    finally:
        await avatar_bridge_manager.cleanup(user.id)  # 清理桥接资源（音频流、连接池等）
