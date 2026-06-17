"""Review/audit envelope construction for the resource LangGraph workflow."""

from __future__ import annotations

import json
from typing import Any

from app.resource.schemas import AgentResult, ResourceGenerationRequest, ReviewResult, TeachingPlan
from app.config import REVIEW_CONTENT_LIMIT

SOURCE_AUDIT_AGENT_IDS = ("content", "reading")
COMPLETENESS_ONLY_AGENT_IDS = ("quiz", "mindmap", "code")
PPT_AGENT_ID = "ppt"
COORDINATOR_AGENT_ID = "coordinator"
PRE_REVIEW_AGENT_ID = "pre_review"
PPT_REVIEW_AGENT_ID = "ppt_review"
VIDEO_AGENT_ID = "video"
VIDEO_REVIEW_AGENT_ID = "video_review"
BUNDLE_AGENT_ID = "bundle"


def has_generated_content(result: AgentResult | None) -> bool:
    if result is None or not result.success:
        return False
    content = result.content
    if content is None:
        return False
    if isinstance(content, str):
        return bool(content.strip())
    return True


def bounded_content(content: Any) -> str:
    if isinstance(content, str):
        text = content
    else:
        text = json.dumps(content, ensure_ascii=False)
    if len(text) <= REVIEW_CONTENT_LIMIT:
        return text
    return f"{text[:REVIEW_CONTENT_LIMIT]}\n\n[内容已截断用于审核上下文控制]"


def profile_summary(profile: dict[str, Any]) -> str:
    for key in ("profile_markdown", "summary", "profile_summary"):
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    profile_data = profile.get("profile_data")
    if isinstance(profile_data, dict):
        return json.dumps(profile_data, ensure_ascii=False)
    return ""


def build_pre_audit_envelope(
    *,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    profile: dict[str, Any],
    teaching_plan: TeachingPlan | None,
) -> tuple[dict[str, Any], list[str]]:
    selected_agents = request.enabled_agent_ids()
    checked_agents = [
        agent_id
        for agent_id in selected_agents
        if agent_id in SOURCE_AUDIT_AGENT_IDS or agent_id in COMPLETENESS_ONLY_AGENT_IDS
    ]
    missing_resources = [
        agent_id
        for agent_id in checked_agents
        if not has_generated_content(results.get(agent_id))
    ]
    deep_audit_resources = [
        {
            "agent_id": agent_id,
            "title": results[agent_id].downstream_context.title
            if results[agent_id].downstream_context else results[agent_id].title,
            "summary": results[agent_id].downstream_context.one_sentence_summary
            if results[agent_id].downstream_context else results[agent_id].summary,
            "covered_outline_ids": results[agent_id].downstream_context.covered_outline_ids
            if results[agent_id].downstream_context else [],
            "materials": [
                m.model_dump(mode="json")
                for m in (results[agent_id].downstream_context.materials or [])
            ],
        }
        for agent_id in selected_agents
        if agent_id in SOURCE_AUDIT_AGENT_IDS and has_generated_content(results.get(agent_id))
    ]
    completeness_only = [
        {
            "agent_id": agent_id,
            "title": results.get(agent_id).title if results.get(agent_id) else "",
            "summary": results.get(agent_id).summary if results.get(agent_id) else "",
            "has_content": has_generated_content(results.get(agent_id)),
        }
        for agent_id in selected_agents
        if agent_id in COMPLETENESS_ONLY_AGENT_IDS
    ]
    return {
        "mode": "pre_audit",
        "request_context": {
            "learning_need": request.learning_need,
            "learning_scenario": request.learning_scenario,
            "profile_summary": profile_summary(profile),
            "teaching_plan": teaching_plan.model_dump(mode="json") if teaching_plan else {},
        },
        "upstream_handoffs": {
            agent_id: result.downstream_context.model_dump(mode="json")
            for agent_id, result in results.items()
            if result.success and result.downstream_context is not None
        },
        "deep_audit_resources": deep_audit_resources,
        "completeness_only": completeness_only,
    }, missing_resources


