"""资源工作流的共享 LangGraph 状态类型和归约器。"""

from __future__ import annotations

from typing import Any, Annotated, Literal, TypedDict

from app.resource.schemas import (
    AgentResult,
    ResourceGenerationRequest,
    TeachingPlan,
)


def merge_results_dict(left: dict[str, AgentResult] | None, right: dict[str, AgentResult] | None) -> dict[str, AgentResult]:
    """合并两个 Agent 结果字典（LangGraph Send 并行后的归约器）。

    仅包含成功持久化的 Agent 结果。失败 Agent 存储在 failures 字段中。

    Raises:
        RuntimeError: 如果同一 agent_id 在两边都存在（工作流不变量违反）。
    """
    if left is None:
        left = {}
    if right is None:
        right = {}
    overlap = set(left.keys()) & set(right.keys())
    if overlap:
        raise RuntimeError(f"workflow invariant violated: duplicate agent results for {sorted(overlap)}")
    return {**left, **right}


def merge_failures_dict(left: dict[str, "AgentFailure"] | None, right: dict[str, "AgentFailure"] | None) -> dict[str, "AgentFailure"]:
    """合并两个 Agent 失败字典（LangGraph Send 并行后的归约器）。

    Raises:
        RuntimeError: 如果同一 agent_id 在两边都存在（工作流不变量违反）。
    """
    if left is None:
        left = {}
    if right is None:
        right = {}
    overlap = set(left.keys()) & set(right.keys())
    if overlap:
        raise RuntimeError(f"workflow invariant violated: duplicate agent failures for {sorted(overlap)}")
    return {**left, **right}


class AgentFailure(TypedDict):
    """Agent 执行失败记录 — 用于追踪非致命的 Agent 失败。

    失败 Agent 不会创建 GeneratedResourceItem 记录，
    仅在工作流状态中保留失败信息以供日志和状态计算使用。

    注意：event 不在 stage 中，因为事件发布失败是 observational，
    不能使已持久化的 Agent 变为失败。
    """
    agent_id: str
    stage: Literal["generation", "validation", "persistence"]
    error_type: str
    message: str


class CoverageReport(TypedDict, total=False):
    """大纲覆盖报告 — 追踪哪些大纲项被覆盖、哪些缺失。"""
    covered_outline_ids: list[str]
    missing_outline_ids: list[str]
    critical_missing_ids: list[str]


class ParentState(TypedDict, total=False):
    """全局编排状态 — 供 LangGraph 全局图节点共享。

    results: 仅包含成功持久化的 AgentResult，key 为 agent_id。
    failures: 包含失败的 AgentFailure 记录，key 为 agent_id。
    """
    user_id: int
    resource_id: int
    request: ResourceGenerationRequest
    profile: dict[str, Any]
    run_id: str
    emitter: Any
    teaching_plan: TeachingPlan
    results: Annotated[dict[str, AgentResult], merge_results_dict]
    failures: Annotated[dict[str, AgentFailure], merge_failures_dict]
    success: bool
    coverage_report: CoverageReport


class WorkerInputState(TypedDict):
    """Worker 节点输入状态 — 每个并行 worker 的独立输入。"""
    agent_id: str
    user_id: int
    resource_id: int
    request: ResourceGenerationRequest
    teaching_plan: TeachingPlan
    profile: dict[str, Any]
    run_id: str
    emitter: Any
