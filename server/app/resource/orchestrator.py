"""后台编排入口 — 独立资源生成的 LangGraph 全局编排。

负责：
1. 更新资源状态为 generating
2. 构建并执行 LangGraph 全局编排图
3. 处理成功/失败结果，发送完成事件
"""

from __future__ import annotations

import time

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.event import ResourceEvents
from app.resource.service import ResourceService
from app.resource.status import ResourceLifecycleStatus
from app.resource.workflow import build_parent_graph
from app.resource.workflow.state import ParentState

logger = get_module_logger("resource", sub="orchestrator")


async def run_multi_agent_generation(
    user_id: int,
    resource_id: int,
) -> None:
    """后台资源生成编排入口。

    只从任务创建时冻结的请求快照读取工作流输入。
    """
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    start_time = time.perf_counter()
    success = False

    try:
        # 全局状态与事件在同一事务写入；前端刷新后从该事实恢复。
        await events.send("global", "running", "资源生成已开始")
        logger.info(
            "启动 LangGraph 全局编排图资源生成: user_id=%s, resource_id=%s",
            user_id, resource_id,
        )

        # 读取创建时冻结的请求快照。
        async with session_scope() as session:
            service = ResourceService(session)
            resource = await service.get_resource(user_id, resource_id)
            if resource is None:
                raise ValueError(f"资源不存在或无权限: {resource_id}")
            snapshot = resource.request_snapshot_json
            if not snapshot:
                raise ValueError(f"资源缺少请求快照: {resource_id}")

        # 构建并编译全局编排图
        graph = build_parent_graph()
        initial_state = ParentState(
            user_id=user_id,
            resource_id=resource_id,
            selected_agents=list(snapshot["selected_agents"]),
            request_data={
                "learning_need": snapshot["learning_need"],
                "learning_scenario": snapshot["learning_scenario"],
                "agent_configs": snapshot["agent_configs"],
                "username": snapshot["username"],
            },
            profile=dict(snapshot["profile"]),
        )
        # 执行整张工作流图
        final_state = await graph.ainvoke(initial_state)
        # 读取工作流终态是否成功
        success = bool(final_state.get("success", False))

        final_status = ResourceLifecycleStatus.COMPLETED
        if not success:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "LangGraph 未产生成功终态: resource_id=%s elapsed_ms=%d",
                resource_id, elapsed_ms,
            )
            final_status = ResourceLifecycleStatus.FAILED
        else:
            async with session_scope() as session:
                service = ResourceService(session)
                resource = await service.get_resource(user_id, resource_id)
                if resource is not None:
                    final_status = ResourceLifecycleStatus(resource.status)

        # 根据成败发送全局终态事件
        if success:
            async with session_scope() as session:
                service = ResourceService(session)
                completed_event = await service.publish_generation_status(
                    resource_id=resource_id,
                    status=final_status,
                    message="资源生成完成",
                )
            await events.publish_committed(completed_event)
        else:
            await events.send("global", "failed", "资源生成未产生可用结果")
        total_elapsed = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "资源生成结束: resource_id=%s success=%s elapsed_ms=%d",
            resource_id, success, total_elapsed,
        )
    # 顶层异常兜底：标记失败并推送失败事件
    except Exception as exc:
        total_elapsed = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "资源生成异常: resource_id=%s error=%s elapsed_ms=%d",
            resource_id, exc, total_elapsed, exc_info=True,
        )
        await events.send("global", "failed", "资源生成过程中发生异常")
