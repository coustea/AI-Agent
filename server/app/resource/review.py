"""Resource review context builders.

This module keeps review/audit payload construction out of the persistence
service so workflow orchestration can depend on a small, testable interface.
"""

from __future__ import annotations

import json
from typing import Any

from app.resource.schemas import AgentResult, ResourceGenerationRequest, ReviewResult

SOURCE_AUDIT_AGENT_IDS = ("content", "reading")
COMPLETENESS_ONLY_AGENT_IDS = ("quiz", "mindmap", "code")
PPT_AGENT_ID = "ppt"
COORDINATOR_AGENT_ID = "coordinator"
PRE_REVIEW_AGENT_ID = "pre_review"
PPT_REVIEW_AGENT_ID = "ppt_review"
VIDEO_AGENT_ID = "video"
VIDEO_REVIEW_AGENT_ID = "video_review"
BUNDLE_AGENT_ID = "bundle"
REVIEW_CONTENT_LIMIT = 12_000


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
    blueprint: Any | None,
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
            "title": results[agent_id].title,
            "summary": results[agent_id].summary,
            "audit_content": bounded_content(results[agent_id].content),
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
            "blueprint": blueprint.model_dump(mode="json") if blueprint else {},
        },
        "deep_audit_resources": deep_audit_resources,
        "completeness_only": completeness_only,
    }, missing_resources


def build_ppt_audit_envelope(
    *,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    profile: dict[str, Any],
    blueprint: Any | None,
) -> tuple[dict[str, Any], list[str]]:
    selected_agents = request.enabled_agent_ids()
    missing_resources: list[str] = []
    ppt_result = results.get(PPT_AGENT_ID)
    if PPT_AGENT_ID in selected_agents and not has_generated_content(ppt_result):
        missing_resources.append(PPT_AGENT_ID)
    approved_sources = [
        {
            "agent_id": agent_id,
            "title": results[agent_id].title,
            "summary": results[agent_id].summary,
            "source_content": bounded_content(results[agent_id].content),
        }
        for agent_id in selected_agents
        if agent_id in SOURCE_AUDIT_AGENT_IDS and has_generated_content(results.get(agent_id))
    ]
    ppt_resource = (
        {
            "agent_id": PPT_AGENT_ID,
            "title": ppt_result.title,
            "summary": ppt_result.summary,
            "audit_content": bounded_content(ppt_result.content),
        }
        if has_generated_content(ppt_result)
        else None
    )
    return {
        "mode": "ppt_audit",
        "request_context": {
            "learning_need": request.learning_need,
            "learning_scenario": request.learning_scenario,
            "profile_summary": profile_summary(profile),
            "blueprint": blueprint.model_dump(mode="json") if blueprint else {},
        },
        "approved_sources": approved_sources,
        "ppt_resource": ppt_resource,
    }, missing_resources


def build_video_audit_envelope(
    *,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    profile: dict[str, Any],
    blueprint: Any | None,
) -> tuple[dict[str, Any], list[str]]:
    selected_agents = request.enabled_agent_ids()
    missing_resources: list[str] = []
    video_result = results.get(VIDEO_AGENT_ID)
    if VIDEO_AGENT_ID in selected_agents and not has_generated_content(video_result):
        missing_resources.append(VIDEO_AGENT_ID)
    approved_sources = [
        {
            "agent_id": agent_id,
            "title": results[agent_id].title,
            "summary": results[agent_id].summary,
            "source_content": bounded_content(results[agent_id].content),
        }
        for agent_id in selected_agents
        if agent_id in SOURCE_AUDIT_AGENT_IDS and has_generated_content(results.get(agent_id))
    ]
    video_resource = (
        {
            "agent_id": VIDEO_AGENT_ID,
            "title": video_result.title,
            "summary": video_result.summary,
            "audit_content": bounded_content(video_result.content),
        }
        if has_generated_content(video_result)
        else None
    )
    return {
        "mode": "video_audit",
        "request_context": {
            "learning_need": request.learning_need,
            "learning_scenario": request.learning_scenario,
            "profile_summary": profile_summary(profile),
            "blueprint": blueprint.model_dump(mode="json") if blueprint else {},
        },
        "approved_sources": approved_sources,
        "video_resource": video_resource,
    }, missing_resources


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
    """从 AgentResult 构造 ReviewResult。"""
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
