"""资源域公共服务 — 直接使用 ORM，供 API 和兄弟模块调用。

重构说明（v4）：
- split_content() 替代 _content_envelope()，严格分流
- 窄持久化 API：create_task, save_teaching_plan, start_agent_run, save_agent_result,
  complete_agent_run, mark_agent_failed, finalize_generation
- finalizer 只相信数据库状态
- 不创建 fallback、placeholder 或默认内容
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_module_logger
from app.infra.models import GeneratedResource, GeneratedResourceAgentRun, GeneratedResourceItem as ItemModel
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    TeachingPlan,
)

logger = get_module_logger("resource", sub="service")

# Agent ID 常量
PPT_AGENT_ID = "ppt"
COORDINATOR_AGENT_ID = "coordinator"
VIDEO_AGENT_ID = "video"
BUNDLE_AGENT_ID = "bundle"
AGGREGATION_AGENT_IDS = (PPT_AGENT_ID, VIDEO_AGENT_ID)
STANDALONE_RESOURCE_SOURCES = ("standalone", "single_agent")


def split_content(result: AgentResult) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    """将 AgentResult 内容拆分为 JSON 和纯文本存储字段。

    严格分流：不创建 envelope 包装，不降级非法 JSON。
    """
    if result.file_type == "json":
        value = json.loads(result.content) if isinstance(result.content, str) else result.content
        if not isinstance(value, (dict, list)):
            raise ValueError("JSON resource content must be an object or array")
        return value, None
    if result.file_type in {"markdown", "mermaid", "text", "code"}:
        if not isinstance(result.content, str) or not result.content.strip():
            raise ValueError("Text resource content must be non-empty")
        return None, result.content
    raise ValueError(f"Unsupported resource format: {result.file_type}")


def _db_item_to_dto(item: ItemModel) -> GeneratedResourceItem:
    """将数据库行转换为前端资源项 DTO。

    按 content_format 读取 content_json 或 content_text，不猜测旧 envelope。
    """
    if not item.title or not item.content_format:
        raise ValueError(f"资源项 {item.id} 缺少标题或格式")
    if item.content_format == "json":
        if item.content_json is None:
            raise ValueError(f"资源项 {item.id} JSON 格式但 content_json 为空")
        content = item.content_json
    elif item.content_format in {"markdown", "mermaid", "text", "code"}:
        if not item.content_text:
            raise ValueError(f"资源项 {item.id} 文本格式但 content_text 为空")
        content = item.content_text
    else:
        raise ValueError(f"资源项 {item.id} 不支持的格式: {item.content_format}")
    return GeneratedResourceItem(
        id=str(item.id), type=item.agent_type,
        title=item.title,
        format=item.content_format, content=content,
        summary=item.summary or "", metrics=item.metrics or {},
        downstream_context=DownstreamContext.model_validate(item.downstream_context) if isinstance(item.downstream_context, dict) else None,
        execution_report=item.execution_report, metadata=item.metadata_json or {},
        status=item.status, error_message=item.error_message,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


class ResourceService:
    """资源域公共用例，直接使用 ORM。

    窄持久化 API：
    - create_task: 创建任务并保存 request/profile 快照
    - save_teaching_plan: 保存计划并创建 pending agent runs
    - start_agent_run: 将 run 从 pending 改为 running
    - save_agent_result: 插入成功 item
    - complete_agent_run: 将 run 改为 completed
    - mark_agent_failed: 写 failed/interrupted
    - finalize_generation: 锁父记录并计算终态
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _commit(self, model: Any) -> None:
        """提交并刷新模型。"""
        try:
            await self.session.commit()
            await self.session.refresh(model)
        except Exception:
            await self.session.rollback()
            raise

    # =========================================================================
    # 任务创建与快照
    # =========================================================================

    async def create_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        profile_snapshot: dict[str, Any] | None = None,
        source: str = "standalone",
    ) -> dict[str, Any]:
        """创建任务并保存 request/profile 快照。"""
        resource = GeneratedResource(
            user_id=user_id,
            learning_need=request.learning_need,
            selected_agents=request.enabled_agent_ids(),
            agent_configs=request.agent_configs.model_dump(mode="json"),
            request_snapshot=request.model_dump(mode="json"),
            profile_snapshot=profile_snapshot,
            source=source,
            status="pending",
        )
        self.session.add(resource)
        await self.session.flush()
        resource_id = int(getattr(resource, "id", 0) or 0)
        await self._commit(resource)
        return {"resource_id": resource_id, "status": "pending", "source": source}

    async def claim_task(self, resource_id: int, run_id: str) -> bool:
        """原子认领：将父任务从 pending 改为 generating 并设置 run_id。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.status != "pending":
            return False
        resource.status = "generating"
        resource.run_id = run_id
        resource.started_at = datetime.now(timezone.utc)
        resource.heartbeat_at = datetime.now(timezone.utc)
        await self._commit(resource)
        return True

    # =========================================================================
    # Teaching Plan 持久化
    # =========================================================================

    async def save_teaching_plan(
        self,
        *,
        user_id: int,
        resource_id: int,
        run_id: str,
        teaching_plan: TeachingPlan,
    ) -> None:
        """校验 owner 后保存计划、完成 planning run，并为每个所选 Agent 创建 pending run。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")
        resource.teaching_plan = teaching_plan.model_dump(mode="json")
        await self._commit(resource)

        # 完成 planning run
        planning_run = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == "planning",
            )
        )
        planning_run_obj = planning_run.one_or_none()
        if planning_run_obj:
            planning_run_obj.status = "completed"
            planning_run_obj.finished_at = datetime.now(timezone.utc)
            await self._commit(planning_run_obj)

        # 为每个非 Planning Agent 创建 pending run
        selected = resource.selected_agents or []
        for agent_id in selected:
            if agent_id == "planning":
                continue
            run = GeneratedResourceAgentRun(
                resource_id=resource_id,
                run_id=run_id,
                agent_id=agent_id,
                stage="pending",
                status="pending",
            )
            self.session.add(run)
        await self.session.commit()

    # =========================================================================
    # Agent Run 生命周期
    # =========================================================================

    async def start_agent_run(
        self,
        *,
        resource_id: int,
        run_id: str,
        agent_id: str,
        stage: str,
    ) -> None:
        """将唯一 run 从 pending 改为 running。"""
        run = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == agent_id,
            )
        )
        run_obj = run.one_or_none()
        if run_obj and run_obj.status == "pending":
            run_obj.status = "running"
            run_obj.stage = stage
            run_obj.started_at = datetime.now(timezone.utc)
            await self._commit(run_obj)

    async def complete_agent_run(
        self,
        *,
        resource_id: int,
        agent_id: str,
        elapsed_ms: int | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """将 run 改为 completed。"""
        run = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == agent_id,
            )
        )
        run_obj = run.one_or_none()
        if run_obj:
            run_obj.status = "completed"
            run_obj.finished_at = datetime.now(timezone.utc)
            run_obj.elapsed_ms = elapsed_ms
            run_obj.metrics = metrics
            await self._commit(run_obj)

    async def mark_agent_failed(
        self,
        *,
        resource_id: int,
        run_id: str,
        agent_id: str,
        stage: str,
        error_type: str,
        error_message: str,
        elapsed_ms: int | None = None,
    ) -> None:
        """写 failed/interrupted run 记录。不创建 item。"""
        run = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == agent_id,
            )
        )
        run_obj = run.one_or_none()
        if run_obj:
            run_obj.status = "failed"
            run_obj.stage = stage
            run_obj.error_type = error_type
            run_obj.error_message = error_message
            run_obj.finished_at = datetime.now(timezone.utc)
            run_obj.elapsed_ms = elapsed_ms
            await self._commit(run_obj)
        else:
            # 创建新的 failed run
            new_run = GeneratedResourceAgentRun(
                resource_id=resource_id,
                run_id=run_id,
                agent_id=agent_id,
                stage=stage,
                status="failed",
                error_type=error_type,
                error_message=error_message,
                finished_at=datetime.now(timezone.utc),
                elapsed_ms=elapsed_ms,
            )
            self.session.add(new_run)
            await self._commit(new_run)

    # =========================================================================
    # Agent Result 持久化
    # =========================================================================

    async def save_agent_result(
        self,
        *,
        resource_id: int,
        user_id: int,
        agent_id: str,
        result: AgentResult,
        source_item_ids: list[int] | None = None,
        depends_on_agents: list[str] | None = None,
    ) -> ItemModel:
        """保存成功 Agent 的结果。先校验，再插入 item。"""
        if not result.success:
            raise ValueError("仅能保存成功的结果")
        if not result.title.strip() or not result.file_type.strip():
            raise ValueError(f"Agent {agent_id} 缺少资源标题或格式")

        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")
        if agent_id not in (resource.selected_agents or []):
            raise ValueError(f"Agent {agent_id} 不在已选择的 Agent 列表中")

        # 身份校验
        metadata_agent_id = result.metadata.get("agent_id") if result.metadata else None
        if metadata_agent_id != agent_id:
            raise ValueError(
                f"Agent 结果身份不匹配: scheduled={agent_id!r} metadata={metadata_agent_id!r}"
            )

        # 校验 source_item_ids
        if source_item_ids:
            valid_ids = set()
            for sid in source_item_ids:
                item = await self.session.get(ItemModel, sid)
                if item and item.resource_id == resource_id:
                    valid_ids.add(sid)
            if len(valid_ids) != len(source_item_ids):
                raise ValueError(f"source_item_ids 包含无效或不属于当前资源的 ID")

        # 校验依赖
        dependencies = list(dict.fromkeys(depends_on_agents or []))
        if agent_id in dependencies:
            raise ValueError(f"Agent {agent_id} 不能依赖自身")
        if dependencies:
            stmt = (
                select(ItemModel.agent_type)
                .where(ItemModel.resource_id == resource_id)
                .where(ItemModel.user_id == user_id)
                .where(ItemModel.status == "completed")
                .where(col(ItemModel.agent_type).in_(dependencies))
            )
            persisted = set((await self.session.exec(stmt)).all())
            missing = set(dependencies) - persisted
            if missing:
                raise ValueError(
                    f"Agent 依赖尚未成功持久化: agent_id={agent_id!r} missing={sorted(missing)}"
                )

        # 使用 split_content 进行严格分流
        content_json, content_text = split_content(result)

        # 从 metadata 提取文件路径
        output_file_path = result.metadata.get("output_file_path") if result.metadata else None
        json_file_path = result.metadata.get("json_file_path") if result.metadata else None
        audio_file_paths = result.metadata.get("audio_file_paths") if result.metadata else None

        item = ItemModel(
            resource_id=resource_id,
            user_id=user_id,
            agent_type=agent_id,
            content_format=result.file_type,
            title=result.title,
            summary=result.summary,
            generated_by=agent_id,
            content_json=content_json,
            content_text=content_text,
            metadata_json=result.metadata,
            metrics=result.metrics,
            downstream_context=result.downstream_context.model_dump(mode="json") if result.downstream_context else None,
            output_file_path=output_file_path,
            json_file_path=json_file_path,
            audio_file_paths=audio_file_paths,
            depends_on_agents=dependencies or None,
            source_item_ids=source_item_ids,
            status="completed",
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(item)
        await self._commit(item)
        return item

    async def list_resource_items(self, user_id: int, resource_id: int) -> list[ItemModel]:
        stmt = select(ItemModel).where(ItemModel.user_id == user_id).where(ItemModel.resource_id == resource_id).order_by(col(ItemModel.id).asc())
        return list((await self.session.exec(stmt)).all())

    async def list_resource_type_summary(self, user_id: int, resource_ids: list[int]) -> dict[int, list[str]]:
        if not resource_ids:
            return {}
        stmt = select(ItemModel.resource_id, ItemModel.agent_type).where(ItemModel.user_id == user_id).where(col(ItemModel.resource_id).in_(resource_ids)).order_by(col(ItemModel.resource_id).asc())
        summary: dict[int, list[str]] = {rid: [] for rid in resource_ids}
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
    ) -> str:
        """锁父记录并从数据库计算终态。

        不接收调用者声称的成功集合，不再次保存资源项。
        """
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")

        # 从数据库查询成功 item
        successful = set(await self.get_completed_agent_ids(resource_id))
        # 从数据库查询失败/中断 run
        failed = set(await self.get_failed_agent_ids(resource_id))

        unresolved = expected_agent_ids - successful - failed
        overlap = successful & failed
        unexpected = (successful | failed) - expected_agent_ids

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
            status = "failed"
        elif successful == expected_agent_ids:
            status = "completed"
        elif successful:
            status = "partial_completed"
        else:
            status = "failed"

        # 更新父记录
        resource.status = status
        resource.failed_agents = sorted(expected_agent_ids - successful)
        resource.finished_at = datetime.now(timezone.utc)
        resource.updated_at = datetime.now(timezone.utc)
        await self._commit(resource)
        return status

    async def update_resource_status(self, resource_id: int, status: str) -> None:
        """更新资源任务状态。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource:
            resource.status = status
            resource.updated_at = datetime.now(timezone.utc)
            await self._commit(resource)

    async def get_completed_agent_ids(self, resource_id: int) -> list[str]:
        """获取已完成 item 的 agent_id 列表。"""
        stmt = (
            select(ItemModel.agent_type)
            .where(ItemModel.resource_id == resource_id)
            .where(ItemModel.status == "completed")
        )
        return list((await self.session.exec(stmt)).all())

    async def get_failed_agent_ids(self, resource_id: int) -> list[str]:
        """获取失败/中断 run 的 agent_id 列表。"""
        stmt = (
            select(GeneratedResourceAgentRun.agent_id)
            .where(GeneratedResourceAgentRun.resource_id == resource_id)
            .where(GeneratedResourceAgentRun.status.in_(["failed", "interrupted"]))
        )
        return list((await self.session.exec(stmt)).all())

    async def get_resource(self, user_id: int, resource_id: int, *, allowed_sources: tuple[str, ...] | None = None) -> GeneratedResource | None:
        resource = await self.session.get(GeneratedResource, resource_id)
        if (
            resource
            and resource.user_id == user_id
            and (allowed_sources is None or resource.source in allowed_sources)
        ):
            return resource
        return None

    async def list_resources(self, user_id: int, limit: int = 20, offset: int = 0, *, sources: tuple[str, ...] | None = None) -> list[GeneratedResource]:
        stmt = select(GeneratedResource).where(GeneratedResource.user_id == user_id)
        if sources:
            stmt = stmt.where(col(GeneratedResource.source).in_(sources))
        stmt = stmt.order_by(col(GeneratedResource.id).desc()).offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_resources(self, user_id: int, *, sources: tuple[str, ...] | None = None) -> int:
        stmt = select(func.count(GeneratedResource.id)).where(GeneratedResource.user_id == user_id)
        if sources:
            stmt = stmt.where(col(GeneratedResource.source).in_(sources))
        return (await self.session.exec(stmt)).one()

    async def get_generation_status(self, user_id: int, resource_id: int, *, allowed_sources: tuple[str, ...] | None = None) -> dict[str, Any] | None:
        """从数据库重建资源生成状态。

        优先级：数据库 > event_bus snapshot
        返回已完成 items、运行中/失败的 agent runs 状态。
        """
        resource = await self.get_resource(user_id, resource_id, allowed_sources=allowed_sources)
        if resource is None:
            return None

        # 从数据库读取成功 items
        db_items = await self.list_resource_items(user_id, resource_id)
        items_by_agent = {item.agent_type: item for item in db_items}

        # 从数据库读取 agent runs 状态
        runs_stmt = (
            select(GeneratedResourceAgentRun)
            .where(GeneratedResourceAgentRun.resource_id == resource_id)
        )
        runs_result = await self.session.exec(runs_stmt)
        runs_by_agent = {run.agent_id: run for run in runs_result.all()}

        # 构建 agent_snapshots：数据库状态优先
        merged: dict[str, dict[str, Any]] = {}
        selected_agents = list(resource.selected_agents or [])

        for agent_id in selected_agents:
            # 成功 item 优先
            if agent_id in items_by_agent:
                item = items_by_agent[agent_id]
                merged[agent_id] = {
                    "event_type": "agent.artifact_ready",
                    "agent_id": agent_id,
                    "status": "finished",
                    "message": f"{agent_id} 资源已保存",
                    "progress": 100,
                    "phase": "artifact_saved",
                    "artifact_id": str(item.id),
                }
            # 否则查看 run 状态
            elif agent_id in runs_by_agent:
                run = runs_by_agent[agent_id]
                merged[agent_id] = {
                    "event_type": f"agent.{run.status}",
                    "agent_id": agent_id,
                    "status": run.status,
                    "message": run.error_message or f"{agent_id} {run.status}",
                    "progress": 100 if run.status == "completed" else 0,
                    "phase": run.stage,
                }

        return {
            "resource_id": resource_id,
            "status": resource.status,
            "selected_agents": selected_agents,
            "agent_snapshots": merged,
            "current_message": "",
            "resources": [_db_item_to_dto(item).model_dump(mode="json") for item in db_items],
        }

    async def get_resource_bundle(self, user_id: int, resource_id: int, *, allowed_sources: tuple[str, ...] | None = None) -> ResourceBundle | None:
        resource = await self.get_resource(user_id, resource_id, allowed_sources=allowed_sources)
        if resource is None:
            return None
        db_items = await self.list_resource_items(user_id, resource_id)
        return ResourceBundle(
            id=str(resource.id), task_id=str(resource.id), title="个性化学习资源包",
            learning_need=resource.learning_need or "", selected_agents=resource.selected_agents or [],
            resources=[_db_item_to_dto(item) for item in db_items], status=resource.status,
            created_at=resource.created_at.isoformat() if resource.created_at else "",
            updated_at=resource.updated_at.isoformat() if resource.updated_at else "",
            metadata={"source": "database", "failed_agents": resource.failed_agents or [], "teaching_plan": resource.teaching_plan or {}},
        )


__all__ = ["ResourceService"]
