"""
Resource HTTP routes.

API 端点：
- POST /resources - 创建后台资源生成任务
- GET /resources/{id}/status - 查询任务执行状态
- GET /resources/{id}/events - SSE 推送任务事件
- GET /resources - 查询资源列表
- GET /resources/{id} - 查询资源详情
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserClaims
from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.profile.context import ProfileScope, load_learner_context
from app.resource.schemas import ResourceGenerationRequest
from app.resource.service import ResourceService
from app.resource.orchestrator import run_multi_agent_generation
from app.response import HttpResponse
from app.resource.event import (
    RESOURCE_TERMINAL_EVENTS,
    ResourceEvents,
    encode_resource_sse,
    _to_event,
)


router = APIRouter()
logger = get_logger(__name__)

@router.post("/resources")
async def create_resource_task(
    req: ResourceGenerationRequest,
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """启动独立资源生成后台任务。"""
    logger.info(
        "[ResourceAPI] 收到后台生成请求: user_id=%s selected_agents=%s",
        current_user.id,
        req.enabled_agent_ids(),
    )
    learner_ctx = await load_learner_context(
        session,
        user_id=current_user.id,
        scope=ProfileScope.RESOURCE,
        topic=req.topic or req.learning_need or "",
    )
    profile_markdown = learner_ctx.to_prompt_text(ProfileScope.RESOURCE)
    service = ResourceService(session)
    result = await service.create_task(
        user_id=current_user.id,
        request=req,
        profile_markdown=profile_markdown,
        username=current_user.username,
    )
    resource_id = result["resource_id"]

    # 启动后台生成（fire-and-forget，不阻塞 Event Loop）
    asyncio.create_task(
        run_multi_agent_generation(
            user_id=current_user.id,
            resource_id=resource_id,
        )
    )

    # 立即返回 resource_id，实际生成在后台进行
    logger.info(
        "[ResourceAPI] 后台生成任务已创建: user_id=%s resource_id=%s",
        current_user.id, resource_id,
    )
    return HttpResponse.success(data={"resource_id": resource_id, "status": "pending"}, status_code=201)


@router.get("/resources/{resource_id}/status")
async def get_generation_status(
    resource_id: int,
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """查询后台生成任务的状态。"""
    logger.debug("[ResourceAPI] 查询生成状态: user_id=%s resource_id=%s", current_user.id, resource_id)
    service = ResourceService(session)
    status_data = await service.get_generation_status(
        user_id=current_user.id,
        resource_id=resource_id,
    )
    # 资源不存在或无权限时返回 404
    if status_data is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")
    return HttpResponse.success(data=status_data)


@router.get("/resources/{resource_id}/events")
async def get_resource_events(
    resource_id: int,
    after_sequence: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """SSE 推送任务事件。"""
    logger.debug("[ResourceAPI] SSE订阅: user_id=%s resource_id=%s after=%s", current_user.id, resource_id, after_sequence)
    # 验证资源所有权
    service = ResourceService(session)
    resource = await service.get_resource(
        current_user.id,
        resource_id,
    )
    # 资源不存在或无权限时拒绝订阅
    if resource is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")

    resume_sequence = after_sequence
    # 若客户端携带 Last-Event-ID，则从该序号之后续传
    if last_event_id and last_event_id.isdigit():
        resume_sequence = max(resume_sequence, int(last_event_id))

    async def event_generator() -> AsyncIterator[str]:
        """异步生成 SSE 事件流并在遇到终态事件或超时时退出。"""
        events = ResourceEvents(user_id=current_user.id, resource_id=resource_id)
        queue: asyncio.Queue | None = None
        delivered_sequence = resume_sequence
        try:
            # 先订阅再读取数据库，避免历史读取与实时订阅之间遗漏事件。
            queue = await events.subscribe()
            replay = await service.list_run_events(
                resource_id=resource_id,
                after_sequence=resume_sequence,
            )
            for row in replay:
                event = _to_event(row)
                delivered_sequence = event.sequence
                yield encode_resource_sse(event)
                if event.event in RESOURCE_TERMINAL_EVENTS:
                    return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    if event.sequence <= delivered_sequence:
                        continue
                    delivered_sequence = event.sequence
                    yield encode_resource_sse(event)
                    if event.event in RESOURCE_TERMINAL_EVENTS:
                        break
                except asyncio.TimeoutError:
                    # 超时无新事件，发送心跳保持连接
                    yield ": heartbeat\n\n"
        except Exception as e:
            logger.error("SSE 事件生成器错误: %s", e)
        finally:
            if queue is not None:
                await events.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """查询资源列表。"""
    logger.debug("[ResourceAPI] 查询资源列表: user_id=%s limit=%d offset=%d", current_user.id, limit, offset)
    service = ResourceService(session)
    resources = await service.list_resources(
        current_user.id,
        limit,
        offset,
    )
    total = await service.count_resources(current_user.id)
    # 汇总每个资源的 agent_type，便于前端分类展示
    type_summary = await service.list_resource_type_summary(
        user_id=current_user.id,
        resource_ids=[value.id for value in resources if value.id is not None],
    )

    items: list[dict[str, Any]] = []
    for value in resources:
        items.append(
            {
                "id": value.id,
                "learning_need": value.learning_need,
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
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """查询资源详情。"""
    logger.debug("[ResourceAPI] 查询资源详情: user_id=%s resource_id=%s", current_user.id, resource_id)
    service = ResourceService(session)
    bundle = await service.get_resource_bundle(
        current_user.id,
        resource_id,
    )
    if bundle is None:
        return HttpResponse.error(code=404, message="资源不存在")
    return HttpResponse.success(data=bundle.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# 仪表盘端点
# ---------------------------------------------------------------------------


def _text(value: Any, fallback: str = "") -> str:
    """安全提取文本值，空值时返回默认值。"""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def _status_label(value: str) -> str:
    """将状态值转换为中文标签。"""
    return {
        "pending": "等待中",
        "generating": "生成中",
        "processing": "处理中",
        "completed": "已完成",
        "failed": "失败",
    }.get(value, value or "待更新")


def _resource_title(resource: Any) -> str:
    """获取资源标题。"""
    if not resource:
        return ""
    return _text(resource.learning_need, "最近生成的资源")


@router.get("/dashboard/recent-resources")
async def get_recent_resources(
    current_user: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """获取最近生成的学习资源列表。"""
    """获取最近生成的学习资源列表。"""
    from app.infra.models import GeneratedResource, GeneratedResourceItem

    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(GeneratedResource.user_id == current_user.id)
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(5)
    )).all())

    result: list[dict[str, Any]] = []
    for r in recent_resources[:4]:
        first_item = (await session.exec(
            select(GeneratedResourceItem)
            .where(GeneratedResourceItem.resource_id == r.id)
            .limit(1)
        )).first()
        result.append({
            "id": r.id,
            "title": _resource_title(r),
            "type": first_item.agent_type if first_item else _status_label(r.status),
            "agent": first_item.agent_type or "资源生成智能体" if first_item else "资源生成智能体",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return HttpResponse.success(data=result)
