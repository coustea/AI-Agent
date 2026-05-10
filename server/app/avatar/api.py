# -*- coding: utf-8 -*-
"""Avatar HTTP API — 管理端点（主服务 :9999 挂载）

提供数字人状态查询、流信息获取、停止控制等 HTTP 端点。
实际的 WebSocket 连接统一走主服务入口的 `/ws/avatar`。
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.auth.security import get_current_user
from app.chat.service import get_avatar_chat_usecases
from app.infra.models import User
from app.memory import MemoryLayer
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


@router.post("/avatar/history/clear")
async def clear_avatar_history(
    session_id: str | None = Form(default=None),
    user: User = Depends(get_current_user),
):
    """清空数字人会话历史消息（默认清空当前会话）。"""
    from app.avatar.bridge.manager import avatar_bridge_manager
    memory_layer = MemoryLayer(module="avatar")

    target_session_id = (session_id or "").strip()
    if not target_session_id:
        status = await avatar_bridge_manager.get_status(user.id)
        target_session_id = str(status.get("session_id") or "").strip()
    if not target_session_id:
        sessions = await memory_layer.list_sessions(user_id=user.id, limit=1)
        if sessions:
            target_session_id = sessions[0].id
    if not target_session_id:
        return HttpResponse.success(data={"session_id": "", "deleted_count": 0})

    deleted_count = await memory_layer.delete_short_term_messages(
        user_id=user.id,
        session_id=target_session_id,
    )
    await memory_layer.reset_session_counters(user_id=user.id, session_id=target_session_id)
    return HttpResponse.success(data={"session_id": target_session_id, "deleted_count": deleted_count})


@router.post("/avatar/attachments/analyze")
async def analyze_avatar_attachments(
    question: str = Form(...),
    session_id: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    file: UploadFile | None = File(default=None),
    image_urls: str | None = Form(default=None),
    file_urls: str | None = Form(default=None),
    user: User = Depends(get_current_user),
):
    """数字人可调用：上传并并行分析附件，返回结构化分析结果。"""
    uc = get_avatar_chat_usecases()

    upload_payloads: list[tuple[str, bytes]] = []
    all_uploads = list(files)
    if file is not None:
        all_uploads.append(file)
    for upload in all_uploads:
        if not upload.filename:
            return HttpResponse.error(code=400, message="文件名不能为空")
        upload_payloads.append((upload.filename, await upload.read()))

    parsed_image_urls: list[str] = []
    parsed_file_urls: list[str] = []
    if image_urls:
        parsed_image_urls = [u.strip() for u in image_urls.split(",") if u.strip()]
    if file_urls:
        parsed_file_urls = [u.strip() for u in file_urls.split(",") if u.strip()]

    try:
        payload = await uc.analyze_uploaded_attachments(
            user_id=user.id,
            question=question,
            session_id=session_id,
            files=upload_payloads,
            image_urls=parsed_image_urls,
            file_urls=parsed_file_urls,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except Exception as exc:
        return HttpResponse.error(code=500, message=f"附件分析失败: {exc}")

    return HttpResponse.success(data=payload)
