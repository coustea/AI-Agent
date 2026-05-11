"""Path planning repository.

提供学习路径规划相关的数据库访问操作，包括：
- 学习路径的持久化存储
- 路径节点的状态管理
- 调整记录的历史追踪
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import (
    GeneratedResource,
    GeneratedResourceItem,
    LearningEvent,
    LearningPath,
    LearningPathNode,
    LearningPathAdjustment,
)
from app.path.planner import ALL_NODE_IDS
from app.path.schemas import PathPlan


class PathRepository:
    """学习路径数据访问层。"""

    async def get_latest_resource(
        self, session: AsyncSession, user_id: int
    ) -> GeneratedResource | None:
        """获取用户最新的生成资源。"""
        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(GeneratedResource.created_at.desc())
            .limit(1)
        )
        result = await session.exec(stmt)
        return result.first()

    async def get_resource_by_id(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ) -> GeneratedResource | None:
        """根据 ID 获取生成资源。"""
        resource = await session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return None
        return resource

    async def list_resource_items(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int,
    ) -> list[GeneratedResourceItem]:
        """列出指定资源包下的资源项。"""
        stmt = (
            select(GeneratedResourceItem)
            .where(GeneratedResourceItem.user_id == user_id)
            .where(GeneratedResourceItem.resource_id == resource_id)
            .order_by(GeneratedResourceItem.created_at.asc(), GeneratedResourceItem.id.asc())
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def list_completed_node_ids_from_events(
        self,
        session: AsyncSession,
        user_id: int,
        resource_id: int | None,
    ) -> set[str]:
        """从学习行为事件中提取已完成路径节点。"""
        stmt = select(LearningEvent).where(LearningEvent.user_id == user_id)
        if resource_id is not None:
            stmt = stmt.where(LearningEvent.resource_id == resource_id)
        stmt = stmt.order_by(LearningEvent.created_at.desc()).limit(200)
        result = await session.exec(stmt)

        completed: set[str] = set()
        for event in result.all():
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
                if event.event_type in {"resource_completed", "node_completed", "quiz_submitted"} and node_id in ALL_NODE_IDS:
                    completed.add(node_id)
        return completed

    async def get_learning_path(
        self,
        session: AsyncSession,
        user_id: int,
        module: str = "mentor",
    ) -> LearningPath | None:
        """获取用户的当前学习路径。"""
        stmt = (
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .where(LearningPath.module == module)
            .where(LearningPath.is_active == True)
        )
        result = await session.exec(stmt)
        return result.first()

    async def get_or_create_learning_path(
        self,
        session: AsyncSession,
        user_id: int,
        module: str = "mentor",
    ) -> LearningPath:
        """获取或创建用户的学习路径。"""
        path = await self.get_learning_path(session, user_id, module)
        if path:
            return path

        path = LearningPath(
            user_id=user_id,
            module=module,
            is_active=True,
        )
        session.add(path)
        await session.commit()
        await session.refresh(path)
        return path

    async def get_path_nodes(
        self,
        session: AsyncSession,
        path_id: int,
    ) -> list[LearningPathNode]:
        """获取路径的所有节点。"""
        stmt = (
            select(LearningPathNode)
            .where(LearningPathNode.path_id == path_id)
            .order_by(LearningPathNode.stage_id, LearningPathNode.priority.desc())
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def get_node_by_id(
        self,
        session: AsyncSession,
        path_id: int,
        node_id: str,
    ) -> LearningPathNode | None:
        """根据节点 ID 获取路径节点。"""
        stmt = (
            select(LearningPathNode)
            .where(LearningPathNode.path_id == path_id)
            .where(LearningPathNode.node_id == node_id)
        )
        result = await session.exec(stmt)
        return result.first()

    async def get_path_node(
        self,
        session: AsyncSession,
        path_id: int,
        node_id: str,
    ) -> LearningPathNode | None:
        """获取单个路径节点（别名方法）。"""
        return await self.get_node_by_id(session, path_id, node_id)

    async def delete_path_nodes(
        self,
        session: AsyncSession,
        path_id: int,
    ) -> int:
        """删除路径的所有节点。"""
        nodes = await self.get_path_nodes(session, path_id)
        count = 0
        for node in nodes:
            await session.delete(node)
            count += 1
        await session.commit()
        return count

    async def create_or_update_path_nodes(
        self,
        session: AsyncSession,
        path_id: int,
        user_id: int,
        plan: PathPlan,
    ) -> list[LearningPathNode]:
        """根据路径计划创建或更新节点。"""
        existing_nodes = await self.get_path_nodes(session, path_id)
        existing_map = {n.node_id: n for n in existing_nodes}

        nodes: list[LearningPathNode] = []
        now = datetime.now(timezone.utc)

        for stage in plan.stages:
            for node in stage.nodes:
                if node.id in existing_map:
                    # 更新现有节点
                    existing = existing_map[node.id]
                    existing.priority = node.priority
                    existing.status = node.status
                    existing.progress = node.progress
                    existing.title = node.title
                    existing.updated_at = now
                    if node.status == "success" and existing.completed_at is None:
                        existing.completed_at = now
                    if node.status == "processing" and existing.started_at is None:
                        existing.started_at = now
                    nodes.append(existing)
                else:
                    # 创建新节点
                    new_node = LearningPathNode(
                        path_id=path_id,
                        user_id=user_id,
                        node_id=node.id,
                        stage_id=stage.id,
                        title=node.title,
                        status=node.status,
                        progress=node.progress,
                        priority=node.priority,
                        recommendation_reason=node.desc,
                    )
                    session.add(new_node)
                    nodes.append(new_node)

        await session.commit()
        for node in nodes:
            await session.refresh(node)
        return nodes

    async def update_node_status(
        self,
        session: AsyncSession,
        path_id: int,
        node_id: str,
        status: str,
        progress: int | None = None,
        resource_id: int | None = None,
    ) -> LearningPathNode | None:
        """更新节点状态。"""
        node = await self.get_node_by_id(session, path_id, node_id)
        if not node:
            return None

        now = datetime.now(timezone.utc)
        node.status = status
        node.updated_at = now

        if progress is not None:
            node.progress = progress

        if status == "processing" and node.started_at is None:
            node.started_at = now

        if status == "success":
            node.progress = 100
            node.completed_at = now

        if resource_id is not None:
            node.resource_id = resource_id

        await session.commit()
        await session.refresh(node)
        return node

    async def update_path_progress(
        self,
        session: AsyncSession,
        path_id: int,
        overall_progress: int,
        current_stage_id: str | None = None,
        current_node_id: str | None = None,
        eta_days: int | None = None,
        confidence: int | None = None,
    ) -> LearningPath | None:
        """更新路径进度。"""
        path = await session.get(LearningPath, path_id)
        if not path:
            return None

        now = datetime.now(timezone.utc)
        path.overall_progress = overall_progress
        path.updated_at = now

        if current_stage_id is not None:
            path.current_stage_id = current_stage_id
        if current_node_id is not None:
            path.current_node_id = current_node_id
        if eta_days is not None:
            path.eta_days = eta_days
        if confidence is not None:
            path.confidence = confidence

        await session.commit()
        await session.refresh(path)
        return path

    async def save_path_plan(
        self,
        session: AsyncSession,
        user_id: int,
        plan: PathPlan,
        module: str = "mentor",
        profile_snapshot: dict[str, Any] | None = None,
    ) -> LearningPath:
        """保存完整的路径计划。"""
        path = await self.get_or_create_learning_path(session, user_id, module)

        now = datetime.now(timezone.utc)
        path.knowledge_level = plan.knowledge_level
        path.learning_goal = plan.learning_goal
        path.overall_progress = plan.progress.overall
        path.current_stage_id = plan.progress.current_stage_id
        path.eta_days = plan.progress.eta_days
        path.confidence = plan.progress.confidence
        path.version = plan.version
        path.updated_at = now

        if profile_snapshot:
            path.profile_snapshot = profile_snapshot

        await session.commit()
        await session.refresh(path)

        # 创建或更新节点
        await self.create_or_update_path_nodes(session, path.id, user_id, plan)

        return path

    async def create_adjustment_record(
        self,
        session: AsyncSession,
        path_id: int,
        user_id: int,
        adjustment_type: str,
        reason: str,
        impacted_node_ids: list[str] | None = None,
        before_snapshot: dict[str, Any] | None = None,
        after_snapshot: dict[str, Any] | None = None,
    ) -> LearningPathAdjustment:
        """创建调整记录。"""
        adjustment = LearningPathAdjustment(
            path_id=path_id,
            user_id=user_id,
            adjustment_type=adjustment_type,
            reason=reason,
            impacted_node_ids=impacted_node_ids,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        session.add(adjustment)
        await session.commit()
        await session.refresh(adjustment)
        return adjustment

    async def get_adjustment_history(
        self,
        session: AsyncSession,
        path_id: int,
        limit: int = 20,
    ) -> list[LearningPathAdjustment]:
        """获取调整历史记录。"""
        stmt = (
            select(LearningPathAdjustment)
            .where(LearningPathAdjustment.path_id == path_id)
            .order_by(LearningPathAdjustment.created_at.desc())
            .limit(limit)
        )
        result = await session.exec(stmt)
        return list(result.all())

    async def deactivate_path(
        self,
        session: AsyncSession,
        path_id: int,
    ) -> bool:
        """停用学习路径。"""
        path = await session.get(LearningPath, path_id)
        if not path:
            return False

        path.is_active = False
        path.updated_at = datetime.now(timezone.utc)
        await session.commit()
        return True

    async def get_completed_node_ids(
        self,
        session: AsyncSession,
        user_id: int,
        module: str = "mentor",
    ) -> set[str]:
        """获取用户已完成的节点 ID 集合。"""
        path = await self.get_learning_path(session, user_id, module)
        if not path:
            return set()

        nodes = await self.get_path_nodes(session, path.id)
        return {n.node_id for n in nodes if n.status == "success"}

    async def get_path_node(
        self,
        session: AsyncSession,
        path_id: int,
        node_id: str,
    ) -> LearningPathNode | None:
        """获取路径中的特定节点。"""
        stmt = (
            select(LearningPathNode)
            .where(LearningPathNode.path_id == path_id)
            .where(LearningPathNode.node_id == node_id)
        )
        result = await session.exec(stmt)
        return result.first()

    async def delete_path_nodes(
        self,
        session: AsyncSession,
        path_id: int,
    ) -> int:
        """删除路径中的所有节点。"""
        from sqlmodel import delete
        stmt = delete(LearningPathNode).where(LearningPathNode.path_id == path_id)
        result = await session.exec(stmt)
        return result.rowcount if hasattr(result, "rowcount") else 0
