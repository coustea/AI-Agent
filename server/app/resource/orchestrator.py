"""Background orchestration entrypoint for standalone resource generation."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.events import AgentEventEmitter
from app.resource.schemas import ResourceGenerationRequest
from app.resource.workflow import build_parent_graph
from app.resource.workflow.state import ParentState

logger = get_module_logger("resource", sub="orchestrator")


async def run_multi_agent_generation(
    user_id: int,
    request: ResourceGenerationRequest,
    profile: dict[str, Any],
    resource_id: int,
) -> None:
    from app.resource.service import ResourceService

    run_id = f"resource-{resource_id}-{uuid4().hex[:8]}"
    emitter = AgentEventEmitter(resource_id=resource_id, run_id=run_id)
    start_time = time.perf_counter()
    success = False

    try:
        logger.info(
            "启动 LangGraph 全局编排图资源生成: run_id=%s user_id=%s, resource_id=%s, agents=%s",
            run_id, user_id, resource_id, request.enabled_agent_ids(),
        )

        async with session_scope() as session:
            usecases = ResourceService(session)
            await usecases.update_resource_status(resource_id, "generating")

        graph = build_parent_graph()
        initial_state = ParentState(
            user_id=user_id,
            resource_id=resource_id,
            request=request,
            profile=profile,
            run_id=run_id,
            emitter=emitter,
            results={},
            review_results=[],
        )
        final_state = await graph.ainvoke(initial_state)
        success = bool(final_state.get("success", False))

        if not success:
            logger.warning("LangGraph 未产生成功终态: resource_id=%s", resource_id)
            async with session_scope() as session:
                usecases = ResourceService(session)
                resource = await usecases.get_resource(user_id, resource_id)
                if resource is not None and resource.status == "generating":
                    await usecases.update_resource_status(resource_id, "failed")

        await emitter.emit_done(
            success=success,
            message="资源生成完成" if success else "资源生成失败",
        )
        total_elapsed = time.perf_counter() - start_time
        logger.info("资源生成结束: resource_id=%s, success=%s, 耗时=%.2fs", resource_id, success, total_elapsed)
    except Exception as exc:
        total_elapsed = time.perf_counter() - start_time
        logger.error("资源生成异常: resource_id=%s, 耗时=%.2fs", resource_id, total_elapsed, exc_info=True)
        async with session_scope() as session:
            usecases = ResourceService(session)
            await usecases.update_resource_status(resource_id, "failed")
        await emitter.emit_done(success=False, message=f"资源生成失败: {exc}")
    finally:
        ResourceService.release_write_lock(resource_id)
