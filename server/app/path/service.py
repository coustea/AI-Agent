"""Path planning service.

学习路径规划业务服务层，整合数据访问和业务逻辑。
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import (
    GeneratedResource,
    GeneratedResourceItem,
    LearningEvent,
    LearningPath,
    LearningPathAdjustment,
    LearningPathNode,
)
from app.memory import MemoryLayer
from app.path.planner import (
    ALL_NODE_IDS,
    NODE_TITLES,
    adjust_plan,
    analyze_profile_dimensions,
    build_initial_plan,
    compute_progress,
    derive_next_action,
    recommend_next_nodes,
)
from app.path.profile_recommender import (
    compute_learning_pace,
    compute_node_scores,
    estimate_completion_time,
    recommend_nodes,
)
from app.path.schemas import PathInsight, PathPlan, PathPlanData, PathPlanMeta, PathSummary


class PathService:
    """学习路径规划服务。"""

    def __init__(self, memory_layer: MemoryLayer | None = None) -> None:
        self.memory_layer = memory_layer or MemoryLayer(module="mentor")

    # =========================================================================
    # 路径规划核心方法
    # =========================================================================

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
        """构建学习路径计划。"""
        profile = await self.memory_layer.get_profile(user_id=user_id)
        resource = await self._get_resource(session, user_id, resource_id)

        if resource_id is not None and resource is None:
            raise LookupError("resource_not_found")

        resource_items = await self._list_resource_items(session, resource)
        planned_node_ids = self._extract_planned_node_ids(resource, resource_items)
        inferred_weak_points = self._extract_weak_points(profile, resource, weak_points)
        completed_node_ids = await self._get_completed_node_ids(session, user_id, resource)

        profile_json = profile.profile_json if profile and profile.profile_json else None
        profile_dimensions = analyze_profile_dimensions(profile_json)

        # 基于画像计算节点评分
        node_scores = compute_node_scores(
            profile_json,
            weak_points=inferred_weak_points,
            completed_node_ids=completed_node_ids,
        )

        plan = build_initial_plan(
            knowledge_level=self._get_profile_field(profile, "knowledge_foundation"),
            learning_goal=self._get_profile_field(profile, "learning_goal"),
            weak_points=inferred_weak_points,
            planned_node_ids=planned_node_ids,
            profile_dimensions=profile_dimensions,
        )

        plan = self._apply_profile_scores(plan, node_scores)
        plan = compute_progress(
            plan,
            completed_node_ids=completed_node_ids,
            pace=compute_learning_pace(profile_json),
        )

        if feedback or weak_points:
            plan = adjust_plan(
                plan,
                weak_points=inferred_weak_points,
                feedback=feedback,
                profile_dimensions=profile_dimensions,
            )

        plan = self._attach_resource_items(plan, resource, resource_items)
        plan = self._attach_recommendation_reasons(plan, profile_dimensions)

        confidence = self._compute_confidence(profile, resource, bool(resource_items), completed_node_ids)
        plan = plan.model_copy(
            update={"progress": plan.progress.model_copy(update={"confidence": confidence})}
        )

        await self._save_learning_path(session, user_id, plan, profile_json, resource)

        return self._build_response(
            plan=plan,
            profile=profile,
            resource=resource,
            resource_items=resource_items,
            force_rebuild=force_rebuild,
        )

    async def update_node_progress(
        self,
        session: AsyncSession,
        user_id: int,
        node_id: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        resource_id: int | None = None,
    ) -> LearningPathNode | None:
        """更新学习节点的进度。"""
        path = await self._get_learning_path(session, user_id)
        if not path:
            return None

        node = await self._get_path_node(session, path.id, node_id)
        if not node:
            return None

        now = datetime.now(timezone.utc)
        updates = {"updated_at": now}

        if status is not None:
            updates["status"] = status
            if status == "processing" and node.started_at is None:
                updates["started_at"] = now
            elif status == "success":
                updates["completed_at"] = now
                updates["progress"] = 100

        if progress is not None:
            updates["progress"] = min(100, max(0, progress))

        if resource_id is not None:
            updates["resource_id"] = resource_id

        for key, value in updates.items():
            setattr(node, key, value)

        session.add(node)
        await session.commit()
        await session.refresh(node)

        await self._recalculate_path_progress(session, path)
        return node

    async def get_node_recommendations(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """获取基于画像的节点推荐。"""
        profile = await self.memory_layer.get_profile(user_id=user_id)
        profile_json = profile.profile_json if profile and profile.profile_json else None

        completed_node_ids = await self._get_completed_node_ids_from_path(session, user_id)

        recommendations = recommend_nodes(
            profile_json,
            completed_node_ids=completed_node_ids,
            top_k=top_k,
        )

        return [
            {
                "node_id": r.node_id,
                "node_title": r.node_title,
                "priority_score": r.priority_score,
                "confidence": r.confidence,
                "reasons": r.reasons,
                "profile_dimensions_used": r.profile_dimensions_used,
            }
            for r in recommendations
        ]

    async def record_adjustment(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        adjustment_type: str,
        reason: str,
        impacted_node_ids: list[str] | None = None,
        before_snapshot: dict[str, Any] | None = None,
        after_snapshot: dict[str, Any] | None = None,
    ) -> LearningPathAdjustment | None:
        """记录路径调整。"""
        path = await self._get_learning_path(session, user_id)
        if not path:
            return None

        adjustment = LearningPathAdjustment(
            path_id=path.id,
            user_id=user_id,
            adjustment_type=adjustment_type,
            reason=reason,
            impacted_node_ids=impacted_node_ids,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            created_at=datetime.now(timezone.utc),
        )

        session.add(adjustment)
        await session.commit()
        await session.refresh(adjustment)
        return adjustment

    # =========================================================================
    # 数据访问方法
    # =========================================================================

    async def _get_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int | None,
    ) -> GeneratedResource | None:
        """获取生成资源。"""
        if resource_id is not None:
            resource = await session.get(GeneratedResource, resource_id)
            return resource if resource and resource.user_id == user_id else None

        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(GeneratedResource.created_at.desc())
            .limit(1)
        )
        result = await session.exec(stmt)
        return result.first()

    async def _list_resource_items(
        self,
        session: AsyncSession,
        resource: GeneratedResource | None,
    ) -> list[GeneratedResourceItem]:
        """列出资源项。"""
        if resource is None or resource.id is None:
            return []

        stmt = (
            select(GeneratedResourceItem)
            .where(GeneratedResourceItem.user_id == resource.user_id)
            .where(GeneratedResourceItem.resource_id == resource.id)
            .order_by(GeneratedResourceItem.created_at.asc())
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def _get_learning_path(
        self,
        session: AsyncSession,
        user_id: int,
        module: str = "mentor",
    ) -> LearningPath | None:
        """获取用户的学习路径。"""
        stmt = (
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .where(LearningPath.module == module)
            .where(LearningPath.is_active == True)
        )
        result = await session.exec(stmt)
        return result.first()

    async def _get_path_node(
        self,
        session: AsyncSession,
        path_id: int,
        node_id: str,
    ) -> LearningPathNode | None:
        """获取路径节点。"""
        stmt = (
            select(LearningPathNode)
            .where(LearningPathNode.path_id == path_id)
            .where(LearningPathNode.node_id == node_id)
        )
        result = await session.exec(stmt)
        return result.first()

    async def _get_completed_node_ids(
        self,
        session: AsyncSession,
        user_id: int,
        resource: GeneratedResource | None,
    ) -> set[str]:
        """从学习事件中获取已完成的节点 ID。"""
        resource_id = resource.id if resource else None

        stmt = select(LearningEvent).where(LearningEvent.user_id == user_id)
        if resource_id is not None:
            stmt = stmt.where(LearningEvent.resource_id == resource_id)
        stmt = stmt.order_by(LearningEvent.created_at.desc()).limit(200)

        result = await session.exec(stmt)
        completed: set[str] = set()

        for event in result.all():
            if event.event_type not in {"resource_completed", "node_completed", "quiz_submitted"}:
                continue

            metadata = event.metadata_json or {}
            candidates = [
                metadata.get("node_id"),
                metadata.get("agent_type"),
                metadata.get("resource_type"),
            ]

            if event.event_type == "quiz_submitted" and event.score is not None and event.score >= 60:
                candidates.append("quiz")

            for raw in candidates:
                node_id = str(raw) if raw else ""
                if node_id in ALL_NODE_IDS:
                    completed.add(node_id)

        return completed

    async def _get_completed_node_ids_from_path(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> set[str]:
        """从路径节点中获取已完成的节点 ID。"""
        path = await self._get_learning_path(session, user_id)
        if not path:
            return set()

        stmt = (
            select(LearningPathNode)
            .where(LearningPathNode.path_id == path.id)
            .where(LearningPathNode.status == "success")
        )
        result = await session.exec(stmt)
        return {n.node_id for n in result.all()}

    async def _save_learning_path(
        self,
        session: AsyncSession,
        user_id: int,
        plan: PathPlan,
        profile_json: dict[str, Any] | None,
        resource: GeneratedResource | None,
    ) -> LearningPath | None:
        """保存学习路径到数据库。"""
        now = datetime.now(timezone.utc)

        path = await self._get_learning_path(session, user_id)
        if path:
            path.version += 1
            path.updated_at = now
        else:
            path = LearningPath(
                user_id=user_id,
                module=self.memory_layer.module,
                created_at=now,
                updated_at=now,
            )

        path.learning_goal = plan.learning_goal
        path.knowledge_level = plan.knowledge_level
        path.overall_progress = plan.progress.overall
        path.current_stage_id = plan.progress.current_stage_id
        path.eta_days = plan.progress.eta_days
        path.confidence = plan.progress.confidence
        path.profile_snapshot = profile_json

        session.add(path)
        await session.commit()
        await session.refresh(path)

        # 删除旧节点
        stmt = delete(LearningPathNode).where(LearningPathNode.path_id == path.id)
        await session.exec(stmt)

        # 创建新节点
        resource_id = resource.id if resource else None
        for stage in plan.stages:
            for node in stage.nodes:
                path_node = LearningPathNode(
                    path_id=path.id,
                    user_id=user_id,
                    node_id=node.id,
                    stage_id=stage.id,
                    title=node.title,
                    status=node.status,
                    progress=node.progress,
                    priority=node.priority,
                    recommendation_reason=node.recommendation_reason or node.desc,
                    resource_id=node.resource_id or resource_id,
                    completed_at=now if node.status == "success" else None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(path_node)

        await session.commit()
        return path

    async def _recalculate_path_progress(
        self,
        session: AsyncSession,
        path: LearningPath,
    ) -> None:
        """重新计算路径整体进度。"""
        stmt = select(LearningPathNode).where(LearningPathNode.path_id == path.id)
        result = await session.exec(stmt)
        nodes = list(result.all())

        if not nodes:
            return

        total = len(nodes)
        completed = sum(1 for n in nodes if n.status == "success")
        overall = int((completed / total) * 100) if total else 0

        current_stage_id = None
        for node in nodes:
            if node.status != "success":
                current_stage_id = node.stage_id
                break

        path.overall_progress = overall
        path.current_stage_id = current_stage_id
        path.updated_at = datetime.now(timezone.utc)

        session.add(path)
        await session.commit()

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _apply_profile_scores(self, plan: PathPlan, node_scores: dict[str, float]) -> PathPlan:
        """将基于画像的节点评分应用到路径规划中。"""
        updated_stages = []
        for stage in plan.stages:
            updated_nodes = [
                node.model_copy(update={"priority": int(node_scores.get(node.id, node.priority))})
                for node in stage.nodes
            ]
            updated_stages.append(stage.model_copy(update={"nodes": updated_nodes}))
        return plan.model_copy(update={"stages": updated_stages})

    def _extract_planned_node_ids(
        self,
        resource: GeneratedResource | None,
        resource_items: list[Any],
    ) -> set[str] | None:
        """提取已规划的节点 ID。"""
        candidates = []

        selected = getattr(resource, "selected_agents", None) if resource else None
        if isinstance(selected, list):
            candidates.extend(str(item) for item in selected)

        candidates.extend(str(getattr(item, "agent_type", "")) for item in resource_items)

        node_ids = {self._normalize_node_id(item) for item in candidates}
        node_ids = {item for item in node_ids if item in ALL_NODE_IDS}

        return node_ids if node_ids else None

    def _extract_weak_points(
        self,
        profile: Any | None,
        resource: GeneratedResource | None,
        extra_weak_points: list[str] | None,
    ) -> list[str]:
        """提取薄弱点。"""
        texts = []

        if profile and profile.profile_json:
            dims = profile.profile_json.get("dimensions", {})
            if dims.get("weakness_points", {}).get("summary"):
                texts.append(dims["weakness_points"]["summary"])

        if resource and resource.learning_need:
            texts.append(resource.learning_need)

        merged_text = " ".join(texts).lower()

        keyword_mapping = {
            "code": "code", "编程": "code",
            "错题": "quiz", "quiz": "quiz", "题目": "quiz",
            "概念": "content", "知识点": "content",
            "结构": "mindmap", "框架": "mindmap",
            "阅读": "reading",
            "图解": "diagram", "图表": "diagram",
            "表达": "content", "讲解": "content",
        }

        inferred = [node_id for kw, node_id in keyword_mapping.items() if kw in merged_text]

        for node_id in (extra_weak_points or []):
            if node_id in ALL_NODE_IDS:
                inferred.append(node_id)

        # 根据学习目标推断
        if not inferred and profile and profile.profile_json:
            goal = profile.profile_json.get("dimensions", {}).get("learning_goal", {}).get("summary", "")
            if goal:
                goal_lower = goal.lower()
                if "exam" in goal_lower or "考试" in goal_lower:
                    inferred.append("quiz")
                if "project" in goal_lower or "项目" in goal_lower:
                    inferred.append("code")

        return [node_id for node_id in ALL_NODE_IDS if node_id in set(inferred)]

    def _get_profile_field(self, profile: Any | None, field: str) -> str | None:
        """获取画像字段值。"""
        if not profile or not profile.profile_json:
            return None
        dims = profile.profile_json.get("dimensions", {})
        return dims.get(field, {}).get("summary")

    def _compute_confidence(
        self,
        profile: Any | None,
        resource: GeneratedResource | None,
        has_resource_items: bool,
        completed_node_ids: set[str],
    ) -> int:
        """计算路径置信度。"""
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

        if has_resource_items:
            score += 10

        if completed_node_ids:
            score += 4

        return max(30, min(score, 95))

    def _attach_resource_items(
        self,
        plan: PathPlan,
        resource: GeneratedResource | None,
        resource_items: list[Any],
    ) -> PathPlan:
        """关联资源项到路径节点。"""
        resource_id = resource.id if resource else None
        item_map: dict[str, Any] = {}

        for item in resource_items:
            node_id = self._normalize_node_id(getattr(item, "agent_type", ""))
            if node_id in ALL_NODE_IDS and node_id not in item_map:
                item_map[node_id] = item

        stages = []
        for stage in plan.stages:
            nodes = []
            for node in stage.nodes:
                item = item_map.get(node.id)
                if item is None:
                    nodes.append(node.model_copy(update={
                        "resource_id": resource_id,
                        "resource_type": node.id,
                        "resource_status": "missing" if resource_id is not None else None,
                    }))
                    continue

                content_json = getattr(item, "content_json", None) or {}
                resource_status = self._get_resource_status(item)

                nodes.append(node.model_copy(update={
                    "resource_id": resource_id,
                    "resource_item_id": getattr(item, "id", None),
                    "resource_type": node.id,
                    "resource_title": content_json.get("title") or node.title,
                    "resource_summary": content_json.get("summary") or getattr(item, "content_text", None),
                    "resource_format": content_json.get("format") or getattr(item, "content_format", None),
                    "resource_status": resource_status,
                }))
            stages.append(stage.model_copy(update={"nodes": nodes}))

        return plan.model_copy(update={"stages": stages})

    def _get_resource_status(self, item: Any) -> str:
        """获取资源项状态。"""
        status = str(getattr(item, "status", "") or "").lower()

        if status == "failed":
            return "failed"
        if status in {"pending", "running"}:
            return "pending"

        if status == "completed":
            content_json = getattr(item, "content_json", None)
            content_text = getattr(item, "content_text", None)

            if isinstance(content_json, dict) and content_json:
                content = content_json.get("content")
                if content not in (None, "", {}, []):
                    return "available"

            if isinstance(content_text, str) and content_text.strip():
                return "available"

        return "missing"

    def _attach_recommendation_reasons(
        self,
        plan: PathPlan,
        profile_dimensions: dict[str, dict],
    ) -> PathPlan:
        """附加推荐理由到节点。"""
        recommendations = recommend_next_nodes(
            plan,
            top_n=len(ALL_NODE_IDS),
            profile_dimensions=profile_dimensions,
        )
        reason_map = {item["node_id"]: item["reason"] for item in recommendations}

        stages = []
        for stage in plan.stages:
            nodes = [
                node.model_copy(update={
                    "recommendation_reason": reason_map.get(
                        node.id,
                        node.recommendation_reason or f"根据学习路径规划，建议完成「{node.title}」",
                    )
                })
                for node in stage.nodes
            ]
            stages.append(stage.model_copy(update={"nodes": nodes}))

        return plan.model_copy(update={"stages": stages})

    def _normalize_node_id(self, raw: str) -> str:
        """标准化节点 ID。"""
        node_id = (raw or "").strip().lower()
        aliases = {
            "image": "diagram", "chart": "diagram", "flowchart": "diagram",
            "ppt": "content", "video": "content",
        }
        return aliases.get(node_id, node_id)

    def _build_response(
        self,
        *,
        plan: PathPlan,
        profile: Any | None,
        resource: GeneratedResource | None,
        resource_items: list[Any],
        force_rebuild: bool,
    ) -> PathPlanData:
        """构建响应数据。"""
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
            current_node=plan.progress.current_node_id,
            knowledge_level=plan.knowledge_level,
            eta_days=plan.progress.eta_days,
            confidence=plan.progress.confidence,
        )

        insights = PathInsight(
            adjustment_reason=adjustment_reason,
            next_action=derive_next_action(plan),
            recommended_nodes=recommend_next_nodes(
                plan,
                top_n=3,
                profile_dimensions=plan.profile_dimensions,
            ),
        )

        data_sources = []
        if profile:
            data_sources.append("profile")
        if resource:
            data_sources.append("resource")
        if resource_items:
            data_sources.append("resource_items")
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
    """学习路径用例层。"""

    def __init__(self, path_service: PathService) -> None:
        self.path_service = path_service

    async def get_path_plan(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        resource_id: int | None = None,
    ) -> PathPlanData:
        """获取路径规划。"""
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
        """重建路径规划。"""
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
        """应用反馈调整路径。"""
        return await self.path_service.build_path_plan(
            session,
            user_id,
            resource_id=resource_id,
            feedback=feedback,
            weak_points=weak_points,
        )


# 全局实例
path_service = PathService()
path_usecases = PathUseCases(path_service)
