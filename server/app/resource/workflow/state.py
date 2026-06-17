"""资源工作流的共享 LangGraph 状态类型和归约器。"""

from __future__ import annotations

from typing import Any, Annotated, TypedDict

from app.resource.schemas import (
    AgentResult,
    ResourceGenerationRequest,
    TeachingPlan,
)


def merge_results_dict(left: dict[str, AgentResult] | None, right: dict[str, AgentResult] | None) -> dict[str, AgentResult]:
    """合并两个 Agent 结果字典（LangGraph Send 并行后的归约器）。"""
    if left is None:
        left = {}
    if right is None:
        right = {}
    return {**left, **right}


class CoverageReport(TypedDict, total=False):
    """大纲覆盖报告 — 追踪哪些大纲项被覆盖、哪些缺失。"""
    covered_outline_ids: list[str]
    missing_outline_ids: list[str]
    critical_missing_ids: list[str]


class ParentState(TypedDict, total=False):
    """全局编排状态 — 供 LangGraph 全局图节点共享。"""
    user_id: int
    resource_id: int
    request: ResourceGenerationRequest
    profile: dict[str, Any]
    run_id: str
    emitter: Any
    teaching_plan: TeachingPlan
    results: Annotated[dict[str, AgentResult], merge_results_dict]
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
