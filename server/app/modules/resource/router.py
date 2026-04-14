"""
资源生成模块 API 路由。
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.dependencies import get_session
from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.core.logging import get_logger
from app.models.resource import GeneratedResource
from app.models.user import User
from app.modules.resource.schemas import ResourceGenerateRequest
from app.modules.resource.sse import AgentEventEmitter
from app.modules.resource.coordinator_agent import CoordinatorAgent

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate")
async def generate_resources(
    req: ResourceGenerateRequest,
    _user=Depends(get_current_user),
):
    """SSE 流式生成多智能体学习资源。

    前端通过 EventSource/fetch 接收 SSE 事件流。
    """

    async def event_stream():
        emitter = AgentEventEmitter()
        coordinator = CoordinatorAgent(emitter)

        task_dict = req.learning_task.model_dump()

        # 在后台运行 coordinator，同时从 emitter 流式输出
        import asyncio

        async def run_and_cleanup():
            try:
                await coordinator.run(
                    req.user_id,
                    task_dict,
                    selected_resources=req.selected_resources,
                )
            except Exception as e:
                await emitter.emit_agent_error("system", str(e))
                await emitter.emit_done("资源生成异常终止")
            finally:
                # 清理所有 Agent 的插件资源
                try:
                    from app.modules.resource.coordinator_agent import AGENT_REGISTRY
                    close_tasks = []
                    for _name, entry in AGENT_REGISTRY.items():
                        if hasattr(entry.agent, "plugin_manager"):
                            close_tasks.append(entry.agent.plugin_manager.aclose())
                    if close_tasks:
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                except Exception as cleanup_err:
                    logger.warning(f"插件资源清理异常: {cleanup_err}")

        runner = asyncio.create_task(run_and_cleanup())

        async for chunk in emitter.stream():
            yield chunk

        # 确保 coordinator 执行完毕
        await runner

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents")
async def list_agents():
    """返回所有可用的子智能体信息。"""
    from app.modules.resource.coordinator_agent import AGENT_REGISTRY

    agents = [
        {
            "id": name,
            "role": info["role"],
            "desc": info["desc"],
            "type": info["type"],
        }
        for name, info in AGENT_REGISTRY.items()
    ]
    return HttpResponse.success(data=agents)


@router.get("/resources")
async def list_resources(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取当前用户的资源生成历史列表。"""
    stmt = (
        select(GeneratedResource)
        .where(GeneratedResource.user_id == current_user.id)
        .order_by(GeneratedResource.created_at.desc())
        .limit(limit)
    )
    result = await session.exec(stmt)
    resources = result.all()

    items = [
        {
            "id": r.id,
            "course": r.course,
            "gap": r.gap,
            "need": r.need,
            "has_mindmap": r.mindmap_result is not None,
            "has_content": r.content_result is not None,
            "has_code": r.code_result is not None,
            "has_quiz": r.quiz_result is not None,
            "has_reading": r.reading_result is not None,
            "has_ppt": r.ppt_result is not None,
            "created_at": r.created_at,
        }
        for r in resources
    ]
    return HttpResponse.success(data=items)


@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取单条资源生成记录的完整内容。"""
    resource = session.get(GeneratedResource, resource_id)
    if not resource or resource.user_id != current_user.id:
        return HttpResponse.error(code=404, message="资源不存在")

    import json
    data = {
        "id": resource.id,
        "course": resource.course,
        "gap": resource.gap,
        "need": resource.need,
        "extra": resource.extra,
        "results": {},
        "created_at": resource.created_at,
    }
    for key in ("mindmap", "content", "code", "quiz", "reading", "ppt"):
        raw = getattr(resource, f"{key}_result")
        if raw:
            try:
                data["results"][key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                data["results"][key] = raw

    return HttpResponse.success(data=data)
