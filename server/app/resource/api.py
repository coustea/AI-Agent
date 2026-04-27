"""Resource HTTP routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import decode_token, get_current_user, is_token_valid
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.schemas import PptGenerateRequest, ResourceGenerateRequest
from app.resource.service import resource_usecases
from app.shared.paths import RESOURCE_DIR, WORKPLACE_DIR
from app.shared.response import HttpResponse

router = APIRouter()
logger = get_logger(__name__)
PPT_DIR = WORKPLACE_DIR / "ppt"


def _extract_visible_agents_from_plan(plan_result: str | None) -> set[str] | None:
    """从 plan_result 中提取 visible_agents。

    兼容旧数据：旧记录没有 visible_agents 字段时返回 None（表示不过滤）。
    """
    if not plan_result:
        return None
    try:
        payload: dict[str, Any] = json.loads(plan_result)
    except (json.JSONDecodeError, TypeError):
        return None
    visible = payload.get("visible_agents")
    if not isinstance(visible, list):
        return None
    return {str(item) for item in visible if str(item).strip()}


@router.post("/generate")
async def generate_resources(
    req: ResourceGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    task_dict = req.learning_task.model_dump()
    logger.info(
        "[ResourceAPI] 收到生成请求: user_id=%s course=%r selected_resources=%s",
        current_user.id,
        task_dict.get("course", ""),
        req.selected_resources,
    )
    return StreamingResponse(
        resource_usecases.stream_bundle(
            user_id=current_user.id,
            task=task_dict,
            selected_resources=req.selected_resources,
        ),
        # 这里直接返回 text/event-stream，让前端一边接收一边更新工作看板。
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents():
    logger.info("[ResourceAPI] 查询可用 Agent 列表")
    return HttpResponse.success(data=resource_usecases.list_agents())


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    logger.info("[ResourceAPI] 查询资源列表: user_id=%s limit=%s", current_user.id, limit)
    resources = await resource_usecases.list_resources(session, current_user.id, limit)

    items: list[dict[str, Any]] = []
    for value in resources:
        visible = _extract_visible_agents_from_plan(value.plan_result)
        items.append(
            {
                "id": value.id,
                "course": value.course,
                "gap": value.gap,
                "need": value.need,
                "status": value.status,
                "has_mindmap": value.mindmap_result is not None and (visible is None or "mindmap" in visible),
                "has_content": value.content_result is not None and (visible is None or "content" in visible),
                "has_code": value.code_result is not None and (visible is None or "code" in visible),
                "has_quiz": value.quiz_result is not None and (visible is None or "quiz" in visible),
                "has_reading": value.reading_result is not None and (visible is None or "reading" in visible),
                "has_image": value.image_result is not None and (visible is None or "image" in visible),
                "has_ppt": value.ppt_result is not None and (visible is None or "ppt" in visible),
                "has_video": value.video_result is not None and (visible is None or "video" in visible),
                "created_at": value.created_at,
            }
        )
    return HttpResponse.success(data=items)


@router.get("/resources/{resource_id}/files/{filename}")
async def get_resource_file(
    resource_id: int,
    filename: str,
    token: str = Query(..., description="资源文件访问 token"),
    session: AsyncSession = Depends(get_session),
):
    if not await is_token_valid(token, session):
        raise HTTPException(status_code=401, detail="Token 已失效或已退出登录")
    user_id = decode_token(token)

    resource = await resource_usecases.get_resource(session, user_id, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在")

    safe_filename = Path(filename).name
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    resource_dir = (RESOURCE_DIR / str(user_id) / str(resource_id)).resolve()
    file_path = (resource_dir / safe_filename).resolve()
    if not str(file_path).startswith(str(resource_dir)):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(path=str(file_path), filename=safe_filename)


@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    logger.info("[ResourceAPI] 查询资源详情: user_id=%s resource_id=%s", current_user.id, resource_id)
    resource = await resource_usecases.get_resource(session, current_user.id, resource_id)
    if resource is None:
        logger.warning("[ResourceAPI] 资源不存在或无权限: user_id=%s resource_id=%s", current_user.id, resource_id)
        return HttpResponse.error(code=404, message="资源不存在")

    data = {
        "id": resource.id,
        "course": resource.course,
        "gap": resource.gap,
        "need": resource.need,
        "status": resource.status,
        "request_extra": resource.request_extra,
        "plan_result": resource.plan_result,
        "results": {},
        "created_at": resource.created_at,
    }
    visible_agents = _extract_visible_agents_from_plan(resource.plan_result)
    for key in ("mindmap", "content", "code", "quiz", "reading", "image", "ppt", "video"):
        if visible_agents is not None and key not in visible_agents:
            continue
        raw = getattr(resource, f"{key}_result")
        if raw:
            try:
                data["results"][key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                # 新架构里仍允许个别资源先以纯文本落库，详情页不因为单个解析失败而中断。
                data["results"][key] = raw
    return HttpResponse.success(data=data)


@router.post("/ppt/generate")
async def generate_ppt_direct(
    req: PptGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """直接调用 PPT Agent（AI 规划 + 模板渲染），不走整套资源编排。"""
    logger.info(
        "[ResourceAPI] 直连 PPT 生成: user_id=%s topic=%r template=%s",
        current_user.id,
        req.topic,
        req.template_id,
    )
    from app.resource.agents.ppt import ppt_agent

    result = await ppt_agent.generate_ppt(
        topic=req.topic,
        course=req.course,
        major=req.major,
        gap=req.gap,
        user_profile={},
        shared_memory={},
        template_id=req.template_id,
        template_source_url=req.template_source_url or "",
        template_config_url=req.template_config_url or "",
    )
    if not result.get("success"):
        return HttpResponse.error(code=500, message=result.get("error") or "PPT 生成失败", data=result)

    file_path = str(result.get("file_path") or "")
    filename = Path(file_path).name if file_path else ""
    file_url = f"/api/v1/ai/ppt/files/{filename}" if filename else None
    data = {
        "success": True,
        "topic": req.topic,
        "file_path": file_path,
        "file_url": file_url,
        "slide_count": result.get("slide_count", 0),
        "slide_titles": result.get("slide_titles", []),
        "template_id": result.get("template_id", req.template_id),
        "style": result.get("style", ""),
    }
    return HttpResponse.success(data=data)


@router.get("/ppt/files/{filename}")
async def get_ppt_file(
    filename: str,
    token: str = Query(..., description="PPT 文件访问 token"),
    session: AsyncSession = Depends(get_session),
):
    """下载直连 PPT 生成文件。"""
    if not await is_token_valid(token, session):
        raise HTTPException(status_code=401, detail="Token 已失效或已退出登录")
    _ = decode_token(token)

    safe_filename = Path(filename).name
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    ppt_dir = PPT_DIR.resolve()
    file_path = (ppt_dir / safe_filename).resolve()
    if not str(file_path).startswith(str(ppt_dir)):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path=str(file_path), filename=safe_filename)
