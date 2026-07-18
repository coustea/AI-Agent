"""资源域公共服务 — 直接使用 ORM，供 API 和工作流节点调用。

持久化 API：
- create_task: 创建资源生成任务
- publish_agent_status / publish_agent_result: 原子写入运行事实与事件
- finalize_generation: 从数据库计算终态

查询 API：
- get_resource / list_resources / count_resources
- list_resource_items / list_resource_type_summary
- get_generation_status / get_resource_bundle
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_module_logger
from app.resource.catalog import AGENT_CONTENT_FORMAT
from app.resource.events import record_resource_generated_event
from app.infra.models import (
    GeneratedResource,
    GeneratedResourceAgentRun,
    GeneratedResourceItem as ItemModel,
    GeneratedResourceRunEvent,
)
from app.resource.schemas import (
    AgentResult,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ResourceStatusSnapshot,
)
from app.resource.status import ResourceLifecycleStatus

logger = get_module_logger("resource", sub="service")


def _split_content(result: AgentResult) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    """将 AgentResult 内容拆分为 JSON 和纯文本存储字段。

    严格分流：不创建 envelope 包装，不降级非法 JSON。
    HTML/MP4 文件型资源仅在 metadata_json 中保存发布契约。
    """
    # JSON 类型：解析后存入 content_json
    if result.file_type == "json":
        value = json.loads(result.content) if isinstance(result.content, str) else result.content
        if not isinstance(value, (dict, list)):
            raise ValueError("JSON resource content must be an object or array")
        return value, None
    # 文件型（html/mp4）正文为空，引用见 metadata
    if result.file_type in {"html", "mp4"}:
        return None, None
    # 文本型：存入 content_text
    if result.file_type in {"markdown", "mermaid", "text", "code"}:
        if not isinstance(result.content, str) or not result.content.strip():
            raise ValueError("Text resource content must be non-empty")
        return None, result.content
    raise ValueError(f"Unsupported resource format: {result.file_type}")


def _item_to_dto(item: ItemModel, *, include_content: bool = True) -> GeneratedResourceItem:
    """将数据库行转换为前端资源项 DTO。

    include_content=False 时 content 为 None，用于状态轮询等轻量场景。
    content_format 由 agent_type 推导。
    """
    content_format = AGENT_CONTENT_FORMAT.get(item.agent_type, "json")

    # 按格式从数据库对应字段取回内容
    if include_content:
        if content_format == "json":
            content = item.content_json
        elif content_format in {"markdown", "mermaid", "text", "code"}:
            content = item.content_text
        elif content_format in {"html", "mp4"}:
            content = None
        else:
            content = None
    else:
        content = None

    return GeneratedResourceItem(
        id=str(item.id), type=item.agent_type,
        title=item.title,
        format=content_format, content=content,
        metadata=item.metadata_json or {},
        created_at=item.created_at.isoformat() if item.created_at else None,
    )


class ResourceService:
    """资源域公共用例，直接使用 ORM。

    窄持久化 API：创建任务、发布运行状态/产物和查询终态。
    - finalize_generation: 计算终态
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _commit(self, model: Any) -> None:
        """提交并刷新模型。"""
        try:
            # 提交事务并刷新模型，使生成的主键等字段可用
            await self.session.commit()
            await self.session.refresh(model)
        except Exception:
            # 提交失败回滚，避免悬挂事务
            await self.session.rollback()
            logger.warning("[ResourceService] 事务提交失败，已回滚")
            raise

    # =========================================================================
    # 任务创建
    # =========================================================================

    async def create_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        profile_markdown: str = "",
        username: str = "",
    ) -> dict[str, Any]:
        """创建任务。"""
        request_snapshot = {
            "schema_version": 1,
            "learning_need": request.learning_need,
            "learning_scenario": request.learning_scenario,
            "selected_agents": request.enabled_agent_ids(),
            "agent_configs": request.agent_configs.model_dump(mode="json"),
            "profile": {"markdown": profile_markdown},
            "username": username,
        }
        resource = GeneratedResource(
            user_id=user_id,
            learning_need=request.learning_need,
            request_snapshot_json=request_snapshot,
            status=ResourceLifecycleStatus.PENDING.value,
        )
        self.session.add(resource)
        await self.session.flush()
        resource_id = int(getattr(resource, "id", 0) or 0)
        # 选择集是任务的持久化事实，而不是由已执行 Agent 反推的展示结果。
        # 预先创建 pending Run 后，刷新/轮询始终能恢复所有已选 Agent（含尚未
        # 进入聚合阶段的 PPT 与 Cartoon）。
        for agent_id in request_snapshot["selected_agents"]:
            self.session.add(
                GeneratedResourceAgentRun(
                    resource_id=resource_id,
                    agent_id=agent_id,
                    status="pending",
                )
            )
        # 落库并返回新任务 ID
        await self._commit(resource)
        logger.info(
            "[ResourceService] 任务创建成功: resource_id=%s user_id=%s agents=%s",
            resource_id, user_id, request_snapshot["selected_agents"],
        )
        return {"resource_id": resource_id, "status": ResourceLifecycleStatus.PENDING.value}

    async def publish_agent_status(
        self,
        *,
        resource_id: int,
        agent_id: str,
        status: str,
        message: str,
        phase: str | None = None,
        progress: int | None = None,
        data: dict[str, Any] | None = None,
        elapsed_ms: int | None = None,
    ) -> GeneratedResourceRunEvent:
        """原子写入 Agent 当前状态和对应事件。"""
        now = datetime.now(timezone.utc)
        result = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == agent_id,
            )
        )
        run = result.one_or_none()
        if run is None:
            run = GeneratedResourceAgentRun(resource_id=resource_id, agent_id=agent_id)
            self.session.add(run)
        run.status = status
        run.phase = phase or run.phase
        run.message = message
        if progress is not None:
            run.progress = progress
        if elapsed_ms is not None:
            run.elapsed_ms = elapsed_ms
        if status == "running" and run.started_at is None:
            run.started_at = now
        run.updated_at = now

        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None:
            raise ValueError(f"资源不存在: {resource_id}")
        resource.updated_at = now
        event = GeneratedResourceRunEvent(
            resource_id=resource_id,
            agent_id=agent_id,
            event="agent.status",
            status=status,
            phase=phase,
            message=message,
            progress=progress,
            data_json=data or {},
        )
        self.session.add(event)
        await self._commit(event)
        return event

    async def publish_generation_status(
        self,
        *,
        resource_id: int,
        status: ResourceLifecycleStatus,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> GeneratedResourceRunEvent:
        """原子写入资源全局状态和任务级事件。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None:
            raise ValueError(f"资源不存在: {resource_id}")
        now = datetime.now(timezone.utc)
        resource.status = status.value
        resource.updated_at = now
        event_name = {
            ResourceLifecycleStatus.GENERATING: "generation.started",
            ResourceLifecycleStatus.COMPLETED: "generation.completed",
            ResourceLifecycleStatus.PARTIAL: "generation.completed",
            ResourceLifecycleStatus.FAILED: "generation.failed",
        }.get(status, "generation.started")
        event = GeneratedResourceRunEvent(
            resource_id=resource_id,
            event=event_name,
            status=status.value,
            phase="generation",
            message=message,
            data_json=data or {},
        )
        self.session.add(event)
        await self._commit(event)
        return event

    async def publish_planning_result(
        self,
        *,
        resource_id: int,
        plan_json: dict[str, Any],
        elapsed_ms: int,
    ) -> GeneratedResourceRunEvent:
        """原子提交结构化计划、Planning 终态与计划完成事件。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None:
            raise ValueError(f"资源不存在: {resource_id}")
        run_result = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == "planning",
            )
        )
        run = run_result.one_or_none()
        if run is None:
            raise RuntimeError("规划 Agent 缺少运行记录")
        now = datetime.now(timezone.utc)
        resource.plan_json = plan_json
        resource.updated_at = now
        run.status = "completed"
        run.phase = "plan_ready"
        run.message = "教学大纲已生成"
        run.progress = 100
        run.elapsed_ms = elapsed_ms
        run.updated_at = now
        event = GeneratedResourceRunEvent(
            resource_id=resource_id,
            agent_id="planning",
            event="agent.status",
            status="completed",
            phase="plan_ready",
            message=run.message,
            progress=100,
            data_json={"elapsed_ms": elapsed_ms},
        )
        self.session.add(event)
        await self._commit(event)
        return event

    # =========================================================================
    # Agent Result 持久化
    # =========================================================================

    async def publish_agent_result(
        self,
        *,
        resource_id: int,
        user_id: int,
        agent_id: str,
        result: AgentResult,
        elapsed_ms: int,
    ) -> tuple[ItemModel, GeneratedResourceRunEvent]:
        """以一个事务提交产物、Agent 终态与 artifact_ready 事件。"""
        if not result.success or not result.title.strip():
            raise ValueError(f"Agent {agent_id} 没有可保存的成功结果")
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")
        content_json, content_text = _split_content(result)
        item = ItemModel(
            resource_id=resource_id,
            agent_type=agent_id,
            title=result.title,
            content_json=content_json,
            content_text=content_text,
            metadata_json=result.metadata,
        )
        self.session.add(item)
        await self.session.flush()
        now = datetime.now(timezone.utc)
        run_result = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == agent_id,
            )
        )
        run = run_result.one_or_none()
        if run is None:
            raise RuntimeError(f"Agent {agent_id} 缺少运行记录")
        run.status = "completed"
        run.phase = "artifact_saved"
        run.message = f"{result.title} 已保存"
        run.progress = 100
        run.elapsed_ms = elapsed_ms
        run.updated_at = now
        resource.updated_at = now
        event = GeneratedResourceRunEvent(
            resource_id=resource_id,
            agent_id=agent_id,
            event="agent.status",
            status="completed",
            phase="artifact_saved",
            message=run.message,
            progress=100,
            data_json={"artifact_id": str(item.id), "elapsed_ms": elapsed_ms},
        )
        self.session.add(event)
        await self._commit(event)
        await self.session.refresh(item)
        logger.info(
            "[ResourceService] Agent产物保存成功: resource_id=%s agent_id=%s artifact_id=%s title=%s",
            resource_id, agent_id, str(item.id), result.title[:80],
        )
        return item, event

    async def list_run_events(
        self,
        *,
        resource_id: int,
        after_sequence: int = 0,
    ) -> list[GeneratedResourceRunEvent]:
        result = await self.session.exec(
            select(GeneratedResourceRunEvent)
            .where(GeneratedResourceRunEvent.resource_id == resource_id)
            .where(GeneratedResourceRunEvent.id > after_sequence)
            .order_by(GeneratedResourceRunEvent.id)
        )
        return list(result.all())

    async def list_resource_items(self, user_id: int, resource_id: int) -> list[ItemModel]:
        """查询资源项列表。user_id 通过 resource_id → GeneratedResource 验证所有权。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return []
        stmt = (
            select(ItemModel)
            .where(ItemModel.resource_id == resource_id)
            .order_by(col(ItemModel.id).asc())
        )
        return list((await self.session.exec(stmt)).all())

    async def list_resource_type_summary(self, user_id: int, resource_ids: list[int]) -> dict[int, list[str]]:
        if not resource_ids:
            return {}
        stmt = (
            select(ItemModel.resource_id, ItemModel.agent_type)
            .where(col(ItemModel.resource_id).in_(resource_ids))
            .order_by(col(ItemModel.resource_id).asc())
        )
        summary: dict[int, list[str]] = {rid: [] for rid in resource_ids}
        # 收集每个资源包含的 agent_type（去重）
        for rid, atype in (await self.session.exec(stmt)).all():
            if atype not in summary[rid]:
                summary[rid].append(atype)
        return summary

    # =========================================================================
    # Finalizer - 只相信数据库
    # =========================================================================

    async def finalize_generation(
        self,
        user_id: int,
        resource_id: int,
        expected_agent_ids: set[str],
    ) -> ResourceLifecycleStatus:
        """从数据库计算终态。

        不接收调用者声称的成功集合，不再次保存资源项。
        """
        logger.info(
            "[ResourceService] 终态计算开始: resource_id=%s expected_agents=%s",
            resource_id, sorted(expected_agent_ids),
        )
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")

        # 从数据库查询成功 item 的 agent_id（item 表只有成功记录）
        completed_stmt = select(ItemModel.agent_type).where(ItemModel.resource_id == resource_id)
        successful = set((await self.session.exec(completed_stmt)).all())

        # 从数据库查询失败/中断 run 的 agent_id
        failed_stmt = (
            select(GeneratedResourceAgentRun.agent_id)
            .where(GeneratedResourceAgentRun.resource_id == resource_id)
            .where(GeneratedResourceAgentRun.status.in_(["failed", "interrupted"]))
        )
        # 失败集合与预期取交集，排除非本次预期 agent
        failed = set((await self.session.exec(failed_stmt)).all()) & expected_agent_ids

        # 计算三种不一致情况用于终态判定
        unresolved = expected_agent_ids - successful - failed
        overlap = successful & failed
        unexpected = (successful | failed) - expected_agent_ids

        # 存在不一致则判为失败，否则按成功数量分流
        if unresolved or overlap or unexpected:
            logger.warning(
                "finalize_generation invariant check",
                extra={
                    "resource_id": resource_id,
                    "unresolved": sorted(unresolved),
                    "overlap": sorted(overlap),
                    "unexpected": sorted(unexpected),
                },
            )
            status = ResourceLifecycleStatus.FAILED
        elif successful == expected_agent_ids:
            status = ResourceLifecycleStatus.COMPLETED
        elif successful:
            status = ResourceLifecycleStatus.PARTIAL
        else:
            status = ResourceLifecycleStatus.FAILED

        resource.status = status.value
        await self._commit(resource)
        logger.info(
            "[ResourceService] 终态计算完成: resource_id=%s status=%s successful=%s failed=%s",
            resource_id, status.value, sorted(successful), sorted(failed),
        )
        # 记录资源生成事件供学习评估聚合（失败不影响主流程）
        try:
            await record_resource_generated_event(
                db=self.session,
                user_id=user_id,
                resource_id=resource_id,
                status=status.value,
                topic=resource.learning_need,
                agent_types=list(successful),
            )
        except Exception:
            logger.exception(
                "Failed to record resource_generated event: resource_id=%s",
                resource_id,
            )
        return status

    # =========================================================================
    # 查询
    # =========================================================================

    async def get_resource(self, user_id: int, resource_id: int) -> GeneratedResource | None:
        resource = await self.session.get(GeneratedResource, resource_id)
        # 校验归属后返回，否则视为不可见
        if resource and resource.user_id == user_id:
            return resource
        return None

    async def list_resources(self, user_id: int, limit: int = 20, offset: int = 0) -> list[GeneratedResource]:
        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(col(GeneratedResource.id).desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.exec(stmt)).all())

    async def count_resources(self, user_id: int) -> int:
        stmt = select(func.count(GeneratedResource.id)).where(GeneratedResource.user_id == user_id)
        return (await self.session.exec(stmt)).one()

    async def get_generation_status(self, user_id: int, resource_id: int) -> ResourceStatusSnapshot | None:
        """从数据库重建资源生成状态。"""
        resource = await self.get_resource(user_id, resource_id)
        if resource is None:
            return None

        db_items = await self.list_resource_items(user_id, resource_id)
        items_by_agent = {item.agent_type: item for item in db_items}

        runs_stmt = select(GeneratedResourceAgentRun).where(GeneratedResourceAgentRun.resource_id == resource_id)
        runs_result = await self.session.exec(runs_stmt)
        runs_by_agent = {run.agent_id: run for run in runs_result.all()}

        # 选择顺序是创建时冻结的请求事实，不能从成功产物反推。
        selected_agents = [
            agent_id
            for agent_id in resource.request_snapshot_json.get("selected_agents", [])
            if agent_id in AGENT_CONTENT_FORMAT
        ]

        # 构建 agent_snapshots
        merged: dict[str, dict[str, Any]] = {}
        current_message = ""
        now = datetime.now(timezone.utc)

        for agent_id, run in runs_by_agent.items():
            if agent_id in items_by_agent:
                item = items_by_agent[agent_id]
                merged[agent_id] = {
                    "agent_id": agent_id,
                    "status": "completed",
                    "message": f"{agent_id} 资源已保存",
                    "progress": 100,
                    "artifact_id": str(item.id),
                    "elapsed_ms": run.elapsed_ms,
                    "phase": run.phase,
                    "timestamp": int(run.updated_at.timestamp() * 1000) if run.updated_at else None,
                }
            else:
                message = run.message or f"{agent_id} {run.status}"
                elapsed_ms = run.elapsed_ms
                if elapsed_ms is None and run.status == "running" and run.started_at is not None:
                    elapsed_ms = max(0, int((now - run.started_at).total_seconds() * 1000))
                merged[agent_id] = {
                    "agent_id": agent_id,
                    "status": run.status,
                    "message": message,
                    "progress": run.progress,
                    "elapsed_ms": elapsed_ms,
                    "phase": run.phase,
                    "timestamp": int(run.updated_at.timestamp() * 1000) if run.updated_at else None,
                }
                if run.status == "running":
                    current_message = message

        # 兼容已有成功资源但缺少 AgentRun 的历史数据
        for agent_id, item in items_by_agent.items():
            if agent_id in merged:
                continue
            merged[agent_id] = {
                "agent_id": agent_id,
                "status": "completed",
                "message": f"{agent_id} 资源已保存",
                "progress": 100,
                "phase": "completed",
                "elapsed_ms": None,
                "artifact_id": str(item.id),
                "timestamp": int(item.created_at.timestamp() * 1000) if item.created_at else None,
            }

        return ResourceStatusSnapshot(
            resource_id=resource_id,
            learning_need=resource.learning_need,
            status=resource.status,
            selected_agents=selected_agents,
            agent_snapshots=merged,
            current_message=current_message,
            resources=[_item_to_dto(item, include_content=False) for item in db_items],
            updated_at=resource.updated_at.isoformat() if resource.updated_at else None,
        )

    async def get_resource_bundle(self, user_id: int, resource_id: int) -> ResourceBundle | None:
        resource = await self.get_resource(user_id, resource_id)
        if resource is None:
            return None
        db_items = await self.list_resource_items(user_id, resource_id)
        selected_agents = [
            agent_id
            for agent_id in resource.request_snapshot_json.get("selected_agents", [])
            if agent_id in AGENT_CONTENT_FORMAT
        ]

        # 从 agent_runs 推导 failed_agents
        failed_stmt = (
            select(GeneratedResourceAgentRun.agent_id)
            .where(GeneratedResourceAgentRun.resource_id == resource_id)
            .where(GeneratedResourceAgentRun.status.in_(["failed", "interrupted"]))
        )
        failed_agents = list((await self.session.exec(failed_stmt)).all())

        return ResourceBundle(
            id=str(resource.id), title="个性化学习资源包",
            learning_need=resource.learning_need, selected_agents=selected_agents,
            plan=resource.plan_json,
            resources=[_item_to_dto(item) for item in db_items], status=resource.status,
            created_at=resource.created_at.isoformat() if resource.created_at else "",
            updated_at=resource.updated_at.isoformat() if resource.updated_at else "",
            metadata={"failed_agents": failed_agents},
        )


__all__ = ["ResourceService"]
