from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource
from app.memory import MemoryLayer
from app.path.planner import (
    ALL_NODE_IDS,
    adjust_plan,
    build_initial_plan,
    compute_progress,
    derive_next_action,
    score_nodes,
)
from app.path.repository import PathRepository
from app.path.schemas import PathInsight, PathPlan, PathPlanData, PathPlanMeta, PathSummary


class PathService:
    def __init__(self, repository: PathRepository, memory_layer: MemoryLayer | None = None) -> None:
        self.repository = repository
        self.memory_layer = memory_layer or MemoryLayer(module_name="mentor")

    async def build_path_plan(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        resource_id: int | None = None,
        feedback: str | None = None,
        weak_points: list[str] | None = None,
        force_rebuild: bool = False,
    ) -> PathPlanData:
        profile = await self.memory_layer.get_profile(user_id=user_id)
        resource = await self._resolve_resource(session, user_id, resource_id)

        if resource_id is not None and resource is None:
            raise LookupError("resource_not_found")

        plan_payload = self._parse_plan_payload(resource.plan_result if resource else None)
        planned_node_ids = self._extract_planned_node_ids(plan_payload)
        inferred_weak_points = self._extract_weak_points(profile, resource, weak_points)
        completed_node_ids = self._extract_completed_node_ids(resource)

        plan = build_initial_plan(
            knowledge_level=profile.knowledge_level if profile else None,
            learning_goal=profile.learning_goal if profile else None,
            weak_points=inferred_weak_points,
            planned_node_ids=planned_node_ids,
        )
        plan = score_nodes(plan, weak_points=inferred_weak_points)
        plan = compute_progress(
            plan,
            completed_node_ids=completed_node_ids,
            pace=profile.learning_pace if profile else None,
        )
        if feedback or weak_points:
            plan = adjust_plan(plan, weak_points=inferred_weak_points, feedback=feedback)

        confidence = self._compute_confidence(profile, resource, bool(plan_payload), completed_node_ids)
        plan = plan.model_copy(
            update={"progress": plan.progress.model_copy(update={"confidence": confidence})}
        )

        return self._build_response(
            plan=plan,
            profile=profile,
            resource=resource,
            force_rebuild=force_rebuild,
        )

    async def _resolve_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int | None,
    ) -> GeneratedResource | None:
        if resource_id is not None:
            return await self.repository.get_resource_by_id(session, user_id, resource_id)
        return await self.repository.get_latest_resource(session, user_id)

    def _parse_plan_payload(self, plan_result: str | None) -> dict[str, Any]:
        if not plan_result:
            return {}
        try:
            payload = json.loads(plan_result)
        except (json.JSONDecodeError, TypeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _extract_planned_node_ids(self, payload: dict[str, Any]) -> set[str] | None:
        visible = payload.get("visible_agents")
        execution = payload.get("execution_agents")
        source = visible if isinstance(visible, list) and visible else execution
        if not isinstance(source, list) or not source:
            return None
        return {str(item) for item in source if str(item) in ALL_NODE_IDS}

    def _extract_completed_node_ids(self, resource: GeneratedResource | None) -> set[str]:
        if resource is None:
            return set()
        completed: set[str] = set()
        for node_id in ALL_NODE_IDS:
            raw = getattr(resource, f"{node_id}_result", None)
            if raw is None:
                continue
            if isinstance(raw, str):
                normalized = raw.strip().lower()
                if not normalized or normalized in {"null", "{}", "[]"}:
                    continue
            completed.add(node_id)
        return completed

    def _extract_weak_points(
        self,
        profile: Any | None,
        resource: GeneratedResource | None,
        extra_weak_points: list[str] | None,
    ) -> list[str]:
        texts: list[str] = []
        if profile and profile.error_pattern:
            texts.append(profile.error_pattern)
        if resource and resource.gap:
            texts.append(resource.gap)
        if resource and resource.need:
            texts.append(resource.need)
        merged_text = " ".join(texts).lower()

        keyword_mapping: dict[str, str] = {
            "code": "code",
            "编程": "code",
            "错题": "quiz",
            "quiz": "quiz",
            "题目": "quiz",
            "概念": "content",
            "知识点": "content",
            "结构": "mindmap",
            "框架": "mindmap",
            "阅读": "reading",
            "图解": "image",
            "表达": "ppt",
            "讲解": "video",
        }

        inferred: list[str] = []
        for keyword, node_id in keyword_mapping.items():
            if keyword in merged_text:
                inferred.append(node_id)

        for node_id in (extra_weak_points or []):
            if node_id in ALL_NODE_IDS:
                inferred.append(node_id)

        if not inferred and profile and profile.learning_goal:
            goal = profile.learning_goal.lower()
            if "exam" in goal or "考试" in goal:
                inferred.append("quiz")
            if "project" in goal or "项目" in goal:
                inferred.append("code")

        ordered = [node_id for node_id in ALL_NODE_IDS if node_id in set(inferred)]
        return ordered

    def _compute_confidence(
        self,
        profile: Any | None,
        resource: GeneratedResource | None,
        has_plan_payload: bool,
        completed_node_ids: set[str],
    ) -> int:
        score = 35
        now = datetime.now()

        if profile:
            score += 25
            if profile.updated_at and (now - profile.updated_at).days <= 30:
                score += 5
        if resource:
            score += 20
            if resource.created_at:
                age_days = (now - resource.created_at).days
                if age_days <= 7:
                    score += 12
                elif age_days <= 30:
                    score += 8
        if has_plan_payload:
            score += 8
        if completed_node_ids:
            score += 4

        return max(30, min(score, 95))

    def _build_response(
        self,
        *,
        plan: PathPlan,
        profile: Any | None,
        resource: GeneratedResource | None,
        force_rebuild: bool,
    ) -> PathPlanData:
        current_stage = next(
            (stage.title for stage in plan.stages if stage.id == plan.progress.current_stage_id),
            None,
        )

        if plan.adjustments:
            adjustment_reason = plan.adjustments[-1].reason
        elif force_rebuild:
            adjustment_reason = "已根据最新数据重建路径"
        elif resource is None:
            adjustment_reason = "暂无资源记录，已生成冷启动路径"
        else:
            adjustment_reason = "按最新画像与学习资源生成路径"

        summary = PathSummary(
            overall_progress=plan.progress.overall,
            current_stage=current_stage,
            knowledge_level=plan.knowledge_level,
            eta_days=plan.progress.eta_days,
            confidence=plan.progress.confidence,
        )
        insights = PathInsight(
            adjustment_reason=adjustment_reason,
            next_action=derive_next_action(plan),
        )
        data_sources = []
        if profile:
            data_sources.append("profile")
        if resource:
            data_sources.append("resource")
        if resource and resource.plan_result:
            data_sources.append("plan_result")
        if not data_sources:
            data_sources.append("cold_start")

        meta = PathPlanMeta(
            generated_at=plan.generated_at,
            data_sources=data_sources,
            resource_id=resource.id if resource else None,
            plan_version=plan.version,
        )
        return PathPlanData(
            summary=summary,
            stages=plan.stages,
            insights=insights,
            meta=meta,
        )


class PathUseCases:
    def __init__(self, path_service: PathService) -> None:
        self.path_service = path_service

    async def get_path_plan(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        resource_id: int | None = None,
    ) -> PathPlanData:
        return await self.path_service.build_path_plan(
            session,
            user_id,
            resource_id=resource_id,
        )

    async def rebuild_path_plan(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        resource_id: int | None = None,
    ) -> PathPlanData:
        return await self.path_service.build_path_plan(
            session,
            user_id,
            resource_id=resource_id,
            force_rebuild=True,
        )

    async def apply_feedback(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        feedback: str,
        weak_points: list[str] | None = None,
        resource_id: int | None = None,
    ) -> PathPlanData:
        return await self.path_service.build_path_plan(
            session,
            user_id,
            resource_id=resource_id,
            feedback=feedback,
            weak_points=weak_points,
        )


path_repository = PathRepository()
path_service = PathService(path_repository)
path_usecases = PathUseCases(path_service)
