"""Shared LangGraph state types and reducers for the resource workflow."""

from __future__ import annotations

from typing import Any, Annotated, TypedDict

from app.resource.schemas import (
    AgentResult,
    ResourceGenerationRequest,
    ReviewResult,
    TeachingPlan,
)


def merge_results_dict(left: dict[str, AgentResult] | None, right: dict[str, AgentResult] | None) -> dict[str, AgentResult]:
    if left is None:
        left = {}
    if right is None:
        right = {}
    return {**left, **right}


def merge_review_results_list(left: list[ReviewResult] | None, right: list[ReviewResult] | None) -> list[ReviewResult]:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right


def merge_review_results(items: list[ReviewResult]) -> ReviewResult:
    if not items:
        return ReviewResult(passed=True, overall_score=100)

    merged = ReviewResult(passed=all(item.passed for item in items))
    merged.overall_score = min(item.overall_score for item in items)
    merged.consistency_score = min(item.consistency_score for item in items)
    merged.personalization_score = min(item.personalization_score for item in items)

    for item in items:
        merged.issues.extend(item.issues)
        merged.suggestions.extend(item.suggestions)
        for agent_id in item.failed_agents:
            if agent_id not in merged.failed_agents:
                merged.failed_agents.append(agent_id)
    return merged


class ParentState(TypedDict, total=False):
    user_id: int
    resource_id: int
    request: ResourceGenerationRequest
    profile: dict[str, Any]
    run_id: str
    emitter: Any
    teaching_plan: TeachingPlan
    results: Annotated[dict[str, AgentResult], merge_results_dict]
    review_results: Annotated[list[ReviewResult], merge_review_results_list]
    success: bool


class WorkerInputState(TypedDict):
    agent_id: str
    user_id: int
    resource_id: int
    request: ResourceGenerationRequest
    teaching_plan: TeachingPlan
    profile: dict[str, Any]
    run_id: str
    emitter: Any
