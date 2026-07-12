"""资源域公共服务 — 直接使用 ORM，供 API 和工作流节点调用。

持久化 API：
- create_task: 创建资源生成任务
- upsert_agent_run: Agent 运行状态 upsert
- save_agent_result: 保存 Agent 生成内容
- finalize_generation: 从数据库计算终态
- update_resource_status: 更新任务状态

查询 API：
- get_resource / list_resources / count_resources
- list_resource_items / list_resource_type_summary
- get_generation_status / get_resource_bundle
"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_module_logger
from app.resource.events import record_resource_generated_event
from app.infra.models import GeneratedResource, GeneratedResourceAgentRun, GeneratedResourceItem as ItemModel
from app.resource.schemas import (
    AgentResult,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ResourceStatusSnapshot,
)

logger = get_module_logger("resource", sub="service")

# Agent ID 常量
PPT_AGENT_ID = "ppt"
COORDINATOR_AGENT_ID = "coordinator"
CARTOON_AGENT_ID = "cartoon"
BUNDLE_AGENT_ID = "bundle"
# 基础资源 Agent（为聚合 Agent 提供素材）
BASE_RESOURCE_AGENT_IDS = frozenset({"content", "mindmap", "quiz", "code", "reading"})
# 聚合型 Agent（依赖基础资源）
AGGREGATION_AGENT_IDS = (PPT_AGENT_ID, CARTOON_AGENT_ID)

# agent_type → content_format 映射（不再存 content_format 列）
# 不同 Agent 产物的存储格式：json/html/mp4/markdown
AGENT_CONTENT_FORMAT: dict[str, str] = {
    "content": "markdown",
    "mindmap": "markdown",
    "code": "markdown",
    "quiz": "json",
    "reading": "json",
    "ppt": "html",
    "cartoon": "mp4",
}


def _infer_content_format(agent_type: str) -> str:
    """从 agent_type 推导 content_format。"""
    return AGENT_CONTENT_FORMAT.get(agent_type, "json")


def _split_content(result: AgentResult) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    """将 AgentResult 内容拆分为 JSON 和纯文本存储字段。

    严格分流：不创建 envelope 包装，不降级非法 JSON。
    HTML/MP4 文件型资源仅在 metadata_json 中保存发布引用。
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
    content_format = _infer_content_format(item.agent_type)

    # 按格式从数据库对应字段取回内容
    if include_content:
        if content_format == "json":
            content = item.content_json
        elif content_format in {"markdown", "mermaid", "text", "code"}:
            content = item.content_text
        elif content_format in {"html", "mp4"}:
            content = item.metadata_json or {}
        else:
            content = None
    else:
        content = None

    return GeneratedResourceItem(
        id=str(item.id), type=item.agent_type,
        title=item.title or "",
        format=content_format, content=content,
        metadata=item.metadata_json or {},
        created_at=item.created_at.isoformat() if item.created_at else None,
    )


