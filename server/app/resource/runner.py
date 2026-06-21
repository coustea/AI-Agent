"""无重试的数据库恢复 runner。

职责：
- 进程内任务创建与原子认领
- 启动时恢复 pending 状态的 Agent（不重跑 failed/interrupted）
- 中断时保证数据库状态一致性
- 不含限流、Semaphore 或重试逻辑
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.infra.models import GeneratedResource, GeneratedResourceAgentRun
from app.resource.agents import AGENT_REGISTRY
from app.infra.agent_events import AgentEventEmitter
from app.resource.workflow.execution import execute_resource_agent, AgentOutcome
from app.resource.workflow.nodes import AGENT_TIMEOUTS, BASE_RESOURCE_AGENT_IDS, AGGREGATION_AGENT_IDS
from app.resource.schemas import ResourceInput, TeachingPlan

logger = get_module_logger("resource", sub="runner")


async def recover_pending_agents(
    *,
    resource_id: int,
    user_id: int,
    run_id: str,
    emitter: AgentEventEmitter,
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    request: Any,
) -> dict[str, AgentOutcome]:
    """恢复执行所有 pending 状态的 Agent runs。

    不重跑 failed 或 interrupted 的 Agent。
    返回每个 Agent 的执行结果。
    """
    outcomes: dict[str, AgentOutcome] = {}

    # 查询 pending 状态的 runs
    async with session_scope() as session:
        stmt = (
            select(GeneratedResourceAgentRun)
            .where(GeneratedResourceAgentRun.resource_id == resource_id)
            .where(GeneratedResourceAgentRun.status == "pending")
            .where(GeneratedResourceAgentRun.agent_id != "planning")
        )
        result = await session.exec(stmt)
        pending_runs = list(result.all())

    if not pending_runs:
        logger.info("No pending agents to recover: resource_id=%s", resource_id)
        return outcomes

    logger.info(
        "Recovering pending agents: resource_id=%s agents=%s",
        resource_id,
        [r.agent_id for r in pending_runs],
    )

    # 并行执行所有 pending agents
    tasks: list[asyncio.Task[AgentOutcome]] = []
    for run in pending_runs:
        agent_id = run.agent_id
        agent = AGENT_REGISTRY.get(agent_id)
        if agent is None:
            logger.warning("Unknown agent_id in pending run: %s", agent_id)
            continue

        timeout = AGENT_TIMEOUTS.get(agent_id, 300.0)
        resource_input = _build_recovery_input(
            resource_id=resource_id,
            agent_id=agent_id,
            teaching_plan=teaching_plan,
            profile=profile,
            request=request,
        )

        task = asyncio.create_task(
            execute_resource_agent(
                user_id=user_id,
                resource_id=resource_id,
                run_id=run_id,
                agent_id=agent_id,
                agent=agent(emitter),
                input_data=resource_input,
                emitter=emitter,
                timeout_seconds=timeout,
                source_item_ids=None,
            ),
            name=f"recover-{agent_id}",
        )
        tasks.append(task)

    # 等待所有任务完成
    for task in tasks:
        try:
            outcome = await task
            outcomes[outcome.agent_id] = outcome
        except asyncio.CancelledError:
            logger.warning("Recovery task cancelled")
        except Exception as e:
            logger.error("Recovery task failed: %s", e)

    return outcomes


def _build_recovery_input(
    *,
    resource_id: int,
    agent_id: str,
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    request: Any,
) -> ResourceInput:
    """为恢复执行构建 ResourceInput。"""
    agent_config = request.agent_configs.get(agent_id, {})
    agent_config["agent_id"] = agent_id

    return ResourceInput(
        resource_id=resource_id,
        learning_need=request.learning_need,
        learning_scenario=request.learning_scenario,
        agent_name=agent_id,
        agent_config=agent_config,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs={},  # 恢复时不传递 handoffs，聚合 Agent 应单独处理
    )


async def interrupt_running_agents(resource_id: int) -> list[str]:
    """将所有 running 状态的 Agent runs 标记为 interrupted。

    用于进程关闭时的清理。
    """
    async with session_scope() as session:
        stmt = (
            select(GeneratedResourceAgentRun)
            .where(GeneratedResourceAgentRun.resource_id == resource_id)
            .where(GeneratedResourceAgentRun.status == "running")
        )
        result = await session.exec(stmt)
        running_runs = list(result.all())

        interrupted_ids: list[str] = []
        for run in running_runs:
            run.status = "interrupted"
            run.finished_at = datetime.now(timezone.utc)
            interrupted_ids.append(run.agent_id)

        await session.commit()

    if interrupted_ids:
        logger.info(
            "Interrupted running agents: resource_id=%s agents=%s",
            resource_id,
            interrupted_ids,
        )

    return interrupted_ids


async def find_interrupted_resources(session: AsyncSession) -> list[GeneratedResource]:
    """查询所有处于 generating 状态的资源（可能被中断）。"""
    stmt = (
        select(GeneratedResource)
        .where(GeneratedResource.status == "generating")
    )
    result = await session.exec(stmt)
    return list(result.all())


__all__ = [
    "recover_pending_agents",
    "interrupt_running_agents",
    "find_interrupted_resources",
]