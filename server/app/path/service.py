from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, LearningPath, LearningPathNode, LearningPathAdjustment
from app.memory import MemoryLayer
from app.path.planner import (
    ALL_NODE_IDS,
    adjust_plan,
    analyze_profile_dimensions,
    build_initial_plan,
    compute_progress,
    derive_next_action,
    recommend_next_nodes,
)
from app.path.profile_recommender import (
    compute_node_scores,
    compute_learning_pace,
    estimate_completion_time,
    recommend_nodes,
    suggest_path_adjustment,
)
from app.path.repository import PathRepository
from app.path.schemas import PathInsight, PathPlan, PathPlanData, PathPlanMeta, PathSummary


class PathService:
    def __init__(self, repository: PathRepository, memory_layer: MemoryLayer | None = None) -> None:
        self.repository = repository
        self.memory_layer = memory_layer or MemoryLayer(module="mentor")

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

        resource_items = await self._load_resource_items(session, user_id, resource)
        planned_node_ids = self._extract_planned_node_ids(resource, resource_items)
        inferred_weak_points = self._extract_weak_points(profile, resource, weak_points)
        completed_node_ids = await self._extract_completed_node_ids(session, user_id, resource)

        profile_info = self._parse_profile(profile)
        profile_json = profile.profile_json if profile and profile.profile_json else None
        profile_dimensions = analyze_profile_dimensions(profile_json)

        # 使用基于画像的节点评分
        node_scores = compute_node_scores(
            profile_json,
            weak_points=inferred_weak_points,
            completed_node_ids=completed_node_ids,
        )

        plan = build_initial_plan(
            knowledge_level=profile_info.get("技术能力判断"),
            learning_goal=profile_info.get("当前学习/项目背景"),
            weak_points=inferred_weak_points,
            planned_node_ids=planned_node_ids,
            profile_dimensions=profile_dimensions,
        )

        # 应用基于画像的节点评分
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

        # 保存学习路径到数据库
        await self._persist_learning_path(
            session,
            user_id,
            plan,
            profile_json,
            resource_id=resource.id if resource else None,
        )

        return self._build_response(
            plan=plan,
            profile=profile,
            resource=resource,
            resource_items=resource_items,
            force_rebuild=force_rebuild,
        )

    def _apply_profile_scores(self, plan: PathPlan, node_scores: dict[str, float]) -> PathPlan:
        """将基于画像的节点评分应用到路径规划中。"""
        updated_stages: list[Any] = []
        for stage in plan.stages:
            updated_nodes: list[Any] = []
            for node in stage.nodes:
                score = node_scores.get(node.id, node.priority)
                updated_nodes.append(node.model_copy(update={"priority": int(score)}))
            updated_stages.append(stage.model_copy(update={"nodes": updated_nodes}))
        return plan.model_copy(update={"stages": updated_stages})

    async def _resolve_resource(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int | None,
    ) -> GeneratedResource | None:
        if resource_id is not None:
            return await self.repository.get_resource_by_id(session, user_id, resource_id)
        return await self.repository.get_latest_resource(session, user_id)

    async def _persist_learning_path(
        self,
        session: AsyncSession,
        user_id: int,
        plan: PathPlan,
        profile_json: dict[str, Any] | None,
        *,
        resource_id: int | None = None,
    ) -> LearningPath | None:
        """持久化学习路径到数据库。"""
        now = datetime.now(timezone.utc)

        # 查找或创建学习路径
        existing = await self.repository.get_learning_path(session, user_id)
        if existing:
            path = existing
            path.version += 1
            path.updated_at = now
        else:
            path = LearningPath(
                user_id=user_id,
                module=self.memory_layer.module,
                created_at=now,
                updated_at=now,
            )

        # 更新路径信息
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

        # 删除旧的节点记录
        await self.repository.delete_path_nodes(session, path.id)

        # 创建新的节点记录
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
        path = await self.repository.get_learning_path(session, user_id)
        if not path:
            return None

        node = await self.repository.get_path_node(session, path.id, node_id)
        if not node:
            return None

        now = datetime.now(timezone.utc)
        updates: dict[str, Any] = {"updated_at": now}

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

        # 更新路径整体进度
        await self._recalculate_path_progress(session, path)

        return node

    async def _recalculate_path_progress(
        self,
        session: AsyncSession,
        path: LearningPath,
    ) -> None:
        """重新计算路径整体进度。"""
        nodes = await self.repository.get_path_nodes(session, path.id)
        if not nodes:
            return

        total = len(nodes)
        completed = sum(1 for n in nodes if n.status == "success")
        overall = int((completed / total) * 100) if total else 0

        # 找当前阶段
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
        path = await self.repository.get_learning_path(session, user_id)
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

        path = await self.repository.get_learning_path(session, user_id)
        completed_node_ids: set[str] = set()
        if path:
            nodes = await self.repository.get_path_nodes(session, path.id)
            completed_node_ids = {n.node_id for n in nodes if n.status == "success"}

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

    async def _load_resource_items(
        self,
        session: AsyncSession,
        user_id: int,
        resource: GeneratedResource | None,
    ) -> list[Any]:
        if resource is None or resource.id is None:
            return []
        return await self.repository.list_resource_items(session, user_id, resource.id)

    def _extract_planned_node_ids(
        self,
        resource: GeneratedResource | None,
        resource_items: list[Any],
    ) -> set[str] | None:
        candidates: list[str] = []
        selected = getattr(resource, "selected_agents", None) if resource else None
        if isinstance(selected, list):
            candidates.extend(str(item) for item in selected)
        candidates.extend(str(getattr(item, "agent_type", "")) for item in resource_items)
        node_ids = {self._normalize_node_id(item) for item in candidates}
        node_ids = {item for item in node_ids if item in ALL_NODE_IDS}
        if not node_ids:
            return None
        return node_ids

    async def _extract_completed_node_ids(
        self,
        session: AsyncSession,
        user_id: int,
        resource: GeneratedResource | None,
    ) -> set[str]:
        resource_id = resource.id if resource else None
        if resource_id is None:
            return set()
        return await self.repository.list_completed_node_ids_from_events(session, user_id, resource_id)

    def _extract_weak_points(
        self,
        profile: Any | None,
        resource: GeneratedResource | None,
        extra_weak_points: list[str] | None,
    ) -> list[str]:
        texts: list[str] = []
        if profile and profile.profile_json:
            profile_info = self._parse_profile(profile)
            if profile_info.get("当前薄弱点"):
                texts.append(profile_info["当前薄弱点"])
        if resource and resource.learning_need:
            texts.append(resource.learning_need)
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
            "图解": "diagram",
            "图表": "diagram",
            "表达": "content",
            "讲解": "content",
        }

        inferred: list[str] = []
        for keyword, node_id in keyword_mapping.items():
            if keyword in merged_text:
                inferred.append(node_id)

        for node_id in (extra_weak_points or []):
            if node_id in ALL_NODE_IDS:
                inferred.append(node_id)

        if not inferred and profile:
            profile_info = self._parse_profile(profile)
            goal = (profile_info.get("当前学习/项目背景") or "").lower()
            if "exam" in goal or "考试" in goal:
                inferred.append("quiz")
            if "project" in goal or "项目" in goal:
                inferred.append("code")

        ordered = [node_id for node_id in ALL_NODE_IDS if node_id in set(inferred)]
        return ordered

    def _parse_profile(self, profile) -> dict[str, str]:
        """从 JSON 画像中提取学习路径规划需要的关键信息。"""
        result: dict[str, str] = {}
        if not profile or not profile.profile_json:
            return result

        dimensions = profile.profile_json.get("dimensions", {})
        student_profile = profile.profile_json.get("student_profile") or {}
        result["技术能力判断"] = dimensions.get("knowledge_foundation", {}).get("summary") or ""
        result["当前学习/项目背景"] = dimensions.get("learning_goal", {}).get("summary") or ""
        result["学习偏好"] = dimensions.get("interaction_preference", {}).get("summary") or ""
        result["当前薄弱点"] = dimensions.get("weakness_points", {}).get("summary") or ""
        result["兴趣方向"] = student_profile.get("current_focus", [])
        if isinstance(result["兴趣方向"], list):
            result["兴趣方向"] = ", ".join(result["兴趣方向"])
        return result

    def _compute_confidence(
        self,
        profile: Any | None,
        resource: GeneratedResource | None,
        has_resource_items: bool,
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
        if has_resource_items:
            score += 10
        if completed_node_ids:
            score += 4

        return max(30, min(score, 95))

    def _build_response(
        self,
        *,
        plan: PathPlan,
        profile: Any | None,
        resource: GeneratedResource | None,
        resource_items: list[Any],
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

    def _attach_resource_items(
        self,
        plan: PathPlan,
        resource: GeneratedResource | None,
        resource_items: list[Any],
    ) -> PathPlan:
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
                    nodes.append(
                        node.model_copy(
                            update={
                                "resource_id": resource_id,
                                "resource_type": node.id,
                                "resource_status": "missing" if resource_id is not None else None,
                            }
                        )
                    )
                    continue

                content_json = getattr(item, "content_json", None)
                if not isinstance(content_json, dict):
                    content_json = {}
                resource_status = self._resource_item_status(item)
                nodes.append(
                    node.model_copy(
                        update={
                            "resource_id": resource_id,
                            "resource_item_id": getattr(item, "id", None),
                            "resource_type": node.id,
                            "resource_title": content_json.get("title") or node.title,
                            "resource_summary": content_json.get("summary") or getattr(item, "content_text", None),
                            "resource_format": content_json.get("format") or getattr(item, "content_format", None),
                            "resource_status": resource_status,
                        }
                    )
                )
            stages.append(stage.model_copy(update={"nodes": nodes}))
        return plan.model_copy(update={"stages": stages})

    def _attach_recommendation_reasons(
        self,
        plan: PathPlan,
        profile_dimensions: dict[str, dict],
    ) -> PathPlan:
        recommendations = recommend_next_nodes(
            plan,
            top_n=len(ALL_NODE_IDS),
            profile_dimensions=profile_dimensions,
        )
        reason_map = {item["node_id"]: item["reason"] for item in recommendations}
        stages = []
        for stage in plan.stages:
            nodes = [
                node.model_copy(
                    update={
                        "recommendation_reason": reason_map.get(
                            node.id,
                            node.recommendation_reason or f"根据学习路径规划，建议完成「{node.title}」",
                        )
                    }
                )
                for node in stage.nodes
            ]
            stages.append(stage.model_copy(update={"nodes": nodes}))
        return plan.model_copy(update={"stages": stages})

    def _resource_item_status(self, item: Any) -> str:
        status = str(getattr(item, "status", "") or "").lower()
        if status == "failed":
            return "failed"
        if status in {"pending", "running"}:
            return "pending"
        if status == "completed" and self._resource_item_has_content(item):
            return "available"
        return "missing"

    def _resource_item_has_content(self, item: Any) -> bool:
        content_json = getattr(item, "content_json", None)
        content_text = getattr(item, "content_text", None)
        if isinstance(content_json, dict) and content_json:
            content = content_json.get("content")
            return content not in (None, "", {}, [])
        if isinstance(content_text, str):
            return bool(content_text.strip())
        return False

    def _normalize_node_id(self, raw: str) -> str:
        node_id = (raw or "").strip().lower()
        aliases = {
            "image": "diagram",
            "chart": "diagram",
            "flowchart": "diagram",
            "ppt": "content",
            "video": "content",
        }
        return aliases.get(node_id, node_id)


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
