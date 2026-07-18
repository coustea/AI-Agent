"""LangGraph 工作流节点函数和辅助工具。

节点拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → aggregation(PPT/Cartoon按选择并发) → save_node

核心设计：
- 传递 user_id, resource_id, selected_agents, request_data, profile, teaching_plan
- teaching_plan 是版本化结构化对象，作为下游 Agent 的唯一控制协议
- 所有数据从 LangGraph state 获取，不再从数据库读取快照
- 事件发送通过 ResourceEvents(user_id, resource_id) 创建
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from langgraph.types import Send
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.catalog import AGGREGATION_AGENT_IDS, BASE_RESOURCE_AGENT_IDS
from app.resource.service import ResourceService
from app.resource.status import SUCCESSFUL_RESOURCE_STATUSES
from app.resource.workflow.execution import execute_resource_agent
from app.resource.schemas import (
    DownstreamContext,
    ResourceInput,
    ResourcePlan,
    validate_resource_plan,
)
from app.resource.workflow.state import ParentState
from app.resource.event import ResourceEvents

logger = get_logger(__name__)

# 工作流内部协调节点，不属于用户可选的资源 Agent 目录。
COORDINATOR_AGENT_ID = "coordinator"
BUNDLE_AGENT_ID = "bundle"


def build_agent_resource_input(
    *,
    resource_id: int,
    user_id: int,
    agent_id: str,
    learning_need: str,
    learning_scenario: str,
    agent_configs: dict[str, Any],
    teaching_plan: ResourcePlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    username: str = "",
) -> ResourceInput:
    """为指定 agent 构建 ResourceInput 输入。"""
    agent_config = dict(agent_configs.get(agent_id, {}))
    agent_config["agent_id"] = agent_id
    return ResourceInput(
        resource_id=resource_id,
        user_id=user_id,
        username=username,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        agent_name=agent_id,
        agent_config=agent_config,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=upstream_handoffs,
    )


def _extract_state_data(state: ParentState) -> tuple[str, str, dict[str, Any], dict[str, Any], ResourcePlan | None, str]:
    """从 state 提取通用数据。"""
    request_data: dict[str, Any] = state.get("request_data") or {}
    profile: dict[str, Any] = state.get("profile") or {}
    teaching_plan: ResourcePlan | None = state.get("teaching_plan") or None

    learning_need = request_data.get("learning_need", "")
    learning_scenario = request_data.get("learning_scenario", "self_study")
    agent_configs = request_data.get("agent_configs", {})
    username = str(request_data.get("username", ""))

    return learning_need, learning_scenario, agent_configs, profile, teaching_plan, username


# ── Planning node ──────────────────────────────────────────────────────


async def planning_node(state: ParentState) -> dict[str, Any]:
    """规划节点 — 调用 PlanningAgent 生成结构化协同计划。

    Planning 是唯一致命节点：失败直接抛出异常，不调度任何普通 Agent。
    成功后将结构化计划写入 state。
    返回 selected_agents 供路由函数使用。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]

    selected_agents: list[str] = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, _, username = _extract_state_data(state)

    planning_input = ResourceInput(
        resource_id=resource_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        profile=profile,
        agent_config={"enabled_agents": selected_agents, "agent_configs": agent_configs},
        username=username,
    )

    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    started = time.perf_counter()
    logger.info("规划节点开始: resource_id=%s agents=%s", resource_id, selected_agents)
    try:
        await events.send(
            "planning",
            "running",
            "正在分析学习需求并构建大纲...",
            10,
            data={"phase": "planning"},
        )
        planning_result = await AGENT_REGISTRY["planning"](events).generate_resource(planning_input)
        if not planning_result.success:
            error_msg = planning_result.error or "规划阶段失败"
            raise ValueError(error_msg)

        plan_payload = planning_result.metadata.get("teaching_plan")
        if not isinstance(plan_payload, dict):
            raise ValueError("规划阶段未返回教学计划")
        plan = ResourcePlan.model_validate(plan_payload)
        validate_resource_plan(plan, expected_agent_ids=selected_agents)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "规划节点完成: resource_id=%s agents=%s plan_len=%d elapsed_ms=%d",
            resource_id, plan.agent_ids, len(plan.model_dump_json()), elapsed_ms,
        )
        async with session_scope() as session:
            service = ResourceService(session)
            completed_event = await service.publish_planning_result(
                resource_id=resource_id,
                plan_json=plan.model_dump(mode="json"),
                elapsed_ms=elapsed_ms,
            )
        await events.publish_committed(completed_event)
        # 返回 selected_agents 和 teaching_plan 到 state
        return {
            "selected_agents": selected_agents,
            "teaching_plan": plan,
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "规划节点失败: resource_id=%s error=%s elapsed_ms=%d",
            resource_id, exc, elapsed_ms,
        )
        await events.send(
            "planning",
            "failed",
            str(exc) or "规划失败",
            0,
            data={"phase": "planning", "elapsed_ms": elapsed_ms},
        )
        raise


