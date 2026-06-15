"""WebSocket 路由模块（旧版本）。

提供数字人语音对话的 WebSocket 端点。
注意：此文件为旧版本，新路由已迁移至 ws_routes.py。
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.auth.security import AuthError, _resolve_current_user_from_token
from app.avatar.bridge.manager import avatar_bridge_manager

# 创建路由实例
router = APIRouter()


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
    # 从 query 参数提取 JWT Token
    token = websocket.query_params.get("token", "").strip()
    if not token:
        # 缺少 Token，以 1008（Policy Violation）关闭连接
        await websocket.close(code=1008, reason="missing token")
        return

    try:
        # 验证 Token 并解析用户信息
        user = await _resolve_current_user_from_token(token)
    except AuthError:
        # Token 无效或已过期
        await websocket.close(code=1008, reason="invalid token")
        return

    # 接受 WebSocket 连接
    await websocket.accept()
    # 获取或创建当前用户的数字人桥接实例
    bridge = await avatar_bridge_manager.get_or_create_bridge(user.id)
    try:
        # 进入消息循环，处理前端语音数据并转发到 TTS/ASR 服务
        await bridge.handle_frontend(websocket)
    except WebSocketDisconnect:
        # 客户端正常断开连接，静默处理
        pass
    finally:
        # 清理桥接资源（音频流、连接池等）
        await avatar_bridge_manager.cleanup(user.id)
