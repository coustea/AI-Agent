"""多智能体资源生成编排器 (app.resource.orchestrator) —— 线性阶段 + 并行 Worker 执行。

执行拓扑：
  1. Planning 阶段：调用 ``PlanningAgent`` 产出版本化 ``ResourcePlan``
  2. Base 阶段：并发运行已选基础 Agent（``content``, ``mindmap``, ``quiz``, ``code``, ``reading``），提取 ``DownstreamContext`` 交接素材
  3. Aggregation 阶段：并发运行已选聚合 Agent（``ppt``, ``cartoon``），消费上游 ``handoffs``
  4. Finalize 阶段：从数据库事实计算终态并推送完成事件
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.infra.database import session_scope
from app.infra.logging import get_module_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.catalog import (
    AGENT_BY_ID,
    AGGREGATION_AGENT_IDS,
    BASE_RESOURCE_AGENT_IDS,
)
from app.resource.event import ResourceEvents
from app.resource.schemas import (
    DownstreamContext,
    ResourceInput,
    ResourcePlan,
    SUCCESSFUL_RESOURCE_STATUSES,
    validate_resource_plan,
)
from app.resource.service import ResourceService
from app.resource.validator import extract_core_content, validate_agent_result

logger = get_module_logger("resource", sub="orchestrator")

RESOURCE_GENERATION_CONCURRENCY = 3
_generation_slots = asyncio.Semaphore(RESOURCE_GENERATION_CONCURRENCY)

COORDINATOR_AGENT_ID = "coordinator"
BUNDLE_AGENT_ID = "bundle"


async def _observe(agent_id: str, coro: Any) -> None:
    """Best-effort 发送观察事件，异常不中断主流程。"""
    try:
        await coro
    except Exception as exc:
        logger.warning("Agent[%s] 事件发送失败: %s", agent_id, exc)


async def _record_agent_failure(
    *,
    agent_id: str,
    stage: str,
    exc: BaseException,
    started_at: float,
    events: ResourceEvents,
) -> None:
    """记录 Agent 执行失败日志并向事件通道上报失败状态。"""
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    error_message = str(exc)[:300] or type(exc).__name__
    logger.error(
        "Agent[%s] 执行失败: stage=%s error_type=%s error=%s elapsed_ms=%d",
        agent_id,
        stage,
        type(exc).__name__,
        error_message,
        elapsed_ms,
    )
    await _observe(
        agent_id,
        events.send(
            agent_id,
            "failed",
            error_message,
            0,
            data={"phase": stage, "elapsed_ms": elapsed_ms},
        ),
    )


async def _execute_single_agent(
    *,
    user_id: int,
    resource_id: int,
    agent_id: str,
    input_data: ResourceInput,
    events: ResourceEvents,
) -> tuple[bool, DownstreamContext | None]:
    """执行单个资源 Agent 的完整生命周期（信号量限流、超时、确定性校验、事务持久化与交接提取）。"""
    started = time.perf_counter()
    agent = AGENT_REGISTRY[agent_id](events)
    descriptor = AGENT_BY_ID[agent_id]

    try:
        await events.send(
            agent_id,
            "running",
            descriptor.start_message,
            0,
            data={"phase": "generation_started"},
        )
    except Exception as exc:
        await _record_agent_failure(
            agent_id=agent_id,
            stage="persistence",
            exc=exc,
            started_at=started,
            events=events,
        )
        return False, None

    try:
        async with _generation_slots:
            async with asyncio.timeout(descriptor.timeout_seconds):
                result = await agent.generate_resource(input_data)
    except TimeoutError as exc:
        await _record_agent_failure(
            agent_id=agent_id,
            stage="timeout",
            exc=exc,
            started_at=started,
            events=events,
        )
        return False, None
    except Exception as exc:
        await _record_agent_failure(
            agent_id=agent_id,
            stage="generation",
            exc=exc,
            started_at=started,
            events=events,
        )
        return False, None

    if result.success is not True:
        stage = str(result.metadata.get("generation_stage") or "generation")
        await _record_agent_failure(
            agent_id=agent_id,
            stage=stage,
            exc=RuntimeError(result.error or "Agent returned success=False"),
            started_at=started,
            events=events,
        )
        return False, None

    await _observe(
        agent_id,
        events.send(
            agent_id,
            "running",
            "正在校验资源结构与内容完整性...",
            88,
            data={"phase": "validation"},
        ),
    )
    try:
        validate_agent_result(agent_id, result, input_data)
    except Exception as exc:
        await _record_agent_failure(
            agent_id=agent_id,
            stage="validation",
            exc=exc,
            started_at=started,
            events=events,
        )
        return False, None

    await _observe(
        agent_id,
        events.send(
            agent_id,
            "running",
            "正在保存资源成果...",
            94,
            data={"phase": "persistence"},
        ),
    )
    try:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        async with session_scope() as session:
            service = ResourceService(session)
            _, completed_event = await service.publish_agent_result(
                resource_id=resource_id,
                user_id=user_id,
                agent_id=agent_id,
                result=result,
                elapsed_ms=elapsed_ms,
            )
    except Exception as exc:
        await _record_agent_failure(
            agent_id=agent_id,
            stage="persistence",
            exc=exc,
            started_at=started,
            events=events,
        )
        return False, None

    await _observe(agent_id, events.publish_committed(completed_event))

    handoff: DownstreamContext | None = None
    if agent_id in BASE_RESOURCE_AGENT_IDS:
        raw_text = (
            result.content
            if isinstance(result.content, str)
            else json.dumps(result.content, ensure_ascii=False)
        )
        materials = extract_core_content(
            markdown=raw_text,
            agent_id=agent_id,
            config={k: v for k, v in input_data.agent_config.items() if k != "agent_id"},
        )
        handoff = DownstreamContext(
            source_agent=agent_id,
            title=result.title,
            one_sentence_summary=" ".join(raw_text.split())[:300],
            materials=materials,
        )
    return True, handoff


def _build_agent_input(
    *,
    resource_id: int,
    user_id: int,
    username: str,
    agent_id: str,
    learning_need: str,
    learning_scenario: str,
    agent_configs: dict[str, Any],
    teaching_plan: ResourcePlan,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
) -> ResourceInput:
    """装配传递给单个 Agent 的 ResourceInput 上下文。"""
    cfg = dict(agent_configs.get(agent_id, {}))
    cfg["agent_id"] = agent_id
    return ResourceInput(
        resource_id=resource_id,
        user_id=user_id,
        username=username,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        agent_name=agent_id,
        agent_config=cfg,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=upstream_handoffs,
    )


async def run_multi_agent_generation(
    user_id: int,
    resource_id: int,
) -> None:
    """后台多智能体资源生成编排入口。"""
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    start_time = time.perf_counter()

    try:
        await events.send("global", "running", "资源生成已开始")
        logger.info("启动资源生成编排: user_id=%s resource_id=%s", user_id, resource_id)

        async with session_scope() as session:
            service = ResourceService(session)
            resource = await service.get_resource(user_id, resource_id)
            if resource is None:
                raise ValueError(f"资源不存在或无权限: {resource_id}")
            snapshot = resource.request_snapshot_json
            if not snapshot:
                raise ValueError(f"资源缺少请求快照: {resource_id}")

        selected_agents: list[str] = list(snapshot["selected_agents"])
        learning_need: str = str(snapshot["learning_need"])
        learning_scenario: str = str(snapshot.get("learning_scenario") or "self_study")
        agent_configs: dict[str, Any] = dict(snapshot.get("agent_configs") or {})
        username: str = str(snapshot.get("username") or "")
        profile: dict[str, Any] = dict(snapshot.get("profile") or {})

        # ── 1. Planning 阶段 ──
        plan_started = time.perf_counter()
        await events.send(
            "planning",
            "running",
            "正在分析学习需求并构建大纲...",
            10,
            data={"phase": "planning"},
        )
        planning_input = ResourceInput(
            resource_id=resource_id,
            user_id=user_id,
            username=username,
            learning_need=learning_need,
            learning_scenario=learning_scenario,
            profile=profile,
            agent_config={"enabled_agents": selected_agents, "agent_configs": agent_configs},
        )
        try:
            planning_result = await AGENT_REGISTRY["planning"](events).generate_resource(planning_input)
            if not planning_result.success:
                raise ValueError(planning_result.error or "规划阶段失败")
            plan_payload = planning_result.metadata.get("teaching_plan")
            if not isinstance(plan_payload, dict):
                raise ValueError("规划阶段未返回教学计划")
            teaching_plan = ResourcePlan.model_validate(plan_payload)
            validate_resource_plan(teaching_plan, expected_agent_ids=selected_agents)
            plan_elapsed = int((time.perf_counter() - plan_started) * 1000)
            async with session_scope() as session:
                service = ResourceService(session)
                plan_event = await service.publish_planning_result(
                    resource_id=resource_id,
                    plan_json=teaching_plan.model_dump(mode="json"),
                    elapsed_ms=plan_elapsed,
                )
            await events.publish_committed(plan_event)
        except Exception as exc:
            plan_elapsed = int((time.perf_counter() - plan_started) * 1000)
            await events.send(
                "planning",
                "failed",
                str(exc) or "规划失败",
                0,
                data={"phase": "planning", "elapsed_ms": plan_elapsed},
            )
            raise

        # ── 2. Base Agents 并行生成阶段 ──
        base_agent_ids = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]
        handoffs: dict[str, DownstreamContext] = {}
        base_success_count = 0

        if base_agent_ids:
            base_outcomes = await asyncio.gather(
                *(
                    _execute_single_agent(
                        user_id=user_id,
                        resource_id=resource_id,
                        agent_id=aid,
                        input_data=_build_agent_input(
                            resource_id=resource_id,
                            user_id=user_id,
                            username=username,
                            agent_id=aid,
                            learning_need=learning_need,
                            learning_scenario=learning_scenario,
                            agent_configs=agent_configs,
                            teaching_plan=teaching_plan,
                            profile=profile,
                            upstream_handoffs={},
                        ),
                        events=events,
                    )
                    for aid in base_agent_ids
                )
            )
            for aid, (ok, handoff) in zip(base_agent_ids, base_outcomes, strict=True):
                if ok:
                    base_success_count += 1
                if handoff is not None:
                    handoffs[aid] = handoff

        base_fail_count = len(base_agent_ids) - base_success_count
        await events.send(
            COORDINATOR_AGENT_ID,
            "failed" if base_agent_ids and base_success_count == 0 else "completed",
            f"基础资源并行生成完成：成功 {base_success_count} 个，失败 {base_fail_count} 个",
            70,
            data={"phase": "coordination"},
        )

        # ── 3. Aggregation Agents (PPT / Cartoon) 并行生成阶段 ──
        agg_agent_ids = [aid for aid in selected_agents if aid in AGGREGATION_AGENT_IDS]
        if agg_agent_ids:
            await asyncio.gather(
                *(
                    _execute_single_agent(
                        user_id=user_id,
                        resource_id=resource_id,
                        agent_id=aid,
                        input_data=_build_agent_input(
                            resource_id=resource_id,
                            user_id=user_id,
                            username=username,
                            agent_id=aid,
                            learning_need=learning_need,
                            learning_scenario=learning_scenario,
                            agent_configs=agent_configs,
                            teaching_plan=teaching_plan,
                            profile=profile,
                            upstream_handoffs=handoffs,
                        ),
                        events=events,
                    )
                    for aid in agg_agent_ids
                )
            )

        # ── 4. Finalize 终态计算与广播 ──
        await events.send(
            BUNDLE_AGENT_ID,
            "running",
            "正在组装资源包并保存结果",
            95,
            data={"phase": "aggregation"},
        )
        async with session_scope() as session:
            service = ResourceService(session)
            final_status = await service.finalize_generation(
                user_id=user_id,
                resource_id=resource_id,
                expected_agent_ids=set(selected_agents),
            )
        success = final_status in SUCCESSFUL_RESOURCE_STATUSES
        await events.send(
            BUNDLE_AGENT_ID,
            "completed" if success else "failed",
            "资源包组装完成" if success else "资源包组装失败",
            100,
            data={"phase": "aggregation"},
        )

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
            "资源生成结束: resource_id=%s status=%s elapsed_ms=%d",
            resource_id,
            final_status.value,
            total_elapsed,
        )
    except Exception as exc:
        total_elapsed = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "资源生成异常: resource_id=%s error=%s elapsed_ms=%d",
            resource_id,
            exc,
            total_elapsed,
            exc_info=True,
        )
        await events.send("global", "failed", "资源生成过程中发生异常")


__all__ = ["run_multi_agent_generation"]