# ── Worker nodes ───────────────────────────────────────────────────────


def route_workers_or_merge(state: ParentState) -> list[Send]:
    """路由：有 worker agent → Send 并行分发，否则跳过到 merge_workers。

    同步函数，从 state 读取 planning_node 写入的 selected_agents。
    返回 Send 列表给 LangGraph 并行执行；无 worker 时发送到 merge_workers。
    """
    selected_agents = state.get("selected_agents") or []
    worker_ids = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]
    if not worker_ids:
        # 无 worker 时直接跳到 merge_workers
        logger.debug("[ResourceNodes] 路由: 无基础worker，跳到merge resource_id=%s", state["resource_id"])
        return [Send("merge_workers", {
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
            "selected_agents": selected_agents,
            "request_data": state.get("request_data") or {},
            "profile": state.get("profile") or {},
            "teaching_plan": state.get("teaching_plan"),
        })]
    # Send 必须携带 worker_node 所需的全部数据，
    # 因为 LangGraph Send 创建独立 state，不继承父 state。
    logger.info("[ResourceNodes] 路由: 并行分发worker resource_id=%s workers=%s", state["resource_id"], worker_ids)
    return [
        Send("worker_node", {
            "agent_id": agent_id,
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
            "selected_agents": selected_agents,
            "request_data": state.get("request_data") or {},
            "profile": state.get("profile") or {},
            "teaching_plan": state.get("teaching_plan"),
        })
        for agent_id in worker_ids
    ]


async def worker_node(state: ParentState) -> dict[str, Any]:
    """Worker 节点 — 执行单个基础 agent 的资源生成并持久化结果。

    使用 ParentState，从 state["agent_id"] 读取当前 worker 的 agent_id。
    LangGraph Send 传递的状态会合并到 ParentState 中。
    """
    agent_id = state["agent_id"]
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    learning_need, learning_scenario, agent_configs, profile, teaching_plan, username = _extract_state_data(state)

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=agent_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs={},
        username=username,
    )

    try:
        return await execute_resource_agent(
            user_id=user_id,
            resource_id=resource_id,
            agent_id=agent_id,
            input_data=resource_input,
        )
    except Exception as exc:
        return await _record_node_failure(resource_id, user_id, agent_id, "generation", exc)


# ── Merge workers node ─────────────────────────────────────────────────


async def merge_workers_node(state: ParentState) -> dict[str, Any]:
    """合并 Worker 结果 — 汇总成功/失败计数，检查内容重复。"""
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    started = time.perf_counter()
    logger.info("合并节点开始: resource_id=%s", resource_id)
    await events.send(
        COORDINATOR_AGENT_ID,
        "running",
        "正在汇总并校验基础资源",
        65,
        data={"phase": "coordination"},
    )

    results = state.get("results") or {}
    failures = state.get("failures") or {}
    success_count = len(results)
    fail_count = len(failures)
    selected_agents: list[str] = state.get("selected_agents") or []
    worker_agents = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]

    coordinator_status = "failed" if worker_agents and success_count == 0 else "finished"
    message = (
        f"基础资源并行生成完成：成功 {success_count} 个，失败 {fail_count} 个"
        if worker_agents
        else "未选择基础资源，聚合资源将基于教学计划生成"
    )
    stat = "completed" if coordinator_status == "finished" else "failed"

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "合并节点完成: resource_id=%s success=%d failed=%d elapsed_ms=%d",
        resource_id, success_count, fail_count, elapsed_ms,
    )
    await events.send(
        COORDINATOR_AGENT_ID,
        stat,
        message,
        70,
        data={"phase": "coordination", "elapsed_ms": elapsed_ms},
    )
    return {}


# ── Routing after merge ────────────────────────────────────────────────


# ── Aggregation nodes (PPT, Cartoon) ──────────────────────────────────


