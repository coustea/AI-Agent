"""LangGraph nodes and helpers for the resource workflow."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import Send

from app.infra.database import session_scope
from app.resource.agents import AGENT_REGISTRY
from app.resource.agents.ppt import build_resource_material
from app.resource.events import AgentRunTracker
from app.resource.persistence import ResourceRepository, db_item_to_agent_result
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    TeachingPlan,
)
from app.resource.workflow.audit import (
    BUNDLE_AGENT_ID,
    COORDINATOR_AGENT_ID,
    PPT_AGENT_ID,
    PPT_REVIEW_AGENT_ID,
    PRE_REVIEW_AGENT_ID,
    VIDEO_AGENT_ID,
    VIDEO_REVIEW_AGENT_ID,
    build_ppt_audit_envelope,
    build_pre_audit_envelope,
    build_video_audit_envelope,
    failed_review_result,
    review_result_from_agent,
)
from app.resource.workflow.state import ParentState, WorkerInputState, merge_review_results

logger = logging.getLogger(__name__)

AGGREGATION_AGENT_IDS = (PPT_AGENT_ID, VIDEO_AGENT_ID)
BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def select_worker_agents(enabled_agents: list[str], registry: dict[str, Any]) -> list[str]:
    return [
        agent_id
        for agent_id in enabled_agents
        if agent_id in registry
        and agent_id not in ("planning", "review")
        and agent_id not in AGGREGATION_AGENT_IDS
    ]


def build_agent_resource_input(
    *,
    request,
    resource_id: int,
    agent_id: str,
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    agent_config_extra: dict[str, Any] | None,
):
    agent_config = request.agent_configs.get(agent_id, {})
    if agent_config_extra:
        agent_config = {**agent_config, **agent_config_extra}
    return ResourceInput(
        resource_id=resource_id,
        learning_need=request.learning_need,
        learning_scenario=request.learning_scenario,
        agent_name=agent_id,
        agent_config=agent_config,
        teaching_plan=teaching_plan,
        profile=profile,
        upstream_handoffs=upstream_handoffs,
    )


def require_downstream_context_for_base_result(agent_id: str, result: AgentResult) -> AgentResult:
    if agent_id not in BASE_RESOURCE_AGENT_IDS:
        return result
    if not result.success or result.downstream_context is not None:
        return result
    logger.warning("base agent %s succeeded but emitted no downstream_context; synthesizing", agent_id)
    ctx = DownstreamContext(
        source_agent=agent_id,
        title=result.title or f"{agent_id} 资源",
        one_sentence_summary=(result.summary or "")[:180],
        covered_outline_ids=[],
    )
    return result.model_copy(update={"downstream_context": ctx})


def collect_successful_handoffs(
    results: dict[str, AgentResult],
    teaching_plan: TeachingPlan | None = None,
) -> dict[str, DownstreamContext]:
    handoffs: dict[str, DownstreamContext] = {}
    for agent_id, result in results.items():
        if agent_id not in BASE_RESOURCE_AGENT_IDS:
            continue
        if not result.success or result.downstream_context is None:
            continue
        handoffs[agent_id] = result.downstream_context
    if teaching_plan is not None:
        valid_ids = {item.id for item in teaching_plan.outline}
        if valid_ids:
            for agent_id, ctx in handoffs.items():
                filtered = [oid for oid in ctx.covered_outline_ids if oid in valid_ids]
                handoffs[agent_id] = ctx.model_copy(update={"covered_outline_ids": filtered})
    return handoffs


async def load_results_for_review(
    *,
    user_id: int,
    resource_id: int,
    failures: dict[str, AgentResult],
) -> dict[str, AgentResult]:
    async with session_scope() as session:
        repository = ResourceRepository(session)
        db_items = await repository.list_resource_items(user_id, resource_id)
    persisted = {item.agent_type: db_item_to_agent_result(item) for item in db_items}
    return {**persisted, **failures}


async def persist_result_and_emit_artifact(
    *,
    user_id: int,
    resource_id: int,
    result: AgentResult,
    emitter,
    depends_on_agents: list[str] | None = None,
) -> None:
    async with session_scope() as session:
        repository = ResourceRepository(session)
        resource_item = await repository.save_agent_result(
            user_id=user_id,
            resource_id=resource_id,
            result=result,
            depends_on_agents=depends_on_agents,
        )
    agent_id = str(result.metadata.get("agent_id") or "")
    await emitter.emit_artifact_ready(
        agent_id,
        message=f"{agent_id} 资源已保存，可在产物坞预览",
        artifact_id=str(resource_item.id),
        metrics=result.metrics,
    )


async def planning_node(state: ParentState) -> dict[str, Any]:
    planning_input = ResourceInput(
        resource_id=state["resource_id"],
        learning_need=state["request"].learning_need,
        learning_scenario=state["request"].learning_scenario,
        profile=state["profile"],
        agent_config={"enabled_agents": state["request"].enabled_agent_ids()},
    )
    async with AgentRunTracker(
        emitter=state["emitter"],
        agent_id="planning",
        phase="planning",
        message="正在规划教学方向与大纲",
        progress=5,
    ) as planning_tracker:
        planning_result = await AGENT_REGISTRY["planning"](state["emitter"]).generate_resource(planning_input)
        await planning_tracker.finish(
            "教学方向与大纲已生成" if planning_result.success else (planning_result.error or "规划失败"),
            success=planning_result.success,
            metrics={"enabled_agents": len(state["request"].enabled_agent_ids())},
        )

    teaching_plan = None
    if planning_result.success and planning_result.metadata:
        plan_data = planning_result.metadata.get("teaching_plan")
        if isinstance(plan_data, dict):
            teaching_plan = TeachingPlan.model_validate(plan_data)

    if not planning_result.success or teaching_plan is None:
        raise ValueError(planning_result.error or "规划阶段未返回教学计划")

    return {"teaching_plan": teaching_plan}


def base_worker_ids(state: ParentState) -> list[str]:
    enabled = state["request"].enabled_agent_ids()
    return [aid for aid in enabled if aid in BASE_RESOURCE_AGENT_IDS]


def route_workers_or_merge(state: ParentState) -> list[Send] | list[str]:
    worker_ids = base_worker_ids(state)
    if not worker_ids:
        return ["merge_workers"]
    return [
        Send("worker_node", {
            "agent_id": agent_id,
            "user_id": state["user_id"],
            "resource_id": state["resource_id"],
            "request": state["request"],
            "teaching_plan": state["teaching_plan"],
            "profile": state["profile"],
            "run_id": state["run_id"],
            "emitter": state["emitter"],
        })
        for agent_id in worker_ids
    ]


async def worker_node(state: WorkerInputState) -> dict[str, Any]:
    agent_id = state["agent_id"]
    resource_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=agent_id,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs={},
        agent_config_extra=None,
    )

    agent = AGENT_REGISTRY[agent_id](state["emitter"])
    try:
        async with AgentRunTracker(
            emitter=state["emitter"],
            agent_id=agent_id,
            phase="llm_generating",
            message=f"{agent_id} 模型生成中",
            progress=25,
        ) as tracker:
            result = await agent.generate_resource(resource_input)
            await tracker.step(
                "validating",
                f"{agent_id} 已返回，正在校验与整理结果",
                progress=86,
            )
            await tracker.finish(
                result.summary if result.success else (result.error or f"{agent_id} 生成失败"),
                success=result.success,
                metrics=result.metrics,
            )
    except Exception as exc:
        logger.error("worker_node %s 异常: %s", agent_id, exc, exc_info=True)
        result = AgentResult(
            success=False,
            error=str(exc),
            title=f"{agent_id} 资源",
            summary=f"{agent_id} 生成异常: {exc}",
            metadata={"agent_id": agent_id},
        )
        await state["emitter"].emit_agent(
            agent_id,
            status="failed",
            message=f"{agent_id} 生成异常",
            progress=0,
        )

    if result.success and result.content:
        try:
            await persist_result_and_emit_artifact(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                result=result,
                emitter=state["emitter"],
            )
        except Exception as exc:
            logger.error("worker_node %s 入库异常: %s", agent_id, exc, exc_info=True)
            result = AgentResult(
                success=False,
                error=f"入库失败: {exc}",
                title=result.title,
                summary=result.summary,
                content=result.content,
                file_type=result.file_type,
                metadata=result.metadata,
            )

    result = require_downstream_context_for_base_result(agent_id, result)
    return {"results": {agent_id: result}}


async def merge_workers_node(state: ParentState) -> dict[str, Any]:
    results = state.get("results") or {}
    success_count = sum(1 for r in results.values() if r.success)
    fail_count = sum(1 for r in results.values() if not r.success)
    worker_agents = select_worker_agents(state["request"].enabled_agent_ids(), AGENT_REGISTRY)
    coordinator_status = "failed" if worker_agents and success_count == 0 else "finished"
    message = (
        f"基础资源并行生成完成：成功 {success_count} 个，失败 {fail_count} 个"
        if worker_agents
        else "未选择基础资源，聚合资源将基于教学计划生成"
    )
    await state["emitter"].emit_agent(
        COORDINATOR_AGENT_ID,
        status=coordinator_status,
        message=message,
        progress=70,
    )
    return {}


def route_aggregation_after_audit(state: ParentState) -> list[str]:
    enabled = state["request"].enabled_agent_ids()
    destinations: list[str] = []
    if PPT_AGENT_ID in enabled:
        destinations.append("ppt_node")
    if VIDEO_AGENT_ID in enabled:
        destinations.append("video_node")
    return destinations or ["save_node"]


async def pre_audit_node(state: ParentState) -> dict[str, Any]:
    failed_results = {aid: r for aid, r in state["results"].items() if not r.success}
    review_results = await load_results_for_review(
        user_id=state["user_id"],
        resource_id=state["resource_id"],
        failures=failed_results,
    )

    pre_audit_envelope, missing_resources = build_pre_audit_envelope(
        request=state["request"],
        results=review_results,
        profile=state["profile"],
        teaching_plan=state["teaching_plan"],
    )
    source_audit_required = bool(pre_audit_envelope["deep_audit_resources"])

    pre_review_result = None
    if missing_resources:
        pre_review_result = failed_review_result(
            status="needs_revision",
            message=f"资源生成不完整: {', '.join(missing_resources)}",
            revision_targets=missing_resources,
            review_mode="pre_audit",
        )
        await state["emitter"].emit_agent(
            PRE_REVIEW_AGENT_ID,
            status="finished",
            message=f"审核发现资源不完整: {', '.join(missing_resources)}（已放行，请留意提示）",
            progress=80,
            metrics={"review_warning": True, "missing_resources": missing_resources},
        )
    elif source_audit_required and "review" in AGENT_REGISTRY:
        review_input = ResourceInput(
            resource_id=state["resource_id"],
            learning_need=state["request"].learning_need,
            learning_scenario=state["request"].learning_scenario,
            profile=state["profile"],
            agent_config={
                "review_envelope": pre_audit_envelope,
                "progress_agent_id": PRE_REVIEW_AGENT_ID,
            },
        )
        async with AgentRunTracker(
            emitter=state["emitter"],
            agent_id=PRE_REVIEW_AGENT_ID,
            phase="reviewing_sources",
            message="正在审核基础资源事实性与安全性",
            progress=72,
        ) as pre_review_tracker:
            pre_review_agent_result = await AGENT_REGISTRY["review"](state["emitter"]).generate_resource(review_input)
            await pre_review_tracker.finish(
                "前置审核完成",
                success=pre_review_agent_result.success,
                metrics={"review_status": pre_review_agent_result.metadata.get("review_status")},
            )
        pre_review_result = review_result_from_agent(pre_review_agent_result)
        if not pre_review_result.passed:
            await state["emitter"].emit_agent(
                PRE_REVIEW_AGENT_ID,
                status="finished",
                message=f"审核发现问题: {len(pre_review_result.issues)} 项（已放行，请留意提示）",
                progress=80,
                metrics={"review_warning": True, "issue_count": len(pre_review_result.issues)},
            )
    else:
        await state["emitter"].emit_agent(
            PRE_REVIEW_AGENT_ID,
            status="skipped",
            message="无需深度审核，跳过前置审核",
            progress=80,
        )
        from app.resource.schemas import ReviewResult
        pre_review_result = ReviewResult(passed=True, overall_score=100)

    return {"review_results": [pre_review_result] if pre_review_result else []}


async def ppt_node(state: ParentState) -> dict[str, Any]:
    await state["emitter"].emit_agent(
        PPT_AGENT_ID,
        status="running",
        message="正在生成 PPT",
        progress=80,
        phase="ppt_generating",
    )

    base_handoffs = collect_successful_handoffs(state["results"], teaching_plan=state.get("teaching_plan"))
    material_bundle = build_resource_material(ResourceInput(
        resource_id=state["resource_id"],
        learning_need=state["request"].learning_need,
        learning_scenario=state["request"].learning_scenario,
        agent_name=PPT_AGENT_ID,
        agent_config=state["request"].agent_configs.get(PPT_AGENT_ID, {}),
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
    ))

    ppt_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=PPT_AGENT_ID,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra={
            "material_bundle": material_bundle.model_dump(mode="json"),
            "upstream_handoff_agent_ids": list(base_handoffs.keys()),
        },
    )

    ppt_agent = AGENT_REGISTRY[PPT_AGENT_ID](state["emitter"])
    async with AgentRunTracker(
        emitter=state["emitter"],
        agent_id=PPT_AGENT_ID,
        phase="llm_generating",
        message="PPT 模型生成中",
        progress=80,
    ) as tracker:
        ppt_result = await ppt_agent.generate_resource(ppt_input)
        await tracker.finish(
            ppt_result.summary if ppt_result.success else (ppt_result.error or "PPT 生成失败"),
            success=ppt_result.success,
            metrics=ppt_result.metrics,
        )

    if ppt_result.success and ppt_result.content:
        await persist_result_and_emit_artifact(
            user_id=state["user_id"],
            resource_id=state["resource_id"],
            result=ppt_result,
            emitter=state["emitter"],
            depends_on_agents=list(base_handoffs.keys()),
        )

    await state["emitter"].emit_agent(PPT_REVIEW_AGENT_ID, status="running", message="PPT 内容审核中", progress=90)
    ppt_review_result = None
    if not ppt_result or not ppt_result.success:
        await state["emitter"].emit_agent(
            PPT_REVIEW_AGENT_ID,
            status="skipped",
            message="PPT 未成功生成，跳过 PPT 审核",
            progress=95,
        )
    else:
        ppt_failed_results = {aid: r for aid, r in {**state["results"], "ppt": ppt_result}.items() if not r.success}
        ppt_review_results = await load_results_for_review(
            user_id=state["user_id"],
            resource_id=state["resource_id"],
            failures=ppt_failed_results,
        )
        ppt_audit_envelope, ppt_missing_resources = build_ppt_audit_envelope(
            request=state["request"],
            results=ppt_review_results,
            profile=state["profile"],
            teaching_plan=state["teaching_plan"],
        )
        if ppt_missing_resources:
            ppt_review_result = failed_review_result(
                status="needs_revision",
                message=f"PPT 审核发现缺失: {', '.join(ppt_missing_resources)}",
                revision_targets=ppt_missing_resources,
                review_mode="ppt_audit",
            )
            await state["emitter"].emit_agent(
                PPT_REVIEW_AGENT_ID,
                status="finished",
                message=f"PPT 审核发现问题: {', '.join(ppt_missing_resources)}（已放行，请留意提示）",
                progress=95,
                metrics={"review_warning": True, "missing_resources": ppt_missing_resources},
            )
        elif "review" in AGENT_REGISTRY:
            ppt_review_input = ResourceInput(
                resource_id=state["resource_id"],
                learning_need=state["request"].learning_need,
                learning_scenario=state["request"].learning_scenario,
                profile=state["profile"],
                agent_config={
                    "review_envelope": ppt_audit_envelope,
                    "progress_agent_id": PPT_REVIEW_AGENT_ID,
                },
            )
            async with AgentRunTracker(
                emitter=state["emitter"],
                agent_id=PPT_REVIEW_AGENT_ID,
                phase="reviewing_ppt",
                message="正在审核 PPT 内容安全与事实一致性",
                progress=92,
            ) as ppt_review_tracker:
                ppt_review_agent_result = await AGENT_REGISTRY["review"](state["emitter"]).generate_resource(ppt_review_input)
                await ppt_review_tracker.finish(
                    "PPT 审核完成",
                    success=ppt_review_agent_result.success,
                    metrics={"review_status": ppt_review_agent_result.metadata.get("review_status")},
                )
            ppt_review_result = review_result_from_agent(ppt_review_agent_result)
            if not ppt_review_result.passed:
                await state["emitter"].emit_agent(
                    PPT_REVIEW_AGENT_ID,
                    status="finished",
                    message=f"PPT 审核发现问题: {len(ppt_review_result.issues)} 项（已放行，请留意提示）",
                    progress=95,
                    metrics={"review_warning": True, "issue_count": len(ppt_review_result.issues)},
                )
        else:
            ppt_review_result = failed_review_result(
                status="blocked",
                message="审核智能体不可用，无法完成 PPT 安全审核",
                revision_targets=["review"],
                review_mode="ppt_audit",
            )
            await state["emitter"].emit_agent(
                PPT_REVIEW_AGENT_ID,
                status="finished",
                message="审核智能体不可用，PPT 安全审核已跳过",
                progress=95,
                metrics={"review_warning": True, "reason": "agent_unavailable"},
            )

    return {"results": {"ppt": ppt_result}, "review_results": [ppt_review_result] if ppt_review_result else []}


async def video_node(state: ParentState) -> dict[str, Any]:
    await state["emitter"].emit_agent(
        VIDEO_AGENT_ID,
        status="running",
        message="正在生成讲解视频配置与分镜",
        progress=80,
        phase="video_generating",
    )

    base_handoffs = collect_successful_handoffs(state["results"], teaching_plan=state.get("teaching_plan"))
    video_input = build_agent_resource_input(
        request=state["request"],
        resource_id=state["resource_id"],
        agent_id=VIDEO_AGENT_ID,
        teaching_plan=state["teaching_plan"],
        profile=state["profile"],
        upstream_handoffs=base_handoffs,
        agent_config_extra=None,
    )

    video_agent = AGENT_REGISTRY[VIDEO_AGENT_ID](state["emitter"])
    async with AgentRunTracker(
        emitter=state["emitter"],
        agent_id=VIDEO_AGENT_ID,
        phase="llm_generating",
        message="视频模型生成中",
        progress=80,
    ) as tracker:
        video_result = await video_agent.generate_resource(video_input)
        await tracker.finish(
            video_result.summary if video_result.success else (video_result.error or "视频生成失败"),
            success=video_result.success,
            metrics=video_result.metrics,
        )

    if video_result.success and video_result.content:
        await persist_result_and_emit_artifact(
            user_id=state["user_id"],
            resource_id=state["resource_id"],
            result=video_result,
            emitter=state["emitter"],
            depends_on_agents=list(base_handoffs.keys()),
        )

    await state["emitter"].emit_agent(VIDEO_REVIEW_AGENT_ID, status="running", message="讲解视频内容审核中", progress=90)
    video_review_result = None
    if not video_result or not video_result.success:
        await state["emitter"].emit_agent(
            VIDEO_REVIEW_AGENT_ID,
            status="skipped",
            message="讲解视频未成功生成，跳过审核",
            progress=95,
        )
    else:
        video_failed_results = {aid: r for aid, r in {**state["results"], "video": video_result}.items() if not r.success}
        video_review_results = await load_results_for_review(
            user_id=state["user_id"],
            resource_id=state["resource_id"],
            failures=video_failed_results,
        )
        video_audit_envelope, video_missing_resources = build_video_audit_envelope(
            request=state["request"],
            results=video_review_results,
            profile=state["profile"],
            teaching_plan=state["teaching_plan"],
        )
        if video_missing_resources:
            video_review_result = failed_review_result(
                status="needs_revision",
                message=f"视频审核发现缺失: {', '.join(video_missing_resources)}",
                revision_targets=video_missing_resources,
                review_mode="video_audit",
            )
            await state["emitter"].emit_agent(
                VIDEO_REVIEW_AGENT_ID,
                status="finished",
                message=f"视频审核发现问题: {', '.join(video_missing_resources)}（已放行，请留意提示）",
                progress=95,
                metrics={"review_warning": True, "missing_resources": video_missing_resources},
            )
        elif "review" in AGENT_REGISTRY:
            video_review_input = ResourceInput(
                resource_id=state["resource_id"],
                learning_need=state["request"].learning_need,
                learning_scenario=state["request"].learning_scenario,
                profile=state["profile"],
                agent_config={
                    "review_envelope": video_audit_envelope,
                    "progress_agent_id": VIDEO_REVIEW_AGENT_ID,
                },
            )
            async with AgentRunTracker(
                emitter=state["emitter"],
                agent_id=VIDEO_REVIEW_AGENT_ID,
                phase="reviewing_video",
                message="正在审核讲解视频内容安全与事实一致性",
                progress=92,
            ) as video_review_tracker:
                video_review_agent_result = await AGENT_REGISTRY["review"](state["emitter"]).generate_resource(video_review_input)
                await video_review_tracker.finish(
                    "讲解视频审核完成",
                    success=video_review_agent_result.success,
                    metrics={"review_status": video_review_agent_result.metadata.get("review_status")},
                )
            video_review_result = review_result_from_agent(video_review_agent_result)
            if not video_review_result.passed:
                await state["emitter"].emit_agent(
                    VIDEO_REVIEW_AGENT_ID,
                    status="finished",
                    message=f"视频审核发现问题: {len(video_review_result.issues)} 项（已放行，请留意提示）",
                    progress=95,
                    metrics={"review_warning": True, "issue_count": len(video_review_result.issues)},
                )
        else:
            video_review_result = failed_review_result(
                status="blocked",
                message="审核智能体不可用，无法完成视频安全审核",
                revision_targets=["review"],
                review_mode="video_audit",
            )
            await state["emitter"].emit_agent(
                VIDEO_REVIEW_AGENT_ID,
                status="finished",
                message="审核智能体不可用，视频安全审核已跳过",
                progress=95,
                metrics={"review_warning": True, "reason": "agent_unavailable"},
            )

    return {"results": {"video": video_result}, "review_results": [video_review_result] if video_review_result else []}


async def save_node(state: ParentState) -> dict[str, Any]:
    await state["emitter"].emit_agent(
        BUNDLE_AGENT_ID,
        status="running",
        message="正在组装资源包并保存结果",
        progress=95,
        phase="bundling",
    )

    review_result = merge_review_results(state.get("review_results") or [])

    try:
        async with session_scope() as session:
            repository = ResourceRepository(session)
            await repository.save_generation_results(
                user_id=state["user_id"],
                resource_id=state["resource_id"],
                request=state["request"],
                results=state["results"],
                review_result=review_result,
                teaching_plan=state["teaching_plan"],
            )
            saved_items = await repository.list_resource_items(state["user_id"], state["resource_id"])
            resource = await repository.get_resource(state["user_id"], state["resource_id"])
            current_status = resource.status if resource else "failed"
            success = current_status in ("completed", "partial_completed") and len(saved_items) > 0

            await state["emitter"].emit_agent(
                BUNDLE_AGENT_ID,
                status="finished" if success else "failed",
                message="资源包组装完成" if success else "资源包组装失败",
                progress=100,
            )
            return {"success": success}
    except Exception:
        await state["emitter"].emit_agent(BUNDLE_AGENT_ID, status="failed", message="资源包组装异常", progress=0)
        raise
