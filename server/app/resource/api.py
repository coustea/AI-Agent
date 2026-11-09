"""Resource 模块 HTTP 与 SSE 路由端点 (app.resource.api)。

对齐 chat.api 架构模式：纯函数式调用服务层，统一提供快照轮询、SSE 状态推送与取消控制。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth.security import UserClaims, get_current_user
from app.infra.logging import get_logger
from app.resource.schemas import (
    TERMINAL_STATUSES,
    ResourceGenerationRequest,
    encode_resource_sse,
)
from app.resource.service import (
    cancel_run,
    delete_resource_record,
    execute_resource_run,
    get_active_run,
    get_resource_bundle,
    get_resource_status,
    get_run_state,
    list_resource_history,
    list_resources,
    prepare_resource_run,
)
from app.response import HttpResponse

logger = get_logger(__name__)

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/resources")
async def list_resources_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """按用户分页查询独立教学资源列表。"""
    user = get_current_user()
    data = await list_resources(user.id, limit=limit, offset=offset)
    return HttpResponse.success(data=data)


@router.get("/resources/{resource_id}")
async def get_resource_detail_endpoint(resource_id: int) -> JSONResponse:
    """获取指定资源详情。"""
    user = get_current_user()
    bundle = await get_resource_bundle(user.id, resource_id)
    if bundle is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")
    return HttpResponse.success(data=bundle.model_dump())


@router.get("/resources/{resource_id}/status")
async def get_resource_status_endpoint(resource_id: int) -> JSONResponse:
    """获取指定资源生成状态。"""
    user = get_current_user()
    status_data = await get_resource_status(user.id, resource_id)
    if status_data is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")
    return HttpResponse.success(data=status_data)


@router.post("/resource/generate")
async def start_resource_generation(
    payload: ResourceGenerationRequest,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """接收统一资源生成请求，入库主记录并异步启动主 Agent 循环。"""
    user = get_current_user()
    try:
        if not payload.topic.strip():
            return HttpResponse.error(code=400, message="学习主题不能为空")

        run_id, resource_id = await prepare_resource_run(payload, user)
        background_tasks.add_task(execute_resource_run, run_id, payload, user)

        return HttpResponse.success(
            data={"run_id": run_id, "resource_id": resource_id},
            status_code=202,
        )
    except Exception as exc:
        logger.exception("启动资源生成失败: %s", exc)
        return HttpResponse.error(code=500, message=f"启动生成失败: {exc}")


@router.get("/resource/runs/{run_id}")
async def get_resource_run_snapshot(run_id: str) -> JSONResponse:
    """读取指定运行的当前全量状态快照（支持切页/刷新恢复）。"""
    user = get_current_user()
    state = await get_run_state(user.id, run_id)
    if state is None:
        return HttpResponse.error(code=404, message="运行记录不存在或无权限")
    return HttpResponse.success(data=state.model_dump())


@router.get("/resource/runs/{run_id}/events", response_model=None)
async def stream_resource_run_events(
    run_id: str,
    user: UserClaims | None = None,
) -> JSONResponse | StreamingResponse:
    """基于订阅机制的 SSE 实时快照推流端点。"""
    user_claims = user or get_current_user()
    state = await get_run_state(user_claims.id, run_id)
    if state is None:
        return HttpResponse.error(code=404, message="运行记录不存在或无权限")

    hooks = get_active_run(run_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        """订阅通知队列，当产生新状态时推送全量快照。"""
        queue = hooks.subscribe() if hooks is not None else None
        try:
            current = hooks.snapshot() if hooks is not None else state
            while True:
                yield encode_resource_sse(current)
                if current.status in TERMINAL_STATUSES or queue is None:
                    return

                try:
                    await asyncio.wait_for(queue.get(), timeout=25)
                except TimeoutError:
                    yield ": heartbeat\n\n"
                else:
                    await asyncio.sleep(0.08)
                    if not queue.empty():
                        queue.get_nowait()
                current = hooks.snapshot()
        finally:
            if hooks is not None and queue is not None:
                hooks.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/resource/runs/{run_id}/cancel")
async def cancel_resource_generation(run_id: str) -> JSONResponse:
    """取消当前正在运行的教学资源生成任务。"""
    user = get_current_user()
    status = await cancel_run(user.id, run_id)
    if status is None:
        return HttpResponse.error(code=404, message="运行不存在或已结束")
    return HttpResponse.success(data={"run_id": run_id, "status": status})


@router.get("/resource/bundles/{resource_id}")
async def get_bundle_by_id(resource_id: int) -> JSONResponse:
    """获取生成完成的完整教学资源包 DTO。"""
    user = get_current_user()
    bundle = await get_resource_bundle(user.id, resource_id)
    if bundle is None:
        return HttpResponse.error(code=404, message="教学资源包不存在或无权限")
    return HttpResponse.success(data=bundle.model_dump())


@router.get("/resource/history")
async def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    """获取用户的教学资源生成历史记录列表。"""
    user = get_current_user()
    items = await list_resource_history(user.id, limit=limit, offset=offset)
    return HttpResponse.success(data=[item.model_dump() for item in items])


@router.delete("/resource/{resource_id}")
async def delete_resource(resource_id: int) -> JSONResponse:
    """删除指定的教学资源记录。"""
    user = get_current_user()
    success = await delete_resource_record(user.id, resource_id)
    if not success:
        return HttpResponse.error(code=404, message="资源记录不存在或无权限")
    return HttpResponse.success(data={"deleted": True})
