"""Common logic for aggregation-stage nodes (PPT, Video) in the resource workflow.

Both ppt_node and video_node follow the same pattern:
  emit(running) → collect handoffs → build input → run agent → persist →
  run review → emit results

This module extracts that pattern into a single parameterized function.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.resource.agents import AGENT_REGISTRY
from app.resource.events import AgentRunTracker
from app.resource.schemas import AgentResult, ResourceInput
from app.resource.workflow.audit import (
    failed_review_result,
    review_result_from_agent,
)
from app.resource.workflow.nodes import (
    build_agent_resource_input,
    collect_successful_handoffs,
    load_results_for_review,
    persist_result_and_emit_artifact,
)
from app.resource.workflow.state import ParentState

logger = logging.getLogger(__name__)


async def run_aggregation_node(
    state: ParentState,
    *,
    agent_id: str,
    review_agent_id: str,
    running_message: str,
    generating_message: str,
    review_running_message: str,
    review_skipped_message: str,
    build_audit_envelope: Callable[..., tuple[dict[str, Any], list[str]]],
    extra_input_builder: Callable[[ResourceInput], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Run an aggregation agent (PPT/Video) with its review cycle.

    Args:
        extra_input_builder: Optional callback that receives the base ResourceInput
            and returns extra agent_config fields (e.g. material_bundle for PPT).
    """
    emitter = state["emitter"]
    await emitter.emit_agent(
        agent_id,
        status="running",
        message=running_message,
        progress=80,
        phase=f"{agent_id}_generating",
    )

    base_handoffs = collect_successful_handoffs(state["results"], teaching_plan=state.get("teaching_plan"))

    agent_config_extra: dict[str, Any] = {"upstream_handoff_agent_ids": list(base_handoffs.keys())}
    if extra_input_builder:
        extra = extra_input_builder(ResourceInput(
            resource_id=state["resource_id"],
            learning_need=state["request"].learning_need,
            learning_scenario=state["request"].learning_scenario,
            agent_name=agent_id,
            agent_config=state["request"].agent_configs.get(agent_id, {}),
            teaching_plan=state["teaching_plan"],
            profile=state["profile"],
            upstream_handoffs=base_handoffs,
        ))
        if extra:
            agent_config_extra.update(extra)

    agent_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=agent_config_extra,
    )

    agent = AGENT_REGISTRY[agent_id](emitter)
    async with AgentRunTracker(
        emitter=emitter,
        agent_id=agent_id,
        phase="llm_generating",
        message=generating_message,
        progress=80,
    ) as tracker:
        result = await agent.generate_resource(agent_input)
        await tracker.finish(
            result.summary if result.success else (result.error or f"{agent_id} 生成失败"),
            success=result.success,
            metrics=result.metrics,
        )

    if result.success and result.content:
        await persist_result_and_emit_artifact(
            user_id=state["user_id"],
            resource_id=state["resource_id"],
            result=result,
            emitter=emitter,
            depends_on_agents=list(base_handoffs.keys()),
        )

    # ── Review cycle ──────────────────────────────────────────────────────
    await emitter.emit_agent(review_agent_id, status="running", message=review_running_message, progress=90)
    review_result = None

    if not result or not result.success:
        await emitter.emit_agent(
            review_agent_id,
            status="skipped",
            message=review_skipped_message,
            progress=95,
        )
    else:
        failed_results = {aid: r for aid, r in {**state["results"], agent_id: result}.items() if not r.success}
        review_results = await load_results_for_review(
            user_id=state["user_id"],
            resource_id=state["resource_id"],
            failures=failed_results,
        )
        audit_envelope, missing_resources = build_audit_envelope(
            request=state["request"],
            results=review_results,
            profile=state["profile"],
            teaching_plan=state["teaching_plan"],
        )
        if missing_resources:
            review_result = failed_review_result(
                status="needs_revision",
                message=f"{agent_id} 审核发现缺失: {', '.join(missing_resources)}",
                revision_targets=missing_resources,
                review_mode=f"{agent_id}_audit",
            )
            await emitter.emit_agent(
                review_agent_id,
                status="finished",
                message=f"{agent_id} 审核发现问题: {', '.join(missing_resources)}（已放行，请留意提示）",
                progress=95,
                metrics={"review_warning": True, "missing_resources": missing_resources},
            )
        elif "review" in AGENT_REGISTRY:
            review_input = ResourceInput(
                resource_id=state["resource_id"],
                learning_need=state["request"].learning_need,
                learning_scenario=state["request"].learning_scenario,
                profile=state["profile"],
                agent_config={
                    "review_envelope": audit_envelope,
                    "progress_agent_id": review_agent_id,
                },
            )
            async with AgentRunTracker(
                emitter=emitter,
                agent_id=review_agent_id,
                phase=f"reviewing_{agent_id}",
                message=f"正在审核{running_message.replace('正在生成', '')}内容安全与事实一致性",
                progress=92,
            ) as review_tracker:
                review_agent_result = await AGENT_REGISTRY["review"](emitter).generate_resource(review_input)
                await review_tracker.finish(
                    f"{agent_id} 审核完成",
                    success=review_agent_result.success,
                    metrics={"review_status": review_agent_result.metadata.get("review_status")},
                )
            review_result = review_result_from_agent(review_agent_result)
            if not review_result.passed:
                await emitter.emit_agent(
                    review_agent_id,
                    status="finished",
                    message=f"{agent_id} 审核发现问题: {len(review_result.issues)} 项（已放行，请留意提示）",
                    progress=95,
                    metrics={"review_warning": True, "issue_count": len(review_result.issues)},
                )
        else:
            review_result = failed_review_result(
                status="blocked",
                message=f"审核智能体不可用，无法完成{agent_id}安全审核",
                revision_targets=["review"],
                review_mode=f"{agent_id}_audit",
            )
            await emitter.emit_agent(
                review_agent_id,
                status="finished",
                message=f"审核智能体不可用，{agent_id}安全审核已跳过",
                progress=95,
                metrics={"review_warning": True, "reason": "agent_unavailable"},
            )

    return {"results": {agent_id: result}, "review_results": [review_result] if review_result else []}
