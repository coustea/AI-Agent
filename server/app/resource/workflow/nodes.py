"""LangGraph 工作流节点函数和辅助工具。

节点拓扑：
  START → planning → worker_node(×N, Send并行) → merge_workers
    → aggregation(PPT/Cartoon按选择并发) → save_node

核心设计：
- 传递 user_id, resource_id, selected_agents, request_data, profile, teaching_plan
- teaching_plan 是 Markdown 字符串，不再使用结构化 JSON schema
- 所有数据从 LangGraph state 获取，不再从数据库读取快照
- 事件发送通过 ResourceEvents(user_id, resource_id) 创建
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from langgraph.types import Send
from app.infra.database import session_scope
from app.infra.models import GeneratedResource as GeneratedResourceModel
from app.infra.logging import get_logger
from app.resource.agents import AGENT_REGISTRY
from app.resource.service import ResourceService
from app.resource.workflow.execution import execute_resource_agent
from app.resource.workflow.validation import check_content_overlap
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    ResourcePlan,
    validate_resource_plan,
)
from app.resource.workflow.state import ParentState
from app.resource.service import (
    AGGREGATION_AGENT_IDS,
    BASE_RESOURCE_AGENT_IDS,
    BUNDLE_AGENT_ID,
    CARTOON_AGENT_ID,
    COORDINATOR_AGENT_ID,
    PPT_AGENT_ID,
    _infer_content_format,
)
from app.resource.event import ResourceEvents

logger = get_logger(__name__)


from app.resource.workflow.extraction import extract_core_content


def build_agent_resource_input(
    *,
    resource_id: int,
    user_id: int,
    agent_id: str,
    learning_need: str,
    learning_scenario: str,
    selected_agents: list[str],
    agent_configs: dict[str, Any],
    teaching_plan: str | None,
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


async def get_handoffs(
    resource_id: int,
    user_id: int,
    agent_configs: dict[str, Any] | None = None,
) -> dict[str, DownstreamContext]:
    """从成功持久化的基础资源构建下游交接内容。

    使用 extract_core_content() 提取核心内容，替代旧的盲切片逻辑。
    """
    async with session_scope() as session:
        service = ResourceService(session)
        items = await service.list_resource_items(user_id, resource_id)

    handoffs: dict[str, DownstreamContext] = {}
    for item in items:
        if item.agent_type not in BASE_RESOURCE_AGENT_IDS:
            continue
        if item.content_text:
            content = item.content_text
        elif item.content_json is not None:
            content = json.dumps(
                item.content_json,
                ensure_ascii=False,
                indent=2,
            )
        else:
            content = ""

        if not content:
            continue

        # 提取 agent 配置（用于驱动提取行为）。资源项表只保存产物，
        # 不再保存输入快照；运行时配置从工作流 state 的 request_data 传入。
        config = dict((agent_configs or {}).get(item.agent_type, {}))

        # 使用新的提取函数
        materials = extract_core_content(
            markdown=content,
            agent_id=item.agent_type,
            config=config,
        )

        summary = " ".join(content.split())[:300] or item.title or item.agent_type
        handoffs[item.agent_type] = DownstreamContext(
            source_agent=item.agent_type,
            title=item.title or "",
            one_sentence_summary=summary,
            materials=materials,
        )
    return handoffs


def _extract_state_data(state: ParentState) -> tuple[str, str, dict[str, Any], dict[str, Any], str | None, str]:
    """从 state 提取通用数据：learning_need, learning_scenario, agent_configs, profile, teaching_plan, username。"""
    request_data: dict[str, Any] = state.get("request_data") or {}
    profile: dict[str, Any] = state.get("profile") or {}
    teaching_plan: str | None = state.get("teaching_plan") or None

    learning_need = request_data.get("learning_need", "")
    learning_scenario = request_data.get("learning_scenario", "self_study")
    agent_configs = request_data.get("agent_configs", {})
    username = str(request_data.get("username", ""))

    return learning_need, learning_scenario, agent_configs, profile, teaching_plan, username


# ── Planning node ──────────────────────────────────────────────────────


async def planning_node(state: ParentState) -> dict[str, Any]:
    """规划节点 — 调用 PlanningAgent 生成 Markdown 协同计划。

    Planning 是唯一致命节点：失败直接抛出异常，不调度任何普通 Agent。
    成功后将 Markdown 计划写入 state。
    返回 selected_agents 供路由函数使用。
    """
    user_id = state["user_id"]
    resource_id = state["resource_id"]

    selected_agents: list[str] = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, _, username = _extract_state_data(state)

    # 提取基础 Agent IDs
    enabled_base_agents = [
        agent_id
        for agent_id in selected_agents
        if agent_id in BASE_RESOURCE_AGENT_IDS
    ]

    # agent_configs 已从 _extract_state_data 提取

    planning_input = ResourceInput(
        resource_id=resource_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        profile=profile,
        agent_config={"enabled_agents": enabled_base_agents, "agent_configs": agent_configs},
        username=username,
    )

    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    started = time.perf_counter()
    logger.info("规划节点开始: resource_id=%s agents=%s", resource_id, enabled_base_agents)
    try:
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                status="running",
            )
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

        # 从 metadata 提取 Markdown 计划
        plan_markdown = planning_result.metadata.get("teaching_plan", "")
        if not plan_markdown or not isinstance(plan_markdown, str):
            raise ValueError("规划阶段未返回教学计划")

        # 使用 ResourcePlan 包装器校验
        plan = ResourcePlan(content=plan_markdown, title=planning_result.title)
        validate_resource_plan(plan, expected_agent_ids=enabled_base_agents if enabled_base_agents else None)

        assigned_agents = set(plan.agent_ids)
        expected_agents = set(enabled_base_agents)
        if assigned_agents != expected_agents:
            raise ValueError(
                "协同计划 Agent 段落与选中的基础 Agent 不匹配: "
                f"missing={sorted(expected_agents - assigned_agents)} "
                f"unexpected={sorted(assigned_agents - expected_agents)}"
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "规划节点完成: resource_id=%s agents=%s plan_len=%d elapsed_ms=%d",
            resource_id, list(assigned_agents), len(plan_markdown), elapsed_ms,
        )
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                status="completed",
                elapsed_ms=elapsed_ms,
            )
            # 将协同计划持久化到 generated_resources.plan_content
            resource = await session.get(GeneratedResourceModel, resource_id)
            if resource is not None:
                resource.plan_content = plan_markdown
        await events.send(
            "planning",
            "completed",
            "教学大纲已生成",
            100,
            data={"phase": "planning", "elapsed_ms": elapsed_ms},
        )
        # 返回 selected_agents 和 teaching_plan 到 state
        return {
            "selected_agents": selected_agents,
            "teaching_plan": plan_markdown,
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "规划节点失败: resource_id=%s error=%s elapsed_ms=%d",
            resource_id, exc, elapsed_ms,
        )
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id="planning",
                status="failed",
                error_message=str(exc)[:500],
                elapsed_ms=elapsed_ms,
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


def route_workers_or_merge(state: ParentState) -> list[Send] | list[str]:
    """路由：有 worker agent → Send 并行分发，否则直接合并。

    同步函数，从 state 读取 planning_node 写入 of selected_agents。
    """
    selected_agents = state.get("selected_agents") or []
    worker_ids = [aid for aid in selected_agents if aid in BASE_RESOURCE_AGENT_IDS]
    if not worker_ids:
        return ["merge_workers"]
    # Send 必须携带 worker_node 所需的全部数据，
    # 因为 LangGraph Send 创建独立 state，不继承父 state。
    return [
        Send("worker_node", {
            "agent_id": agent_id,
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
            "selected_agents": selected_agents,
            "request_data": state.get("request_data") or {},
            "profile": state.get("profile") or {},
            "teaching_plan": state.get("teaching_plan") or "",
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
    selected_agents = state.get("selected_agents") or []

    learning_need, learning_scenario, agent_configs, profile, teaching_plan, username = _extract_state_data(state)

    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=agent_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        selected_agents=selected_agents,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs={},
        username=username,
    )

    return await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=agent_id,
        input_data=resource_input,
    )


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

    # 内容去重检查
    teaching_plan_markdown = state.get("teaching_plan") or ""
    if results and teaching_plan_markdown:
        async with session_scope() as session:
            service = ResourceService(session)
            items = await service.list_resource_items(user_id, resource_id)

        existing_results: dict[str, AgentResult] = {}
        for item in items:
            if item.agent_type in BASE_RESOURCE_AGENT_IDS:
                content_format = _infer_content_format(item.agent_type)
                if content_format == "json" and item.content_json:
                    content = str(item.content_json)
                elif item.content_text:
                    content = item.content_text
                else:
                    content = ""

                existing_results[item.agent_type] = AgentResult(
                    success=True,
                    content=content,
                    title=item.title or "",
                    file_type=content_format,
                )

        # 检查每个成功 Agent 的内容重叠
        for agent_id in results:
            if agent_id in existing_results:
                warnings = check_content_overlap(
                    agent_id,
                    existing_results[agent_id],
                    existing_results,
                )
                for warning in warnings:
                    await events.send(agent_id, "running", f"⚠️ {warning}", 70)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "合并节点完成: resource_id=%s success=%d failed=%d elapsed_ms=%d",
        resource_id, success_count, fail_count, elapsed_ms,
    )
    async with session_scope() as session:
        service = ResourceService(session)
        await service.upsert_agent_run(
            resource_id=resource_id,
            agent_id=COORDINATOR_AGENT_ID,
            status=stat,
            error_message=message if stat == "failed" else None,
            elapsed_ms=elapsed_ms,
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

    selected_agents = state.get("selected_agents") or []
    learning_need, learning_scenario, agent_configs, profile, teaching_plan, username = _extract_state_data(state)

    base_handoffs = await get_handoffs(
        resource_id=resource_id,
        user_id=user_id,
        agent_configs=agent_configs,
    )
    resource_input = build_agent_resource_input(
        resource_id=resource_id,
        user_id=user_id,
        agent_id=agent_id,
        learning_need=learning_need,
        learning_scenario=learning_scenario,
        selected_agents=selected_agents,
        agent_configs=agent_configs,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=base_handoffs,
        username=username,
    )

    return await execute_resource_agent(
        user_id=user_id,
        resource_id=resource_id,
        agent_id=agent_id,
        input_data=resource_input,
    )


async def aggregation_node(state: ParentState) -> dict[str, Any]:
    """仅并发运行本次选择的 PPT/Cartoon，不依赖固定 LangGraph barrier。"""
    user_id = state["user_id"]
    resource_id = state["resource_id"]
    events = ResourceEvents(user_id=user_id, resource_id=resource_id)
    selected = [aid for aid in state.get("selected_agents", []) if aid in AGGREGATION_AGENT_IDS]
    if not selected:
        return {}

    # PPT/Cartoon 的专用服务可直接以教学计划作为素材，因此不能因没有基础
    # Agent 成果而跳过已选 Agent。这样“仅 PPT”“仅 Cartoon”与基础 Agent
    # 全部失败的任务仍会进入各自的真实生成链路并独立保存产物。
    outputs = await asyncio.gather(*[_aggregation_node(state, agent_id) for agent_id in selected])
    merged_results: dict[str, Any] = {}
    merged_failures: dict[str, Any] = {}
    for output in outputs:
        merged_results.update(output.get("results", {}))
        merged_failures.update(output.get("failures", {}))
    async with session_scope() as session:
        service = ResourceService(session)
        await service.upsert_agent_run(
            resource_id=resource_id,
            agent_id=BUNDLE_AGENT_ID,
            status="running",
            error_message=f"失败 {len(merged_failures)} 个" if merged_failures else None,
        )
    await events.send(
        BUNDLE_AGENT_ID,
        "running",
        "聚合资源处理完成，开始组装资源包",
        90,
        data={"phase": "aggregation_ready", "success_count": len(merged_results), "fail_count": len(merged_failures)},
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
            success = status in ("completed", "partial_completed")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "保存节点完成: resource_id=%s status=%s elapsed_ms=%d",
                resource_id, status, elapsed_ms,
            )
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=BUNDLE_AGENT_ID,
                status="completed" if success else "failed",
                error_message="资源包组装失败" if not success else None,
                elapsed_ms=elapsed_ms,
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
        async with session_scope() as session:
            service = ResourceService(session)
            await service.upsert_agent_run(
                resource_id=resource_id,
                agent_id=BUNDLE_AGENT_ID,
                status="failed",
                error_message=str(exc)[:500],
                elapsed_ms=elapsed_ms,
            )
        await events.send(
            BUNDLE_AGENT_ID,
            "failed",
            "资源包组装异常",
            0,
            data={"phase": "aggregation", "elapsed_ms": elapsed_ms},
        )
        raise
