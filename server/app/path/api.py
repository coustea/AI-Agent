import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.evaluation.schemas import LearningEventCreate
from app.infra.database import get_session
from app.infra.models import LearningEvent, LearningPath, PathNode, PathNodeResource, User
from app.infra.response import HttpResponse
from app.path.event import PathEvents, encode_path_sse, get_path_channel
from app.path.schemas import (
    PathRequest,
    LearningPathResourceDTO,
    PathQuizSubmitRequest,
)
from app.path.service import (
    PathService,
    build_learning_event_item,
    run_generation_bg,
    run_resource_generation_bg,
)
from uuid import uuid4

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])
# 单独的仪表盘路由（不带 prefix）
dashboard_router = APIRouter(tags=["dashboard"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# ── 路径创建 ───────────────────────────────────────────────────────────


# POST /api/v1/ai/path-plan — 创建学习路径，返回 path_id 和 run_id
@router.post("")  # POST /api/v1/ai/path-plan — 创建学习路径
async def create_path(
    request: PathRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    path_id = await service.create_path(current_user.id, request)
    run_id = str(uuid4())
    events = PathEvents(user_id=current_user.id, path_id=path_id, run_id=run_id)
    await events.open()
    background_tasks.add_task(  # 后台异步执行路径生成（LLM 规划 + 节点创建）
        run_generation_bg,
        user_id=current_user.id,
        path_id=path_id,
        request=request,
        run_id=run_id,
    )
    return HttpResponse.success(
        data={"id": path_id, "run_id": run_id, "status": "generating"},
        status_code=201,
    )


# ── SSE 事件流 ─────────────────────────────────────────────────────────


# SSE 端点：订阅路径规划实时事件流
@router.get("/{path_id}/runs/{run_id}/events")  # SSE 路径规划实时事件流
async def stream_path_plan_events(
    path_id: int,
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """订阅路径规划实时事件流 — 前端 usePathEvents 通过此端点接收生成进度。"""
    events = await get_path_channel(current_user.id, path_id, run_id)
    if events is None:
        return HttpResponse.error(code=410, message="事件流已过期或不存在")

    # SSE 事件流生成器：先重放历史事件，再持续推送新事件
    async def event_stream():
        queue, replay = await events.subscribe(after_sequence)
        try:
            for event in replay:
                yield encode_path_sse(event)
            if replay and replay[-1].event in {"planning.completed", "planning.failed", "resource.completed", "resource.failed"}:
                return
            if not replay and events.is_terminal and after_sequence >= events.last_sequence:
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    if events.is_terminal:
                        return
                    yield ": heartbeat\n\n"
                    continue
                yield encode_path_sse(event)
                if event.event in {"planning.completed", "planning.failed", "resource.completed", "resource.failed"}:
                    return
        finally:
            await events.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# ── 路径查询 ───────────────────────────────────────────────────────────


# 获取当前用户所有可继续学习的路径概览
@router.get("/active")  # GET /api/v1/ai/path-plan/active — 获取所有可继续学习路径
async def get_active_paths(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    responses = await service.list_active_path_overviews(current_user.id, module)
    return HttpResponse.success(data=[item.model_dump(mode="json") for item in responses])


# 获取最近更新的可继续学习路径概览
@router.get("/latest")
async def get_latest_active_path(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    response = await service.get_latest_active_path_overview(current_user.id, module)
    return HttpResponse.success(data=response.model_dump(mode="json") if response else None)


# 获取用户路径历史列表
@router.get("/history")  # GET /api/v1/ai/path-plan/history — 获取路径历史列表
async def get_path_history(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    items = await service.list_path_history(current_user.id, module)
    return HttpResponse.success(data=[item.model_dump(mode="json") for item in items])


# 激活历史路径，同时归档其他激活路径
@router.post("/{path_id}/activate")  # POST /api/v1/ai/path-plan/{id}/activate — 激活历史路径
async def activate_history_path(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.activate_history_path(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


# ── 节点工作区 ───────────────────────────────────────────────────────────


# 获取节点学习工作区（教程、资源、测验状态）
@router.get("/nodes/{node_id}/workspace")  # GET /api/v1/ai/path-plan/nodes/{id}/workspace — 获取节点学习区
async def get_node_workspace(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_workspace(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))




# ── 节点学习流程 ───────────────────────────────────────────────────────────


# 标记节点开始学习（轻量，仅改状态）
@router.post("/nodes/{node_id}/start-learning")  # POST 标记节点开始学习（轻量）
async def start_learning(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.start_learning(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


# 为节点生成教程内容（耗时，调用 LLM）
@router.post("/nodes/{node_id}/tutorial")  # POST 为节点生成教程（耗时）
async def generate_tutorial(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_tutorial(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


# ── 测验流程 ───────────────────────────────────────────────────────────


# 获取最新一轮已有测验题（不重新生成）
@router.get("/nodes/{node_id}/questions")  # GET 获取最新一轮已有测验题（不重新生成）
async def get_node_questions(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_questions(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


# 生成节点测验题，LLM 根据教程生成 5 道选择题
@router.post("/nodes/{node_id}/questions")  # POST 生成节点测验题 — LLM 根据教程生成 5 道题
async def generate_node_questions(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_questions(current_user.id, node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


# 提交测验答案并自动评分，决定节点下一步状态
@router.post("/nodes/{node_id}/quiz-submit")  # POST 提交节点测验 — 自动评分并决定下一步
async def submit_node_quiz(
    node_id: int,
    payload: PathQuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.submit_node_quiz(current_user.id, node_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


# ── 辅助资源生成 ───────────────────────────────────────────────────────────


# 支持的资源类型
RESOURCE_TYPES = {"mindmap", "code", "ppt", "reading", "cartoon"}


# 创建节点辅助资源生成任务（思维导图/代码实操/PPT/阅读/动画）
@router.post("/nodes/{node_id}/resources/{resource_type}")
async def generate_node_resource(
    node_id: int,
    resource_type: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """创建节点辅助资源生成任务 — 支持类型：mindmap, code, ppt, reading, cartoon"""
    logger.info(
        "[PathAPI] 收到资源生成请求: user_id=%s node_id=%s type=%s",
        current_user.id, node_id, resource_type,
    )
    if resource_type not in RESOURCE_TYPES:
        logger.warning("[PathAPI] 不支持的资源类型: %s", resource_type)
        return HttpResponse.error(code=400, message=f"不支持的资源类型: {resource_type}")
    service = PathService(session)
    run_id = str(uuid4())
    logger.info("[PathAPI] 生成 run_id: %s", run_id)
    try:
        result = await service.create_node_resource_task(
            current_user.id,
            node_id,
            resource_type,
            run_id,
        )
        logger.info(
            "[PathAPI] 资源任务创建成功: resource_id=%s type=%s",
            result.resource.id, resource_type,
        )
    except ValueError as exc:
        logger.error("[PathAPI] 资源任务创建失败: %s", exc)
        return HttpResponse.error(code=400, message=str(exc))
    events = PathEvents(user_id=current_user.id, path_id=result.resource.id, run_id=run_id)
    await events.open()
    logger.info(
        "[PathAPI] 添加后台任务: resource_id=%s run_id=%s",
        result.resource.id, run_id,
    )
    background_tasks.add_task(
        run_resource_generation_bg,
        user_id=current_user.id,
        resource_id=result.resource.id,
        run_id=run_id,
    )
    return HttpResponse.success(data=result.model_dump(mode="json"), status_code=202)


# 获取节点辅助资源
@router.get("/nodes/{node_id}/resources/{resource_type}")
async def get_node_resource(
    node_id: int,
    resource_type: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取节点辅助资源 — 支持类型：mindmap, code, ppt, reading, cartoon"""
    if resource_type not in RESOURCE_TYPES:
        return HttpResponse.error(code=400, message=f"不支持的资源类型: {resource_type}")
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, resource_type)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


# ── 资源列表与详情 ───────────────────────────────────────────────────────────


# 获取路径资源列表（支持分页）
@router.get("/resources")  # GET /api/v1/ai/path-plan/resources — 获取路径资源列表
async def list_path_resources(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(PathNodeResource)
        .where(PathNodeResource.user_id == current_user.id)
        .order_by(col(PathNodeResource.created_at).desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list((await session.exec(stmt)).all())
    node_map: dict[int, PathNode] = {}
    if rows:
        node_ids = {row.node_id for row in rows}
        node_rows = list((await session.exec(select(PathNode).where(PathNode.id.in_(node_ids)))).all())
        node_map = {node.id: node for node in node_rows if node.id is not None}
    total_stmt = select(func.count()).select_from(PathNodeResource).where(
        PathNodeResource.user_id == current_user.id
    )
    total = (await session.exec(total_stmt)).first() or 0
    return HttpResponse.success(data={
        "items": [
            {
                "id": row.id,
                "learning_need": row.title,
                "status": row.status or "completed",
                "error_message": row.error_message,
                "summary": row.summary,
                "resource_types": [row.resource_type],
                "resource_type": row.resource_type,
                "title": row.title,
                "path_id": row.path_id,
                "path_node_id": row.node_id,
                "node_id": node_map.get(row.node_id).node_id if node_map.get(row.node_id) else None,
                "node_title": node_map.get(row.node_id).title if node_map.get(row.node_id) else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
        "total": total,
    })


# 资源生成 SSE 端点
@router.get("/resources/{resource_id}/runs/{run_id}/events")
async def stream_path_resource_events(
    resource_id: int,
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
):
    events = await get_path_channel(current_user.id, resource_id, run_id)
    if events is None:
        return HttpResponse.error(code=410, message="事件流已过期或不存在")

    async def event_stream():
        queue, replay = await events.subscribe(after_sequence)
        try:
            for event in replay:
                yield encode_path_sse(event)
            if replay and replay[-1].event in {"resource.completed", "resource.failed"}:
                return
            if not replay and events.is_terminal and after_sequence >= events.last_sequence:
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    if events.is_terminal:
                        return
                    yield ": heartbeat\n\n"
                    continue
                yield encode_path_sse(event)
                if event.event in {"resource.completed", "resource.failed"}:
                    return
        finally:
            await events.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# 获取单个路径资源详情
@router.get("/resources/{resource_id}")  # GET 路径资源详情
async def get_path_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    resource = await session.get(PathNodeResource, resource_id)
    if resource is None or resource.user_id != current_user.id:
        return HttpResponse.error(code=404, message="路径资源不存在")
    return HttpResponse.success(data=LearningPathResourceDTO.from_model(resource).model_dump(mode="json"))


# 获取路径详情（含所有节点）
@router.get("/{path_id}")  # GET /api/v1/ai/path-plan/{id} — 获取路径详情（含所有节点）
async def get_path_by_id(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        response = await service.get_path_by_id(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=404, message=str(exc))
    return HttpResponse.success(data=response.model_dump(mode="json"))


# ── 学习事件与评估 ───────────────────────────────────────────────────────────


# 记录路径学习事件
@router.post("/{path_id}/events")
async def record_path_learning_event(
    path_id: int,
    payload: LearningEventCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        event_result = await service.record_learning_event(current_user.id, path_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    if isinstance(event_result, tuple):
        event = event_result[0]
        if len(event_result) > 1 and isinstance(event_result[1], dict):
            event.event_metadata = {**(event.event_metadata or {}), **event_result[1]}
    else:
        event = event_result
    if not event.entity_id:
        event.entity_id = str(path_id)
    if not event.module:
        event.module = "path"
    event.event_metadata = {
        **(event.event_metadata or {}),
        "path_node_id": getattr(event, "path_node_id", None) or payload.path_node_id,
        "node_id": getattr(event, "node_id", None) or payload.node_id,
    }
    event_item = build_learning_event_item(event).model_dump(mode="json")
    return HttpResponse.success(data=event_item)


# 获取路径学习评估（学习信号 + 优化建议）
@router.get("/{path_id}/evaluation")  # GET 路径学习评估 — 汇总学习信号和优化建议
async def get_path_learning_evaluation(
    path_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        evaluation = await service.get_learning_evaluation(current_user.id, path_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=evaluation.model_dump(mode="json") if evaluation else None)


# ── 仪表盘端点（从 dashboard 模块迁移）───────────────────────────────────


# 获取当前学习节点：优先可用状态，其次有缺陷完成状态
def _current_node(path_nodes: list[PathNode]) -> PathNode | None:
    """获取当前学习路径节点（优先可用状态，其次已完成有缺陷状态）。"""
    for status in ("available", "completed_with_gaps"):
        for node in path_nodes:
            if node.status == status:
                return node
    return path_nodes[0] if path_nodes else None


# 仪表盘：获取继续学习数据（每条活跃路径的当前节点）
@dashboard_router.get("/dashboard/continue-learning")
async def get_continue_learning(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取继续学习数据 — 每条活跃路径的当前节点（一条路径只显示一个节点）。"""
    active_paths = list((await session.exec(
        select(LearningPath)
        .where(LearningPath.user_id == current_user.id, LearningPath.status == "active")
        .order_by(col(LearningPath.updated_at).desc())
        .limit(5)
    )).all())

    if not active_paths:
        return HttpResponse.success(data={"active_paths": []})

    result = []
    for path in active_paths:
        # 获取每条路径的节点
        path_nodes = list((await session.exec(
            select(PathNode)
            .where(PathNode.user_id == current_user.id, PathNode.path_id == path.id)
            .order_by(col(PathNode.priority).asc(), col(PathNode.updated_at).desc())
            .limit(12)
        )).all())
        current_node = _current_node(path_nodes)

        # 获取该路径的最后学习时间
        last_learned_at: datetime | None = None
        last_event = (await session.exec(
            select(LearningEvent)
            .where(
                LearningEvent.user_id == current_user.id,
                LearningEvent.module == "path",
                LearningEvent.entity_id == str(path.id),
            )
            .order_by(col(LearningEvent.created_at).desc())
            .limit(1)
        )).first()
        if last_event:
            last_learned_at = last_event.created_at

        result.append({
            "id": path.id,
            "title": path.title,
            "overall_progress": path.overall_progress,
            "current_node_title": current_node.title if current_node else None,
            "current_node_id": current_node.node_id if current_node else None,
            "updated_at": path.updated_at.isoformat() if path.updated_at else None,
            "last_learned_at": last_learned_at.isoformat() if last_learned_at else None,
        })

    return HttpResponse.success(data={"active_paths": result})


