"""
资源生成模块 API 路由。
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.response import HttpResponse
from app.core.security import get_current_user
from app.modules.resource_generator.schemas import ResourceGenerateRequest
from app.modules.resource_generator.sse import AgentEventEmitter
from app.modules.resource_generator.coordinator_agent import CoordinatorAgent

router = APIRouter()


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
                await coordinator.run(req.user_id, task_dict)
            except Exception as e:
                await emitter.emit_agent_error("system", str(e))
                await emitter.emit_done("资源生成异常终止")

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
    from app.modules.resource_generator.coordinator_agent import AGENT_REGISTRY

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