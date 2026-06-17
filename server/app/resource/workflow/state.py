"""Shared LangGraph state types and reducers for the resource workflow."""

from __future__ import annotations

from typing import Any, Annotated, TypedDict

from app.resource.schemas import (
    AgentResult,
    ResourceGenerationRequest,
    TeachingPlan,
)


def merge_results_dict(left: dict[str, AgentResult] | None, right: dict[str, AgentResult] | None) -> dict[str, AgentResult]:
    if left is None:
        left = {}
    if right is None:
        right = {}
    return {**left, **right}


class CoverageReport(TypedDict, total=False):
    covered_outline_ids: list[str]
    missing_outline_ids: list[str]
    critical_missing_ids: list[str]


class ParentState(TypedDict, total=False):
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
    agent_id: str
    user_id: int
    resource_id: int
    request: ResourceGenerationRequest
    teaching_plan: TeachingPlan
    profile: dict[str, Any]
    run_id: str
    emitter: Any
