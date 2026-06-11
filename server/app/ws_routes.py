"""Application websocket routes."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.auth.security import AuthError, _resolve_current_user_from_token
from app.avatar.bridge.manager import avatar_bridge_manager

router = APIRouter()


@router.websocket("/ws/avatar")
async def avatar_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "").strip()
    if not token:
        await websocket.close(code=1008, reason="missing token")
        return

    try:
        user = await _resolve_current_user_from_token(token)
    except AuthError:
        await websocket.close(code=1008, reason="invalid token")
        return

    await websocket.accept()
    bridge = await avatar_bridge_manager.get_or_create_bridge(user.id)
    try:
        await bridge.handle_frontend(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        await avatar_bridge_manager.cleanup(user.id)
