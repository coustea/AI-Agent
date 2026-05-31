from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.path.schemas import GeneratePathRequest, PathNodeResourceRequest, PathPlanFeedbackRequest
from app.path.service import CoursePathService, bg_generate_path_task
from app.resource.service import bg_gen_task
from app.infra.response import HttpResponse

router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])
logger = get_logger(__name__)


@router.post("/generate")
async def generate_path(
    request: GeneratePathRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """创建异步路径规划任务，避免慢速模型调用阻塞 HTTP 请求。"""
    logger.info("[PathAPI] 路径规划请求: user_id=%s topic=%s", current_user.id, request.topic)
    service = CoursePathService(session)
    result = await service.start_generation_task(user_id=current_user.id, request=request)
    if result["should_schedule"]:
        background_tasks.add_task(bg_generate_path_task, result["task"].task_id)
    return HttpResponse.success(data=result["task"].model_dump(mode="json"))


@router.get("/tasks/active")
async def get_active_generation_task(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """读取刷新页面后仍在运行的路径规划任务。"""
    response = await CoursePathService(session).get_active_generation_task(
        user_id=current_user.id,
        module=module,
    )
    return HttpResponse.success(data=response.model_dump(mode="json") if response else None)


@router.get("/tasks/{task_id}/status")
async def get_generation_task_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """读取路径规划任务的真实持久化阶段状态。"""
    response = await CoursePathService(session).get_generation_task(
        user_id=current_user.id,
        task_id=task_id,
    )
    if response is None:
        return HttpResponse.error(code=404, message="路径规划任务不存在")
    return HttpResponse.success(data=response.model_dump(mode="json"))


@router.get("/active")
async def get_active_path(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取当前活跃的学习路径。"""
    service = CoursePathService(session)
    response = await service.get_active_path(user_id=current_user.id, module=module)
    if response is None:
        return HttpResponse.success(data=None)
    return HttpResponse.success(data=response.model_dump(mode="json"))


@router.post("/nodes/{node_id}/generate-resources")
async def generate_node_resources(
    node_id: int,
    payload: PathNodeResourceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """为路径节点生成学习资源。后端根据节点内容自动构造 learning_need。"""
    logger.info("[PathAPI] 节点资源生成: user_id=%s node_id=%s", current_user.id, node_id)
    service = CoursePathService(session)

    try:
        result = await service.generate_node_resources(
            user_id=current_user.id,
            node_id=node_id,
            selected_agents=payload.selected_agents,
            agent_configs=payload.agent_configs,
            output_options=payload.output_options,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))

    if result["should_schedule"]:
        background_tasks.add_task(
            bg_gen_task,
            user_id=current_user.id,
            request=result["request"],
            profile=result["profile"],
            resource_id=result["resource_id"],
            node_id=node_id,
        )

    return HttpResponse.success(data={
        "resource_id": result["resource_id"],
        "node_id": node_id,
        "status": result["status"],
    })


@router.post("/nodes/{node_id}/start")
async def start_node(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Start learning when a node's generated resources are ready."""
    service = CoursePathService(session)
    try:
        response = await service.start_node(user_id=current_user.id, node_id=node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=response.model_dump(mode="json"))


@router.post("/nodes/{node_id}/complete")
async def complete_node(
    node_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Complete a node, update path progress, and unlock eligible successors."""
    service = CoursePathService(session)
    try:
        response = await service.complete_node(user_id=current_user.id, node_id=node_id)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=response.model_dump(mode="json"))


@router.post("/adjust")
async def adjust_path(
    request: PathPlanFeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """根据用户反馈或当前画像，动态纠偏并重新编排后续学习节点。"""
    service = CoursePathService(session)
    try:
        updated_path = await service.adjust_path(user_id=current_user.id, request=request)
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=updated_path.model_dump(mode="json"))
