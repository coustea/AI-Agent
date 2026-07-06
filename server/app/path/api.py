from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import bg_apply_profile_update_from_learning_event
from app.infra.database import get_session
from app.infra.models import PathNode, PathNodeResource, User
from app.infra.response import HttpResponse
from app.path.event import PathEvents
from app.path.schemas import (
    PathRequest,
    LearningPathResourceDTO,
    PathQuizSubmitRequest,
)
from app.path.service import PathService, build_learning_event_item, run_generation_bg

router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])


# ── 路径创建 ───────────────────────────────────────────────────────────


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


# ── 路径查询 ───────────────────────────────────────────────────────────


@router.get("/active")  # GET /api/v1/ai/path-plan/active — 获取当前激活的学习路径
async def get_active_path(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    response = await service.get_active_path_overview(current_user.id, module)
    return HttpResponse.success(data=response.model_dump(mode="json") if response else None)


@router.get("/history")  # GET /api/v1/ai/path-plan/history — 获取路径历史列表
async def get_path_history(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    items = await service.list_path_history(current_user.id, module)
    return HttpResponse.success(data=[item.model_dump(mode="json") for item in items])


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


@router.post("/nodes/{node_id}/mindmap")  # POST 生成思维导图
async def generate_mindmap(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, "mindmap")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/code")  # POST 生成代码实操
async def generate_code(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, "code")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/ppt")  # POST 生成 PPT 课件
async def generate_ppt(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, "ppt")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/reading")  # POST 生成拓展阅读
async def generate_reading(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, "reading")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


@router.post("/nodes/{node_id}/content")  # POST 生成补充内容
async def generate_content(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, "content")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))



@router.post("/nodes/{node_id}/cartoon")  # POST 生成动画讲解资源
async def generate_cartoon(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.generate_node_resource(current_user.id, node_id, "cartoon")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json"))


# ── 辅助资源获取 ───────────────────────────────────────────────────────────


@router.get("/nodes/{node_id}/mindmap")  # GET 获取节点思维导图（最新版本）
async def get_mindmap(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, "mindmap")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


@router.get("/nodes/{node_id}/code")  # GET 获取节点代码实操
async def get_code(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, "code")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


@router.get("/nodes/{node_id}/ppt")  # GET 获取节点 PPT 课件
async def get_ppt(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, "ppt")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


@router.get("/nodes/{node_id}/reading")  # GET 获取节点拓展阅读
async def get_reading(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, "reading")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


@router.get("/nodes/{node_id}/content")  # GET 获取节点补充内容
async def get_content(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, "content")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)



@router.get("/nodes/{node_id}/cartoon")  # GET 获取节点动画讲解资源
async def get_cartoon(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        result = await service.get_node_resource_by_type(current_user.id, node_id, "cartoon")
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=result.model_dump(mode="json") if result else None)


# ── 资源列表与详情 ───────────────────────────────────────────────────────────


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
    total_stmt = select(PathNodeResource).where(PathNodeResource.user_id == current_user.id)
    total = len(list((await session.exec(total_stmt)).all()))
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


@router.post("/{path_id}/events")  # POST 记录路径学习事件 — 前端上报学习行为
async def record_path_learning_event(
    path_id: int,
    payload: LearningEventCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = PathService(session)
    try:
        event, profile_payload = await service.record_learning_event(current_user.id, path_id, payload)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    background_tasks.add_task(
        bg_apply_profile_update_from_learning_event,
        current_user.id,
        profile_payload,
    )
    return HttpResponse.success(data=build_learning_event_item(event).model_dump(mode="json"))


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


