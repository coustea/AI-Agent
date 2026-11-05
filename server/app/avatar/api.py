# -*- coding: utf-8 -*-
"""Avatar HTTP API — 管理端点（主服务 :9999 挂载）

提供数字人状态查询、流信息获取、停止控制等 HTTP 端点。
实际的 WebSocket 连接统一走主服务入口的 `/ws/avatar`。
"""

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.avatar.bridge.manager import avatar_bridge_manager
from app.infra.logging import get_logger
from app.infra.models import User
from app.response import HttpResponse

logger = get_logger(__name__)

# 数字人模块路由，挂载在 /api/v1/ai/avatar/ 下
router = APIRouter()


@router.get("/avatar/status")  # GET 数字人连接状态
async def get_avatar_status(
    user: User = Depends(get_current_user),
):
    """获取数字人连接状态"""
    status = await avatar_bridge_manager.get_status(user.id)
    logger.info("[AvatarAPI] 查询连接状态: user_id=%s connected=%s", user.id, status.get("connected"))
    return HttpResponse.success(data=status)


@router.get("/avatar/stream")  # GET 获取数字人视频流信息
async def get_avatar_stream(
    user: User = Depends(get_current_user),
):
    """获取数字人视频流信息"""
    stream_info = await avatar_bridge_manager.get_stream_info(user.id)
    # 流信息未就绪时返回 404
    if not stream_info:
        logger.info("[AvatarAPI] 视频流未就绪: user_id=%s", user.id)
        return HttpResponse.error(message="数字人视频流未就绪", code=404)
    return HttpResponse.success(data=stream_info)


@router.post("/avatar/stop")  # POST 停止数字人说话
async def stop_avatar(
    user: User = Depends(get_current_user),
):
    """停止数字人说话"""
    await avatar_bridge_manager.stop(user.id)
    logger.info("[AvatarAPI] 停止播报: user_id=%s", user.id)
    return HttpResponse.success(data={"status": "stopped"})


@router.post("/avatar/cleanup")  # POST 清理数字人连接资源
async def cleanup_avatar(
    user: User = Depends(get_current_user),
):
    """清理数字人连接资源"""
    await avatar_bridge_manager.cleanup(user.id)
    logger.info("[AvatarAPI] 清理连接资源: user_id=%s", user.id)
    return HttpResponse.success()
