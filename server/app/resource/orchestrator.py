"""后台编排入口 — 独立资源生成的 LangGraph 全局编排。

负责：
1. 更新资源状态为 generating
2. 构建并执行 LangGraph 全局编排图
3. 处理成功/失败结果，发送完成事件
"""

from __future__ import annotations

import time
from typing import Any

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.event import ResourceEvents
from app.resource.service import ResourceService
from app.resource.workflow import build_parent_graph
from app.resource.workflow.state import ParentState

logger = get_module_logger("resource", sub="orchestrator")


async def run_multi_agent_generation(
    user_id: int,
    resource_id: int,
    *,
    selected_agents: list[str] | None = None,
    request_data: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> None:
    """后台资源生成编排入口。

    通过参数传入 selected_agents, request_data, profile，
    不再从数据库读取快照列。
    """
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    start_time = time.perf_counter()
    success = False

    try:
        await events.send("global", "running", "资源生成已开始")
        logger.info(
            "启动 LangGraph 全局编排图资源生成: user_id=%s, resource_id=%s",
            user_id, resource_id,
        )

        async with session_scope() as session:
            service = ResourceService(session)
            await service.update_resource_status(resource_id, "generating")

        graph = build_parent_graph()
        initial_state = ParentState(
            user_id=user_id,
            resource_id=resource_id,
            selected_agents=selected_agents or [],
            request_data=request_data or {},
            profile=profile or {},
        )
        final_state = await graph.ainvoke(initial_state)
        success = bool(final_state.get("success", False))

        if not success:
            logger.warning("LangGraph 未产生成功终态: resource_id=%s", resource_id)
            async with session_scope() as session:
                service = ResourceService(session)
                resource = await service.get_resource(user_id, resource_id)
                if resource is not None and resource.status == "generating":
                    await service.update_resource_status(
                        resource_id,
                        "failed",
                        error_message="工作流未产生成功终态",
                    )

        if success:
            await events.send("global", "completed", "资源生成完成")
        else:
            await events.send("global", "failed", "资源生成未产生可用结果")
        total_elapsed = time.perf_counter() - start_time
        logger.info("资源生成结束: resource_id=%s, success=%s, 耗时=%.2fs", resource_id, success, total_elapsed)
    except Exception as exc:
        total_elapsed = time.perf_counter() - start_time
        logger.error("资源生成异常: resource_id=%s, 耗时=%.2fs", resource_id, total_elapsed, exc_info=True)
        async with session_scope() as session:
            service = ResourceService(session)
            await service.update_resource_status(
                resource_id,
                "failed",
                error_message=str(exc) or type(exc).__name__,
            )
        await events.send("global", "failed", "资源生成过程中发生异常")