class ResourceService:
    """资源域公共用例，直接使用 ORM。

    窄持久化 API：
    - create_task: 创建任务
    - save_agent_result: 插入成功 item
    - upsert_agent_run: 写入/更新 Agent 运行记录
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
        guidance_strategy: dict[str, Any] = None,
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
            "guidance_strategy": guidance_strategy or {},
        }
        resource = GeneratedResource(
            user_id=user_id,
            learning_need=request.learning_need,
            request_snapshot_json=request_snapshot,
            status="pending",
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
        return {"resource_id": resource_id, "status": "pending"}

    # =========================================================================
    # Agent Run 生命周期
    # =========================================================================

    async def upsert_agent_run(
        self,
        *,
        resource_id: int,
        agent_id: str,
        status: str,
        error_message: str | None = None,
        elapsed_ms: int | None = None,
    ) -> None:
        """Upsert Agent 运行记录。存在则更新，不存在则创建。"""
        # 按 resource_id + agent_id 查找既有运行记录
        run = await self.session.exec(
            select(GeneratedResourceAgentRun).where(
                GeneratedResourceAgentRun.resource_id == resource_id,
                GeneratedResourceAgentRun.agent_id == agent_id,
            )
        )
        run_obj = run.one_or_none()
        # 已存在则原地更新状态/错误/耗时
        if run_obj:
            run_obj.status = status
            if error_message is not None:
                run_obj.error_message = error_message
            if elapsed_ms is not None:
                run_obj.elapsed_ms = elapsed_ms
            await self._commit(run_obj)
        else:
            new_run = GeneratedResourceAgentRun(
                resource_id=resource_id,
                agent_id=agent_id,
                status=status,
                error_message=error_message,
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
    ) -> ItemModel:
        """保存成功 Agent 的结果。"""
        # 仅保存成功结果，且必须有标题
        if not result.success:
            raise ValueError("仅能保存成功的结果")
        if not result.title.strip():
            raise ValueError(f"Agent {agent_id} 缺少资源标题")

        resource = await self.session.get(GeneratedResource, resource_id)
        # 校验资源存在且归属当前用户
        if resource is None or resource.user_id != user_id:
            raise ValueError("资源不存在或无权限")

        # 按格式拆分内容为 JSON / 文本存储
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
        await self._commit(item)
        return item

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
    ) -> str:
        """从数据库计算终态。

        不接收调用者声称的成功集合，不再次保存资源项。
        """
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
            status = "failed"
        elif successful == expected_agent_ids:
            status = "completed"
        elif successful:
            status = "partial_completed"
        else:
            status = "failed"

        resource.status = status
        await self._commit(resource)
        # 记录资源生成事件供学习评估聚合（失败不影响主流程）
        try:
            await record_resource_generated_event(
                db=self.session,
                user_id=user_id,
                resource_id=resource_id,
                status=status,
                topic=resource.learning_need,
                agent_types=list(successful),
            )
        except Exception:
            logger.exception(
                "Failed to record resource_generated event: resource_id=%s",
                resource_id,
            )
        return status

    async def update_resource_status(
        self,
        resource_id: int,
        status: str,
    ) -> None:
        """更新资源任务状态。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        # 仅在资源存在时更新状态
        if resource:
            resource.status = status
            await self._commit(resource)

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

        for agent_id, run in runs_by_agent.items():
            if agent_id in items_by_agent:
                item = items_by_agent[agent_id]
                merged[agent_id] = {
                    "event_type": "agent.artifact_ready",
                    "agent_id": agent_id,
                    "status": "finished",
                    "message": f"{agent_id} 资源已保存",
                    "progress": 100,
                    "artifact_id": str(item.id),
                    "elapsed_ms": run.elapsed_ms,
                }
            else:
                message = run.error_message or f"{agent_id} {run.status}"
                merged[agent_id] = {
                    "event_type": f"agent.{run.status}",
                    "agent_id": agent_id,
                    "status": run.status,
                    "message": message,
                    "progress": 100 if run.status == "completed" else 0,
                    "elapsed_ms": run.elapsed_ms,
                }
                if run.status == "running":
                    current_message = message

        # 兼容已有成功资源但缺少 AgentRun 的历史数据
        for agent_id, item in items_by_agent.items():
            if agent_id in merged:
                continue
            merged[agent_id] = {
                "event_type": "agent.artifact_ready",
                "agent_id": agent_id,
                "status": "finished",
                "message": f"{agent_id} 资源已保存",
                "progress": 100,
                "artifact_id": str(item.id),
            }

        return ResourceStatusSnapshot(
            resource_id=resource_id,
            learning_need=resource.learning_need or "",
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
            learning_need=resource.learning_need or "", selected_agents=selected_agents,
            plan_content=resource.plan_content,
            resources=[_item_to_dto(item) for item in db_items], status=resource.status,
            created_at=resource.created_at.isoformat() if resource.created_at else "",
            updated_at=resource.updated_at.isoformat() if resource.updated_at else "",
            metadata={"source": "database", "failed_agents": failed_agents},
        )


__all__ = ["ResourceService"]
