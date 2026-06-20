"""
Resource HTTP routes.

API 端点：
- POST /resources - 创建后台资源生成任务
- POST /resources/single - 创建单智能体资源生成任务
- GET /resources/{id}/status - 查询任务执行状态
- GET /resources/{id}/events - SSE 推送任务事件
- GET /agents - 查询可用 Agent 列表
- GET /resources - 查询资源列表
- GET /resources/{id} - 查询资源详情
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse

from app.auth.security import get_current_user, get_current_user_flexible
from app.config import WORKPLACE_DIR
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.resource.events import AgentEvent, resource_event_bus
from app.resource.schemas import AGENT_META, AGENT_DEFAULT_ORDER, ResourceGenerationRequest, SingleResourceRequest, AgentSelection
from app.resource.service import ResourceService
from app.resource.orchestrator import run_multi_agent_generation
from app.profile.service import get_profile_service
from app.infra.response import HttpResponse

STANDALONE_RESOURCE_SOURCES = ("standalone", "single_agent")


router = APIRouter()
logger = get_logger(__name__)


@router.post("/resources")
async def create_resource_task(
    req: ResourceGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动独立资源生成后台任务。"""
    logger.info(
        "[ResourceAPI] 收到后台生成请求: user_id=%s selected_agents=%s",
        current_user.id,
        req.enabled_agent_ids(),
    )
    repo = ResourceService(session)
    result = await repo.create_task(
        user_id=current_user.id,
        request=req,
        source="standalone",
    )
    resource_id = result["resource_id"]

    profile_builder = get_profile_service()
    profile_record = await profile_builder.get_profile(user_id=current_user.id)
    profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

    background_tasks.add_task(
        run_multi_agent_generation,
        user_id=current_user.id,
        request=req,
        profile=profile_dict,
        resource_id=resource_id,
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"}, status_code=201)


@router.post("/resources/single")
async def create_single_resource_task(
    req: SingleResourceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """启动单智能体资源生成后台任务（即调即用）。"""
    logger.info(
        "[ResourceAPI] 收到单智能体生成请求: user_id=%s agent_id=%s",
        current_user.id,
        req.agent_id.value,
    )

    profile_builder = get_profile_service()
    profile_record = await profile_builder.get_profile(user_id=current_user.id)
    profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

    repo = ResourceService(session)
    result = await repo.create_task(
        user_id=current_user.id,
        request=ResourceGenerationRequest(
            learning_need=req.learning_need,
            selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        ),
        source="single_agent",
    )
    resource_id = result["resource_id"]

    # 单智能体模式：通过多智能体流水线执行，只启用一个 agent
    background_tasks.add_task(
        run_multi_agent_generation,
        user_id=current_user.id,
        request=ResourceGenerationRequest(
            learning_need=req.learning_need,
            selected_agents=[AgentSelection(agent_id=req.agent_id, enabled=True)],
        ),
        profile=profile_dict,
        resource_id=resource_id,
    )

    return HttpResponse.success(data={"resource_id": resource_id, "status": "generating", "agent_id": req.agent_id.value}, status_code=201)


@router.get("/resources/{resource_id}/status")
async def get_generation_status(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询后台生成任务的状态。"""
    service = ResourceService(session)
    status_data = await service.get_generation_status(
        user_id=current_user.id,
        resource_id=resource_id,
        allowed_sources=STANDALONE_RESOURCE_SOURCES,
    )
    if status_data is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")
    return HttpResponse.success(data=status_data)


@router.get("/resources/{resource_id}/events")
async def stream_resource_events(
    resource_id: int,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    """SSE 端点：订阅资源生成事件，实时推送 agent 状态变更。"""
    service = ResourceService(session)
    resource = await service.get_resource(
        current_user.id,
        resource_id,
        allowed_sources=STANDALONE_RESOURCE_SOURCES,
    )
    if resource is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")

    async def event_stream():
        queue = resource_event_bus.subscribe(resource_id)
        try:
            snapshot = resource_event_bus.get_latest_snapshot(resource_id)
            for agent_id, agent_snapshot in snapshot.get("agent_snapshots", {}).items():
                snapshot_data = {
                    key: value
                    for key, value in agent_snapshot.items()
                    if key in AgentEvent.model_fields
                    and key not in {"event_type", "agent_id"}
                }
                snapshot_event = AgentEvent(
                    event_type="agent.snapshot",
                    agent_id=agent_id,
                    **snapshot_data,
                )
                yield f"event: {snapshot_event.event_type}\ndata: {snapshot_event.model_dump_json()}\n\n"

            await session.refresh(resource)
            if resource.status in {"completed", "partial_completed", "failed"}:
                done_event = AgentEvent(
                    event_type="resource.done",
                    success=resource.status in {"completed", "partial_completed"},
                    message="资源生成完成" if resource.status != "failed" else "资源生成失败",
                )
                yield f"event: {done_event.event_type}\ndata: {done_event.model_dump_json()}\n\n"
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield f": heartbeat\n\n"
                    continue
                data = event.model_dump_json()
                yield f"event: {event.event_type}\ndata: {data}\n\n"
                if event.event_type == "resource.done":
                    break
        finally:
            resource_event_bus.unsubscribe(resource_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/agents")
async def list_agents():
    """查询可用 Agent 列表。"""
    agents: list[dict[str, Any]] = []
    for agent_id in AGENT_DEFAULT_ORDER:
        meta = AGENT_META.get(agent_id, {})
        agents.append({
            "id": agent_id,
            "name": meta.get("name", agent_id),
            "icon": meta.get("icon", ""),
            "description": meta.get("description", ""),
            "configurable": True,
        })

    return HttpResponse.success(data=agents)


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源列表。"""
    service = ResourceService(session)
    resources = await service.list_resources(
        current_user.id,
        limit,
        offset,
        sources=STANDALONE_RESOURCE_SOURCES,
    )
    total = await service.count_resources(current_user.id, sources=STANDALONE_RESOURCE_SOURCES)
    type_summary = await service.list_resource_type_summary(
        user_id=current_user.id,
        resource_ids=[value.id for value in resources if value.id is not None],
    )

    items: list[dict[str, Any]] = []
    for value in resources:
        items.append(
            {
                "id": value.id,
                "learning_need": value.learning_need or "",
                "status": value.status,
                "resource_types": type_summary.get(value.id or 0, []),
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        )
    return HttpResponse.success(data={"items": items, "total": total})



@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """查询资源详情。"""
    service = ResourceService(session)
    bundle = await service.get_resource_bundle(
        current_user.id,
        resource_id,
        allowed_sources=STANDALONE_RESOURCE_SOURCES,
    )
    if bundle is None:
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))


@router.get("/video/audio/{filename:path}")
async def get_video_audio(
    filename: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """提供生成的视频音频文件。

    安全措施：
    - 用户认证
    - 目录遍历防护
    - 路径规范化检查
    """
    # 目录遍历安全检查
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        return HttpResponse.error(code=400, message="Illegal filename")

    # 只允许安全字符（字母、数字、下划线、横线、点）
    if not re.match(r'^[\w\-\.]+\.mp3$', filename):
        return HttpResponse.error(code=400, message="Invalid filename format")

    file_path = WORKPLACE_DIR / "video_audio" / filename

    # 路径规范化检查
    try:
        file_path = file_path.resolve()
        base_dir = (WORKPLACE_DIR / "video_audio").resolve()
        if not str(file_path).startswith(str(base_dir)):
            return HttpResponse.error(code=400, message="Path traversal detected")
    except Exception:
        return HttpResponse.error(code=400, message="Invalid path")

    if not file_path.exists():
        return HttpResponse.error(code=404, message="Audio file not found")

    return FileResponse(path=str(file_path), media_type="audio/mpeg")


@router.post("/video/render")
async def render_video(
    request: dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """从 VideoPayload JSON 触发 GPU 加速视频渲染。

    安全措施：
    - 用户认证
    - 参数白名单验证
    - 使用 subprocess 列表参数避免 shell 注入
    - 超时限制

    请求体：
        payload: VideoPayload JSON 对象
        gl: 可选 GPU 后端 — "angle"（默认）, "swiftshader", "egl"
    """
    payload = request.get("payload")
    if not payload or not isinstance(payload, dict):
        return HttpResponse.error(code=400, message="Missing 'payload' in request body")

    # gl 参数白名单
    gl = request.get("gl", "angle")
    if gl not in ("angle", "swiftshader", "egl"):
        return HttpResponse.error(code=400, message="Invalid gl parameter, must be one of: angle, swiftshader, egl")

    job_id = str(uuid.uuid4())[:8]

    # Paths
    video_render_dir = Path(__file__).resolve().parent.parent.parent.parent / "video-render"
    if not (video_render_dir / "package.json").exists():
        return HttpResponse.error(code=500, message="video-render project not found")

    work_dir = WORKPLACE_DIR / "video_render_jobs" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    plan_path = work_dir / "plan.json"
    output_path = work_dir / "output.mp4"

    # 写入 payload JSON 文件
    plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 使用列表参数避免 shell 注入
    render_script = video_render_dir / "scripts" / "render.ts"

    logger.info("Starting video render job %s with gl=%s", job_id, gl)

    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "tsx", str(render_script),
            "--input", str(plan_path),
            "--output", str(output_path),
            "--gl", gl,
            "--concurrency", "4",
            cwd=str(video_render_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)  # 10min max

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace")[-500:]
            logger.error("Render job %s failed: %s", job_id, err_msg)
            return HttpResponse.error(code=500, message=f"Render failed: {err_msg}")

        if not output_path.exists():
            return HttpResponse.error(code=500, message="Render output file not found")

        file_size_mb = output_path.stat().st_size / 1024 / 1024
        logger.info("Render job %s complete: %.1f MB", job_id, file_size_mb)

        return FileResponse(
            path=str(output_path),
            media_type="video/mp4",
            filename=f"{payload.get('title', 'video')}_{job_id}.mp4",
        )

    except asyncio.TimeoutError:
        logger.error("Render job %s timed out", job_id)
        return HttpResponse.error(code=504, message="Render timed out (10min limit)")
    except Exception as e:
        logger.error("Render job %s error: %s", job_id, e)
        return HttpResponse.error(code=500, message=f"Render error: {e}")
