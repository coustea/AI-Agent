"""Resource 模块 Plan-and-Execute 多智能体调度执行内核 (app.resource.harness)。

实现主脑规划与子智能体拓扑执行：
1. Plan 阶段：由 PlanAgent 基于用户高阶需求规划 DAG 任务图 (ExecutionPlan)；
2. Execute 阶段：基于就绪队列 (Ready Queue) 与信号量并发槽调度 SubAgent 执行各任务，
   多模态任务通过工具调用 (Tool) 执行，文本任务通过大模型防御性生成；
3. Hooks 机制：生命周期事件与数据库持久化完全由 ResourceHarnessHooks 承接。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.infra.database import session_scope
from app.resource.agents.planner import PlanAgent
from app.resource.agents.subagent import SubAgent
from app.resource.event import ResourceEvents
from app.resource.hooks import ResourceHarnessHooks
from app.resource.schemas import (
    AgentResult,
    ExecutionPlan,
    ResourceGenerationRequest,
    ResourceLifecycleStatus,
    TaskNode,
    TaskStatus,
)
from app.resource.service import ResourceService
from app.resource.tools import build_resource_toolbox

logger = logging.getLogger(__name__)


class ResourceHarness:
    """Plan-and-Execute 多智能体运行时 Harness 调度器。"""

    def __init__(
        self,
        events: ResourceEvents,
        hooks: ResourceHarnessHooks | None = None,
        max_concurrency: int = 3,
    ) -> None:
        """初始化调度内核，配置事件广播器、钩子与并发信号量。"""
        self.events = events
        self.hooks = hooks or ResourceHarnessHooks(events)
        self.planner = PlanAgent()
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def execute(
        self,
        request: ResourceGenerationRequest,
        *,
        user_id: int,
        resource_id: int,
        username: str = "anonymous",
    ) -> ResourceLifecycleStatus:
        """执行完整的 Plan-and-Execute 资源生成流程。"""
        logger.info(
            "ResourceHarness 启动: user_id=%d resource_id=%d topic=%s targets=%s",
            user_id,
            resource_id,
            request.topic,
            request.target_resources,
        )

        # ── 阶段 1: Plan 主脑规划 ──────────────────────────────────────────
        await self.hooks.on_plan_started(resource_id=resource_id)
        plan_start_time = time.perf_counter()

        async def plan_progress(msg: str, pct: int) -> None:
            """广播规划阶段细粒度进度。"""
            await self.events.send("planning", "running", msg, pct, data={"phase": "planning"})

        plan: ExecutionPlan = await self.planner.plan(
            topic=request.topic,
            learning_goal=request.learning_goal,
            target_resources=request.target_resources,
            difficulty=request.difficulty,
            preferences=request.preferences,
            progress_callback=plan_progress,
        )
        plan_elapsed_ms = int((time.perf_counter() - plan_start_time) * 1000)
        await self.hooks.on_plan_completed(
            resource_id=resource_id,
            plan=plan,
            elapsed_ms=plan_elapsed_ms,
        )

        # ── 阶段 2: 构建多模态工具箱 ───────────────────────────────────────
        toolbox = build_resource_toolbox(
            username=username,
            resource_id=str(resource_id),
        )

        # ── 阶段 3: Execute 子智能体拓扑执行 ───────────────────────────────
        expected_task_ids = {task.task_id for task in plan.tasks}
        completed_task_ids: set[str] = set()
        failed_task_ids: set[str] = set()
        running_task_ids: set[str] = set()
        task_results: dict[str, AgentResult] = {}

        active_tasks: dict[str, asyncio.Task[AgentResult]] = {}

        async def _run_single_task(task_node: TaskNode) -> AgentResult:
            """受信号量保护的单个 SubAgent 任务执行逻辑。"""
            async with self.semaphore:
                task_start_time = time.perf_counter()
                task_node.status = TaskStatus.RUNNING
                await self.hooks.on_task_started(resource_id=resource_id, task=task_node)

                # 收集上游依赖产物
                upstream_results: dict[str, AgentResult] = {
                    dep: task_results[dep]
                    for dep in task_node.dependencies
                    if dep in task_results
                }

                async def task_progress(msg: str, pct: int) -> None:
                    task_node.message = msg
                    task_node.progress = pct
                    await self.hooks.on_task_progress(
                        resource_id=resource_id,
                        task=task_node,
                        message=msg,
                        progress=pct,
                    )

                subagent = SubAgent(role=task_node.subagent_role)
                result = await subagent.execute_task(
                    task=task_node,
                    topic=request.topic,
                    learning_goal=request.learning_goal,
                    difficulty=request.difficulty,
                    upstream_results=upstream_results,
                    preferences=request.preferences,
                    toolbox=toolbox,
                    progress_callback=task_progress,
                )

                elapsed_ms = int((time.perf_counter() - task_start_time) * 1000)
                task_node.elapsed_ms = elapsed_ms

                if result.success:
                    task_node.status = TaskStatus.COMPLETED
                    task_node.progress = 100
                    task_node.message = result.summary or "生成完成"
                    await self.hooks.on_task_completed(
                        user_id=user_id,
                        resource_id=resource_id,
                        task=task_node,
                        result=result,
                        elapsed_ms=elapsed_ms,
                    )
                else:
                    task_node.status = TaskStatus.FAILED
                    task_node.error = result.error
                    task_node.message = result.error or "生成失败"
                    await self.hooks.on_task_failed(
                        resource_id=resource_id,
                        task=task_node,
                        error_message=result.error or "执行异常",
                        elapsed_ms=elapsed_ms,
                    )

                return result

        # 调度主循环
        while len(completed_task_ids | failed_task_ids) < len(plan.tasks):
            # 1. 查找就绪任务
            ready = plan.ready_tasks(completed_task_ids, running_task_ids)

            # 2. 检查是否有因上游失败而无法执行的任务，标记为跳过
            unmet_tasks: list[TaskNode] = []
            for t in plan.tasks:
                if t.task_id in completed_task_ids or t.task_id in failed_task_ids or t.task_id in running_task_ids:
                    continue
                if any(dep in failed_task_ids for dep in t.dependencies):
                    unmet_tasks.append(t)

            for skipped_task in unmet_tasks:
                skipped_task.status = TaskStatus.SKIPPED
                failed_task_ids.add(skipped_task.task_id)
                await self.hooks.on_task_skipped(
                    resource_id=resource_id,
                    task=skipped_task,
                    reason=f"上游依赖任务失败: {skipped_task.dependencies}",
                )

            # 3. 启动所有就绪任务
            for ready_task in ready:
                tid = ready_task.task_id
                running_task_ids.add(tid)
                active_tasks[tid] = asyncio.create_task(
                    _run_single_task(ready_task),
                    name=f"task-{tid}",
                )

            if not active_tasks:
                break

            # 4. 等待至少一个正在执行的任务完成
            done, _ = await asyncio.wait(
                active_tasks.values(),
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 处理已完成的任务
            for finished_task in done:
                finished_tid: str | None = None
                for tid, fut in list(active_tasks.items()):
                    if fut is finished_task:
                        finished_tid = tid
                        del active_tasks[tid]
                        break

                if finished_tid is None:
                    continue

                running_task_ids.discard(finished_tid)
                try:
                    res: AgentResult = finished_task.result()
                    task_results[finished_tid] = res
                    if res.success:
                        completed_task_ids.add(finished_tid)
                    else:
                        failed_task_ids.add(finished_tid)
                except Exception as exc:
                    logger.exception("任务 %s 异常退出: %s", finished_tid, exc)
                    failed_task_ids.add(finished_tid)
                    node = plan.get_task(finished_tid)
                    if node:
                        node.status = TaskStatus.FAILED
                        node.error = str(exc)
                        await self.hooks.on_task_failed(
                            resource_id=resource_id,
                            task=node,
                            error_message=str(exc),
                            elapsed_ms=0,
                        )

        # ── 阶段 4: 终态判定与汇总 ─────────────────────────────────────────
        final_status = await self.hooks.on_execution_finished(
            user_id=user_id,
            resource_id=resource_id,
            expected_task_ids=expected_task_ids,
            successful_task_ids=completed_task_ids,
            failed_task_ids=failed_task_ids,
        )

        logger.info(
            "ResourceHarness 执行结束: status=%s completed=%s failed=%s",
            final_status,
            completed_task_ids,
            failed_task_ids,
        )
        return final_status


async def run_multi_agent_generation(user_id: int, resource_id: int) -> None:
    """在后台独立运行完整的 Plan-and-Execute 资源生成流程。"""
    async with session_scope() as session:
        service = ResourceService(session)
        resource = await service.get_resource(user_id, resource_id)
        if resource is None:
            logger.error("后台生成任务无法找到目标资源: resource_id=%d", resource_id)
            return
        snapshot = resource.request_snapshot_json or {}
        username = snapshot.get("username", "anonymous")
        request = ResourceGenerationRequest.model_validate(snapshot)

    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    harness = ResourceHarness(events)
    try:
        await harness.execute(
            request,
            user_id=user_id,
            resource_id=resource_id,
            username=username,
        )
    except Exception as exc:
        logger.exception("后台生成任务执行异常: resource_id=%d error=%s", resource_id, exc)
        await events.send("global", "failed", f"任务异常终止: {exc}")


__all__ = ["ResourceHarness", "run_multi_agent_generation"]
