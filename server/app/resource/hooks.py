"""Resource 模块多智能体执行 Harness 钩子 (app.resource.hooks)。

遵循 learn-claude-code 的 Hooks 架构思想：
“挂在循环上，不写进循环里”。
封装 SSE 实时推送与数据库状态持久化等副作用，确保智能体主循环与执行逻辑保持纯粹。
"""

from __future__ import annotations

import logging
from typing import Any

from app.infra.database import session_scope
from app.resource.event import ResourceEvents
from app.resource.schemas import (
    AgentResult,
    ExecutionPlan,
    ResourceLifecycleStatus,
    TaskNode,
)
from app.resource.service import ResourceService

logger = logging.getLogger(__name__)


class ResourceHarnessHooks:
    """资源生成 Plan-and-Execute Harness 生命周期钩子集合。"""

    def __init__(self, events: ResourceEvents) -> None:
        """初始化 Harness 钩子并绑定事件广播器。"""
        self._events = events

    async def on_plan_started(self, *, resource_id: int) -> None:
        """规划开始钩子：广播 planning 阶段开启事件。"""
        try:
            await self._events.send(
                "planning",
                "running",
                "PlanAgent 正在构建教学拓扑图...",
                10,
                data={"phase": "planning"},
            )
        except Exception as exc:
            logger.warning("on_plan_started 事件发送异常: %s", exc)

    async def on_plan_completed(
        self,
        *,
        resource_id: int,
        plan: ExecutionPlan,
        elapsed_ms: int,
    ) -> None:
        """教学大纲规划完成钩子：持久化大纲并向客户端广播事件。"""
        try:
            async with session_scope() as session:
                service = ResourceService(session)
                plan_event = await service.publish_planning_result(
                    resource_id=resource_id,
                    plan_json=plan.model_dump(mode="json"),
                    elapsed_ms=elapsed_ms,
                )
            await self._events.publish_committed(plan_event)
        except Exception as exc:
            logger.warning("on_plan_completed 钩子持久化异常: %s", exc)

    async def on_task_started(
        self,
        *,
        resource_id: int,
        task: TaskNode,
    ) -> None:
        """子任务启动钩子：广播任务开始及对应执行角色/工具信息。"""
        try:
            msg = f"{task.subagent_role} 启动任务: {task.title}"
            await self._events.send(
                task.task_id,
                "running",
                msg,
                5,
                data={
                    "phase": "started",
                    "task_type": task.task_type,
                    "tool_name": task.tool_name,
                    "subagent_role": task.subagent_role,
                },
            )
        except Exception as exc:
            logger.warning("Task[%s] on_task_started 事件发送失败: %s", task.task_id, exc)

    async def on_task_progress(
        self,
        *,
        resource_id: int,
        task: TaskNode,
        message: str,
        progress: int,
    ) -> None:
        """任务进度推进钩子：向前端广播细粒度执行与工具调用日志。"""
        try:
            await self._events.send(
                task.task_id,
                "running",
                message,
                progress,
                data={
                    "phase": "working",
                    "task_type": task.task_type,
                    "tool_name": task.tool_name,
                },
            )
        except Exception as exc:
            logger.debug("Task[%s] on_task_progress 事件忽略: %s", task.task_id, exc)

    async def on_task_completed(
        self,
        *,
        user_id: int,
        resource_id: int,
        task: TaskNode,
        result: AgentResult,
        elapsed_ms: int,
    ) -> None:
        """任务成功完成钩子：原子持久化生成产物并广播完成事件。"""
        try:
            async with session_scope() as session:
                service = ResourceService(session)
                _, completed_event = await service.publish_agent_result(
                    resource_id=resource_id,
                    user_id=user_id,
                    agent_id=task.task_id,
                    result=result,
                    elapsed_ms=elapsed_ms,
                )
            await self._events.publish_committed(completed_event)
        except Exception as exc:
            logger.error("Task[%s] on_task_completed 持久化或广播失败: %s", task.task_id, exc)

    async def on_task_failed(
        self,
        *,
        resource_id: int,
        task: TaskNode,
        error_message: str,
        elapsed_ms: int,
    ) -> None:
        """任务执行失败钩子：记录错误并上报失败状态。"""
        logger.error(
            "Task[%s] 执行失败: error=%s elapsed_ms=%d",
            task.task_id,
            error_message,
            elapsed_ms,
        )
        try:
            await self._events.send(
                task.task_id,
                "failed",
                error_message[:300],
                0,
                data={"phase": "failed", "elapsed_ms": elapsed_ms},
            )
        except Exception as exc:
            logger.warning("Task[%s] on_task_failed 事件发送失败: %s", task.task_id, exc)

    async def on_task_skipped(
        self,
        *,
        resource_id: int,
        task: TaskNode,
        reason: str,
    ) -> None:
        """任务跳过钩子（前置依赖失败时触发）。"""
        logger.warning("Task[%s] 跳过执行: %s", task.task_id, reason)
        try:
            await self._events.send(
                task.task_id,
                "failed",
                f"前置依赖未满足: {reason}",
                0,
                data={"phase": "skipped"},
            )
        except Exception as exc:
            logger.warning("Task[%s] on_task_skipped 事件发送失败: %s", task.task_id, exc)

    async def on_execution_finished(
        self,
        *,
        user_id: int,
        resource_id: int,
        expected_task_ids: set[str],
        successful_task_ids: set[str],
        failed_task_ids: set[str],
    ) -> ResourceLifecycleStatus:
        """执行终态判定钩子：更新任务总状态并广播最终完成事件。"""
        async with session_scope() as session:
            service = ResourceService(session)
            final_status = await service.finalize_generation(
                user_id=user_id,
                resource_id=resource_id,
                expected_agent_ids=expected_task_ids,
                successful_agents=successful_task_ids,
                failed_agents=failed_task_ids,
            )

        if final_status in (ResourceLifecycleStatus.COMPLETED, ResourceLifecycleStatus.PARTIAL):
            async with session_scope() as session:
                service = ResourceService(session)
                completed_event = await service.publish_generation_status(
                    resource_id=resource_id,
                    status=final_status,
                    message="资源包全部生成完成",
                )
            await self._events.publish_committed(completed_event)
        else:
            await self._events.send("global", "failed", "资源生成未产生有效成果")

        return final_status