async def _aggregation_node(state: ParentState, agent_id: str) -> dict[str, Any]:
    """聚合节点（PPT/Cartoon）— 取基础资源交接并调用对应 Agent 生成。

    两者逻辑完全一致，仅目标 agent_id 不同。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    logger.info("%s 聚合节点开始: resource_id=%s", agent_id.upper(), resource_id)

    learning_need, learning_scenario, agent_configs, profile, teaching_plan, username = _extract_state_data(state)

    base_handoffs = dict(state.get("handoffs") or {})
    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=agent_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
        username=username,
    )

    try:
        return await execute_resource_agent(
            user_id=user_id,
            resource_id=resource_id,
            agent_id=agent_id,
            input_data=resource_input,
        )
    except Exception as exc:
        return await _record_node_failure(resource_id, user_id, agent_id, "generation", exc)


async def _record_node_failure(
    resource_id: int,
    user_id: int,
    agent_id: str,
    stage: str,
    exc: Exception,
) -> dict[str, Any]:
    message = str(exc)[:300] or type(exc).__name__
    logger.error(
        "[ResourceNodes] 节点失败: resource_id=%s agent_id=%s stage=%s error=%s",
        resource_id, agent_id, stage, message,
    )
    await ResourceEvents(user_id=user_id, resource_id=resource_id).send(
        agent_id,
        "failed",
        message,
        0,
        data={"phase": stage},
    )
    return {
        "results": {},
        "failures": {agent_id: {"agent_id": agent_id, "stage": stage, "error_type": type(exc).__name__, "message": message}},
    }


async def aggregation_node(state: ParentState) -> dict[str, Any]:
    """仅并发运行本次选择的 PPT/Cartoon，不依赖固定 LangGraph barrier。"""
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    selected = [aid for aid in state.get("selected_agents", []) if aid in AGGREGATION_AGENT_IDS]
    if not selected:
        logger.debug("[ResourceNodes] 聚合节点: 无聚合Agent，跳过 resource_id=%s", resource_id)
        return {}

    logger.info("[ResourceNodes] 聚合节点开始: resource_id=%s agents=%s", resource_id, selected)

    # 聚合 Agent 以教学计划和已完成基础资源的 handoff 为输入；即使基础资源
    # 全部失败，仍会按已选集合逐个执行并各自记录真实结果。
    outputs = await asyncio.gather(
        *[_aggregation_node(state, agent_id) for agent_id in selected],
        return_exceptions=True,
    )
    merged_results: dict[str, Any] = {}
    merged_failures: dict[str, Any] = {}
    for agent_id, output in zip(selected, outputs, strict=True):
        if isinstance(output, Exception):
            output = await _record_node_failure(resource_id, user_id, agent_id, "generation", output)
        merged_results.update(output.get("results", {}))
        merged_failures.update(output.get("failures", {}))
    await events.send(
        BUNDLE_AGENT_ID,
        "running",
        "聚合资源处理完成，开始组装资源包",
        90,
        data={"phase": "aggregation_ready", "success_count": len(merged_results), "fail_count": len(merged_failures)},
    )
    logger.info(
        "[ResourceNodes] 聚合节点完成: resource_id=%s success=%d failed=%d",
        resource_id, len(merged_results), len(merged_failures),
    )
    return {"results": merged_results, "failures": merged_failures}


# ── Save node ──────────────────────────────────────────────────────────


async def save_node(state: ParentState) -> dict[str, Any]:
    """保存节点 — 从数据库计算终态并完成资源生成。"""
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)

    started = time.perf_counter()
    logger.info("保存节点开始: resource_id=%s", resource_id)
    await events.send(
        BUNDLE_AGENT_ID,
        "running",
        "正在组装资源包并保存结果",
        95,
        data={"phase": "aggregation"},
    )

    selected_agents: list[str] = state.get("selected_agents") or []
    selected_agent_ids = set(selected_agents)

    try:
        async with session_scope() as session:
            service = ResourceService(session)
            status = await service.finalize_generation(
                user_id=user_id,
                resource_id=resource_id,
                expected_agent_ids=selected_agent_ids,
            )
            success = status in SUCCESSFUL_RESOURCE_STATUSES
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "保存节点完成: resource_id=%s status=%s elapsed_ms=%d",
                resource_id, status, elapsed_ms,
            )
        await events.send(
            BUNDLE_AGENT_ID,
            "completed" if success else "failed",
            "资源包组装完成" if success else "资源包组装失败",
            100,
            data={"phase": "aggregation", "elapsed_ms": elapsed_ms},
        )
        return {"success": success}
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "保存节点失败: resource_id=%s error=%s elapsed_ms=%d",
            resource_id, exc, elapsed_ms,
        )
        await events.send(
            BUNDLE_AGENT_ID,
            "failed",
            "资源包组装异常",
            0,
            data={"phase": "aggregation", "elapsed_ms": elapsed_ms},
        )
        raise
