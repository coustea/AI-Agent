"""Resource 模块服务层 (app.resource.service)。

对齐 chat.service 架构模式：负责准备环境、调度主 Agent 执行循环、
管理活跃运行快照，并在终态时持久化资源条目与埋点数据。
所有操作均为无状态模块函数，无任何兼容类包装。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

from sqlmodel import col, desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import UserClaims
from app.evaluation.event_types import MODULE_RESOURCE, RESOURCE_GENERATED
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.database import session_scope
from app.infra.llm import LLM, Message
from app.infra.logging import get_logger
from app.infra.models import (
    GeneratedResource,
    GeneratedResourceItem as ItemModel,
)
from app.resource.agent import run_resource_lead_agent
from app.resource.hooks import ResourceRunHooks
from app.resource.schemas import (
    GeneratedResourceBundleDTO,
    GeneratedResourceItemDTO,
    ResourceArtifact,
    ResourceGenerationRequest,
    ResourceHistoryItemDTO,
    ResourceRunState,
    TerminalStatus,
)
from app.resource.tools import build_resource_tools
from app.shared.tools import ToolRegistry

logger = get_logger(__name__)

# 内存中正在运行的快照容器字典
_active_runs: dict[str, ResourceRunHooks] = {}


def now_utc() -> datetime:
    """获取当前 UTC 时间感知对象。"""
    return datetime.now(timezone.utc)


def get_active_run(run_id: str) -> ResourceRunHooks | None:
    """按 run_id 获取当前内存中的活跃运行实例。"""
    return _active_runs.get(run_id)


async def record_resource_generated_event(
    db: AsyncSession,
    *,
    user_id: int,
    resource_id: int,
    status: str,
    topic: str | None = None,
    agent_types: list[str] | None = None,
) -> None:
    """记录一次资源生成埋点事件到 learning_events 表。"""
    payload = LearningEventCreate(
        module=MODULE_RESOURCE,
        entity_id=str(resource_id),
        event_type=RESOURCE_GENERATED,
        topic=topic,
        event_metadata={
            "resource_id": resource_id,
            "status": status,
            "agent_types": agent_types or [],
        },
    )
    await EvaluationService().record_event(db, user_id=user_id, payload=payload)


async def prepare_resource_run(
    request: ResourceGenerationRequest,
    user: UserClaims,
) -> tuple[str, int]:
    """在数据库中入库生成主记录，初始化运行钩子并返回 (run_id, resource_id)。"""
    run_id = f"res-run-{uuid4().hex[:12]}"
    snapshot = request.model_dump(mode="json")
    snapshot["run_id"] = run_id

    async with session_scope() as session:
        record = GeneratedResource(
            user_id=user.id,
            learning_need=request.topic,
            request_snapshot_json=snapshot,
            status="pending",
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        session.add(record)
        await session.flush()
        resource_id = record.id

    if resource_id is None:
        raise RuntimeError("创建资源主记录失败")

    hooks = ResourceRunHooks(run_id=run_id, resource_id=resource_id)
    _active_runs[run_id] = hooks
    logger.info("已注册活跃 Resource 运行 run_id=%s resource_id=%d", run_id, resource_id)
    return run_id, resource_id


async def save_resource_artifacts(
    resource_id: int,
    artifacts: list[ResourceArtifact],
) -> None:
    """将智能体产物保存至 generated_resource_items 表。"""
    if not artifacts:
        return

    async with session_scope() as session:
        for artifact in artifacts:
            existing = await session.exec(
                select(ItemModel).where(
                    ItemModel.resource_id == resource_id,
                    ItemModel.agent_type == artifact.kind,
                )
            )
            for row in existing.all():
                await session.delete(row)

            content_json = None
            content_text = None
            if artifact.file_type == "json" and isinstance(artifact.content, (dict, list)):
                content_json = artifact.content
            elif artifact.file_type in ("markdown", "text", "mermaid", "code") and isinstance(artifact.content, str):
                content_text = artifact.content
            elif artifact.file_type == "markdown" and artifact.content is not None:
                content_text = str(artifact.content)

            meta = dict(artifact.metadata)
            if artifact.url:
                meta["url"] = artifact.url
            if artifact.preview_urls:
                meta["preview_urls"] = artifact.preview_urls

            item = ItemModel(
                resource_id=resource_id,
                agent_type=artifact.kind,
                title=artifact.title,
                content_json=content_json,
                content_text=content_text,
                metadata_json=meta,
                created_at=now_utc(),
            )
            session.add(item)


async def execute_resource_run(
    run_id: str,
    request: ResourceGenerationRequest,
    user: UserClaims,
) -> None:
    """后台任务：装配工具、启动主 Agent 循环、持久化产物并通知终态。"""
    hooks = _active_runs.get(run_id)
    if hooks is None:
        logger.error("未找到对应的活跃运行上下文 run_id=%s", run_id)
        return

    hooks.task = asyncio.current_task()
    status: TerminalStatus = "completed"
    error = ""
    resource_id = hooks.state.resource_id

    try:
        if hooks.cancel_requested:
            raise asyncio.CancelledError

        async with asyncio.timeout(1800):
            # 1. 准备阶段
            hooks.set_phase("preparing", "正在准备教学方案设计与子智能体工作区")

            # 构建主规划智能体上下文
            targets_str = ", ".join(request.target_resources)
            system_prompt = (
                "你是多智能体课程规划总指挥与教学资源总设计师（Resource Lead Agent）。\n"
                "你的核心使命是统筹协调并调度各个领域的专家子智能体工具，为学习者构建高质量、系统化且多模态融合的完整教学资源包。\n"
                "【执行原则】:\n"
                "1. 首先进行整体教学设计思考（输出你的教学规划与步骤安排），思考流会实时展示给用户；\n"
                "2. 紧接着调用子智能体工具，逐项完成用户在【目标交付清单】中指定的全部资源制作；\n"
                "3. 若包含课件 PPT 或教学视频，建议在核心讲义生成后进行调度，以确保多模态教材论据充实；\n"
                "4. 当全部目标资源产出完毕后，输出一份温暖、精炼的导学建议与总结，完成交付。"
            )

            user_instruction = (
                f"【学习主题】: {request.topic}\n"
                f"【学习目标】: {request.learning_goal or f'全面系统掌握 {request.topic} 的核心要义'}\n"
                f"【难度阶段】: {request.difficulty}\n"
                f"【目标交付清单】: {targets_str}\n"
                f"{f'【偏好设置】: {request.preferences}' if request.preferences else ''}\n\n"
                "请开始统筹规划并调度子智能体生成全部所需的教学资源。"
            )

            messages: list[Message] = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_instruction),
            ]

            # 装配工具箱并挂接进度钩子
            tools = build_resource_tools(
                username=user.username,
                resource_id=str(resource_id),
                on_progress=hooks.on_subagent_progress,
            )
            registry = ToolRegistry(tools)

            # 2. 规划与生成阶段
            hooks.set_phase("planning", "课程总指挥正在构思教学体系...")
            result = await run_resource_lead_agent(
                messages=messages,
                llm=LLM(temperature=0.3),
                registry=registry,
                hooks=hooks,
            )
            logger.info("run_resource_lead_agent 执行完成 summary_len=%d", len(result.summary))

    except asyncio.CancelledError:
        status, error = "cancelled", "用户停止生成"
    except TimeoutError:
        status, error = "failed", "生成超时 (>1800s)"
    except Exception as exc:
        logger.exception("执行资源生成主循环异常: %s", exc)
        status, error = "failed", str(exc)

    # 3. 持久化阶段
    hooks.set_phase("saving", "正在保存教学资源包与产物明细...")
    saved = False
    try:
        async with session_scope() as session:
            record = await session.get(GeneratedResource, resource_id)
            if record is not None:
                record.status = status
                record.updated_at = now_utc()
                session.add(record)

            await record_resource_generated_event(
                session,
                user_id=user.id,
                resource_id=resource_id,
                status=status,
                topic=request.topic,
                agent_types=[a.kind for a in hooks.state.artifacts],
            )

        if status == "completed":
            await save_resource_artifacts(resource_id, hooks.state.artifacts)

        saved = True
    except Exception as exc:
        logger.exception("持久化资源终态失败 resource_id=%d: %s", resource_id, exc)
        status, error = "failed", f"持久化失败: {exc}"
    finally:
        hooks.result_state(status, error)
        hooks.publish()
        hooks.task = None
        if saved:
            _active_runs.pop(run_id, None)


async def get_run_state(user_id: int, run_id: str) -> ResourceRunState | None:
    """读取指定运行的状态快照，优先读取内存活跃快照，结束后从数据库恢复。"""
    active = _active_runs.get(run_id)
    if active is not None:
        return active.snapshot()

    # 从数据库精确查询属于该用户的指定运行
    async with session_scope() as session:
        resource_row: GeneratedResource | None = None
        if run_id.isdigit():
            resource_row = await session.get(GeneratedResource, int(run_id))
        else:
            stmt = select(GeneratedResource).where(
                GeneratedResource.user_id == user_id,
                func.json_unquote(func.json_extract(GeneratedResource.request_snapshot_json, "$.run_id")) == run_id,
            )
            resource_row = (await session.exec(stmt)).first()

        if resource_row is None or resource_row.user_id != user_id:
            return None

        items_res = await session.exec(
            select(ItemModel).where(ItemModel.resource_id == resource_row.id)
        )
        items = items_res.all()

        artifacts: list[ResourceArtifact] = []
        for item in items:
            artifacts.append(
                ResourceArtifact(
                    id=f"art-{item.agent_type}-{item.id}",
                    kind=item.agent_type,
                    title=item.title,
                    file_type="json" if item.content_json else ("pptx" if item.agent_type == "ppt" else ("mp4" if item.agent_type == "cartoon" else "markdown")),
                    content=item.content_json or item.content_text,
                    url=item.metadata_json.get("url"),
                    preview_urls=item.metadata_json.get("preview_urls") or [],
                    metadata=item.metadata_json,
                )
            )

        state_status = "completed" if resource_row.status == "completed" else "failed"
        return ResourceRunState(
            run_id=run_id,
            resource_id=resource_row.id or 0,
            status=state_status,
            phase=state_status,
            phase_label="已完成" if state_status == "completed" else "已终止",
            artifacts=artifacts,
        )


async def cancel_run(user_id: int, run_id: str) -> str | None:
    """请求取消指定的活跃运行任务。"""
    hooks = _active_runs.get(run_id)
    if hooks is None:
        return None
    hooks.cancel_requested = True
    if hooks.task and not hooks.task.done():
        hooks.task.cancel()
    hooks.state.status = "cancelled"
    hooks.publish()
    return "cancelled"


async def get_resource_bundle(user_id: int, resource_id: int) -> GeneratedResourceBundleDTO | None:
    """获取指定任务已生成的完整教学资源包 DTO。"""
    async with session_scope() as session:
        resource = await session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return None

        items_res = await session.exec(
            select(ItemModel).where(ItemModel.resource_id == resource_id)
        )
        items = items_res.all()

        item_dtos = [
            GeneratedResourceItemDTO(
                id=item.id or 0,
                resource_id=item.resource_id,
                agent_type=item.agent_type,
                title=item.title,
                content_json=item.content_json,
                content_text=item.content_text,
                metadata_json=item.metadata_json,
                created_at=item.created_at,
            )
            for item in items
        ]

        return GeneratedResourceBundleDTO(
            id=resource.id or 0,
            user_id=resource.user_id,
            topic=resource.learning_need,
            learning_goal=str(resource.request_snapshot_json.get("learning_goal") or ""),
            status=resource.status,
            created_at=resource.created_at,
            items=item_dtos,
        )


async def list_resources(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """按用户分页查询独立教学资源列表及聚合类型统计。"""
    async with session_scope() as session:
        stmt = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(desc(GeneratedResource.id))
            .limit(limit)
            .offset(offset)
        )
        items = list((await session.exec(stmt)).all())

        count_stmt = select(func.count(GeneratedResource.id)).where(GeneratedResource.user_id == user_id)
        total = (await session.exec(count_stmt)).one() or 0

        res_ids = [r.id for r in items if r.id is not None]
        summary: dict[int, list[str]] = {}
        if res_ids:
            item_stmt = select(ItemModel.resource_id, ItemModel.agent_type).where(
                col(ItemModel.resource_id).in_(res_ids)
            )
            rows = (await session.exec(item_stmt)).all()
            for r_id, agent_type in rows:
                summary.setdefault(r_id, []).append(agent_type)

        serialized_items = []
        for r in items:
            data = r.model_dump()
            r_id = r.id or 0
            types = summary.get(r_id, [])
            data["resource_types"] = types
            data["resource_count"] = len(types)
            data["topic"] = r.learning_need
            serialized_items.append(data)

        return {
            "items": serialized_items,
            "total": total,
            "type_summary": summary,
        }


async def get_resource_status(user_id: int, resource_id: int) -> dict[str, Any] | None:
    """获取指定资源生成任务的实时状态字典。"""
    async with session_scope() as session:
        record = await session.get(GeneratedResource, resource_id)
        if record is None or record.user_id != user_id:
            return None
        return {
            "resource_id": record.id,
            "status": record.status,
            "topic": record.learning_need,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }


async def list_resource_history(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[ResourceHistoryItemDTO]:
    """查询用户的历史教学资源生成记录列表。"""
    async with session_scope() as session:
        query = (
            select(GeneratedResource)
            .where(GeneratedResource.user_id == user_id)
            .order_by(desc(GeneratedResource.id))
            .limit(limit)
            .offset(offset)
        )
        rows = (await session.exec(query)).all()

        results: list[ResourceHistoryItemDTO] = []
        for r in rows:
            items_query = select(ItemModel.agent_type).where(ItemModel.resource_id == r.id)
            agent_types = (await session.exec(items_query)).all()

            results.append(
                ResourceHistoryItemDTO(
                    id=r.id or 0,
                    topic=r.learning_need,
                    learning_goal=str(r.request_snapshot_json.get("learning_goal") or ""),
                    status=r.status,
                    created_at=r.created_at,
                    resource_count=len(agent_types),
                    resource_types=list(agent_types),
                )
            )
        return results


async def delete_resource_record(user_id: int, resource_id: int) -> bool:
    """删除指定的教学资源记录及其产物明细。"""
    async with session_scope() as session:
        resource = await session.get(GeneratedResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return False
        await session.delete(resource)
        return True
