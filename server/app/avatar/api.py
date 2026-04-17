# -*- coding: utf-8 -*-
"""
Avatar HTTP API — 管理端点（主服务 :9999 挂载）

提供数字人状态查询、流信息获取、停止控制等 HTTP 端点。
实际的 WebSocket 连接走独立进程 (:8765)。
"""

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.infra.models import User
from app.shared.response import HttpResponse

router = APIRouter()


@router.get("/avatar/status")
async def get_avatar_status(
    user: User = Depends(get_current_user),
):
    """获取数字人连接状态"""
    from app.avatar.bridge.manager import avatar_bridge_manager
    status = await avatar_bridge_manager.get_status(user.id)
    return HttpResponse.success(data=status)


@router.get("/avatar/stream")
async def get_avatar_stream(
    user: User = Depends(get_current_user),
):
    """获取数字人视频流信息"""
    from app.avatar.bridge.manager import avatar_bridge_manager
    stream_info = await avatar_bridge_manager.get_stream_info(user.id)
    if not stream_info:
        return HttpResponse.error(message="数字人视频流未就绪", code=404)
    return HttpResponse.success(data=stream_info)


@router.post("/avatar/stop")
async def stop_avatar(
    user: User = Depends(get_current_user),
):
    """停止数字人说话"""
    from app.avatar.bridge.manager import avatar_bridge_manager
    await avatar_bridge_manager.stop(user.id)
    return HttpResponse.success(data={"status": "stopped"})


@router.post("/avatar/cleanup")
async def cleanup_avatar(
    user: User = Depends(get_current_user),
):
    """清理数字人连接资源"""
    from app.avatar.bridge.manager import avatar_bridge_manager
    await avatar_bridge_manager.cleanup(user.id)
    return HttpResponse.success()