def build_aggregation_audit_envelope(
    *,
    target_agent_id: str,
    audit_mode: str,
    resource_key: str,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    profile: dict[str, Any],
    teaching_plan: TeachingPlan | None,
) -> tuple[dict[str, Any], list[str]]:
    """Parameterized audit envelope for aggregation agents (PPT, Video)."""
    selected_agents = request.enabled_agent_ids()
    missing_resources: list[str] = []
    target_result = results.get(target_agent_id)
    if target_agent_id in selected_agents and not has_generated_content(target_result):
        missing_resources.append(target_agent_id)
    approved_sources = [
        {
            "agent_id": agent_id,
            "title": results[agent_id].downstream_context.title
            if results[agent_id].downstream_context else results[agent_id].title,
            "summary": results[agent_id].downstream_context.one_sentence_summary
            if results[agent_id].downstream_context else results[agent_id].summary,
            "covered_outline_ids": results[agent_id].downstream_context.covered_outline_ids
            if results[agent_id].downstream_context else [],
        }
        for agent_id in selected_agents
        if agent_id in SOURCE_AUDIT_AGENT_IDS and has_generated_content(results.get(agent_id))
    ]
    target_resource = (
        {
            "agent_id": target_agent_id,
            "title": target_result.title,
            "summary": target_result.summary,
            "audit_content": bounded_content(target_result.content),
        }
        if has_generated_content(target_result)
        else None
    )
    return {
        "mode": audit_mode,
        "request_context": {
            "learning_need": request.learning_need,
            "learning_scenario": request.learning_scenario,
            "profile_summary": profile_summary(profile),
            "teaching_plan": teaching_plan.model_dump(mode="json") if teaching_plan else {},
        },
        "upstream_handoffs": {
            agent_id: result.downstream_context.model_dump(mode="json")
            for agent_id, result in results.items()
            if result.success and result.downstream_context is not None
        },
        "approved_sources": approved_sources,
        resource_key: target_resource,
    }, missing_resources


def build_ppt_audit_envelope(
    *,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    profile: dict[str, Any],
    teaching_plan: TeachingPlan | None,
) -> tuple[dict[str, Any], list[str]]:
    return build_aggregation_audit_envelope(
        target_agent_id=PPT_AGENT_ID,
        audit_mode="ppt_audit",
        resource_key="ppt_resource",
        request=request,
        results=results,
        profile=profile,
        teaching_plan=teaching_plan,
    )


def build_video_audit_envelope(
    *,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    profile: dict[str, Any],
    teaching_plan: TeachingPlan | None,
) -> tuple[dict[str, Any], list[str]]:
    return build_aggregation_audit_envelope(
        target_agent_id=VIDEO_AGENT_ID,
        audit_mode="video_audit",
        resource_key="video_resource",
        request=request,
        results=results,
        profile=profile,
        teaching_plan=teaching_plan,
    )


def failed_review_result(
    *,
    status: str,
    message: str,
    revision_targets: list[str],
    review_mode: str,
) -> ReviewResult:
    payload = {
        "status": status,
        "checks": {
            "need_alignment": "not_checked",
            "content_completeness": "fail",
            "factuality": "not_checked",
            "hallucination": "not_checked",
            "safety": "not_checked",
            "grounding": "not_checked",
        },
        "violations": [{"type": "missing_or_failed_resource", "resources": revision_targets}],
        "revision_targets": revision_targets,
        "mode": review_mode,
    }
    return ReviewResult(
        passed=False,
        overall_score=0,
        consistency_score=0,
        personalization_score=0,
        issues=[message],
        suggestions=[json.dumps(payload, ensure_ascii=False)],
        failed_agents=revision_targets,
    )


def review_result_from_agent(result: AgentResult) -> ReviewResult:
    parsed = result.metadata.get("parsed_review")
    status = result.metadata.get("review_status") or ("pass" if result.success else "blocked")
    issues: list[str] = []
    failed_agents: list[str] = []
    if isinstance(parsed, dict):
        violations = parsed.get("violations")
        if isinstance(violations, list):
            issues = [
                item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                for item in violations
            ]
        revision_targets = parsed.get("revision_targets")
        if isinstance(revision_targets, list):
            failed_agents = [str(item) for item in revision_targets]
    if not result.success and not issues:
        issues = [result.error or f"review status: {status}"]
    return ReviewResult(
        passed=result.success,
        overall_score=100 if result.success else 0,
        consistency_score=100 if result.success else 0,
        personalization_score=100 if result.success else 0,
        issues=issues,
        suggestions=[result.content] if result.content else [],
        failed_agents=failed_agents,
    )
