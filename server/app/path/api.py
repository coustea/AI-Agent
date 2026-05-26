from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import User
from app.path.schemas import CoursePathResponse, GeneratePathRequest, PathNodeResourceRequest
from app.path.service import CoursePathService
from app.resource.schemas import AgentSelection, AgentConfigs, OutputOptions
from app.resource.service import bg_gen_task
from app.utils.response import HttpResponse

router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])


@router.post("/generate")
async def generate_path(
    request: GeneratePathRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """生成课程学习路径。路径生成仅创建节点，不自动触发资源生成。"""
    service = CoursePathService(session)
    response = await service.generate_path(user_id=current_user.id, request=request)
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
    service = CoursePathService(session)

    # Parse and validate selected_agents from payload
    selected_agents = [
        AgentSelection(**s) if isinstance(s, dict) else s
        for s in payload.selected_agents
    ]
    agent_configs = AgentConfigs() if payload.agent_configs is None else (
        AgentConfigs.model_validate(payload.agent_configs) if isinstance(payload.agent_configs, dict) else payload.agent_configs
    )
    output_options = OutputOptions() if payload.output_options is None else (
        OutputOptions.model_validate(payload.output_options) if isinstance(payload.output_options, dict) else payload.output_options
    )

    try:
        result = await service.generate_node_resources(
            user_id=current_user.id,
            node_id=node_id,
            selected_agents=selected_agents,
            agent_configs=agent_configs,
            output_options=output_options,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))

    # Dispatch background task with the prepared data
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
        "status": "generating",
    })
