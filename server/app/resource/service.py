"""
资源生成服务层。

整合资源生成工作流、数据库资源记录和 SSE 输出。
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import GeneratedResource, GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.constants import STANDALONE_RESOURCE_SOURCES
from app.resource.events import AgentEventEmitter, AgentRunTracker, resource_event_bus
from app.resource.items import (
    content_envelope,
    db_item_to_resource_item,
    db_item_to_agent_result,
)
from app.resource.review import (
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
from app.resource.agents.ppt import MaterialBundle, build_resource_material
from app.resource.schemas import (
    AgentResult,
    AgentSelection,
    DownstreamContext,
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ResourceInput,
    ReviewResult,
    TeachingPlan,
)
from app.infra.logging import get_module_logger

logger = get_module_logger("resource", sub="workflow")

AGGREGATION_AGENT_IDS = (PPT_AGENT_ID, VIDEO_AGENT_ID)


def _select_worker_agents(enabled_agents: list[str], registry: dict[str, Any]) -> list[str]:
    return [
        agent_id
        for agent_id in enabled_agents
        if agent_id in registry
        and agent_id not in ("planning", "review")
        and agent_id not in AGGREGATION_AGENT_IDS
    ]


BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def _build_agent_resource_input(
    *,
    request: ResourceGenerationRequest,
    resource_id: int,
    agent_id: str,
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    agent_config_extra: dict[str, Any] | None,
) -> ResourceInput:
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


def _collect_successful_handoffs(results: dict[str, AgentResult]) -> dict[str, DownstreamContext]:
    handoffs: dict[str, DownstreamContext] = {}
    for agent_id, result in results.items():
        if agent_id not in BASE_RESOURCE_AGENT_IDS:
            continue
        if not result.success or result.downstream_context is None:
            continue
        handoffs[agent_id] = result.downstream_context
    return handoffs


class ResourceService:
    """资源生成用例。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._write_locks: dict[int, asyncio.Lock] = {}

    def _get_write_lock(self, resource_id: int) -> asyncio.Lock:
        if resource_id not in self._write_locks:
            self._write_locks[resource_id] = asyncio.Lock()
        return self._write_locks[resource_id]

    def _release_write_lock(self, resource_id: int) -> None:
        self._write_locks.pop(resource_id, None)

    async def start_resource_task(
        self,
        *,
        user_id: int,
        request: ResourceGenerationRequest,
        source: str = "standalone",
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """统一入口：创建资源任务记录。"""
        resource = GeneratedResource(
            user_id=user_id,
            learning_need=request.learning_need,
            selected_agents=request.enabled_agent_ids(),
            agent_configs=request.agent_configs.model_dump(mode="json"),
            source=source,
            status="pending",
        )
        self.session.add(resource)
        try:
            await self.session.flush()
            resource_id = int(getattr(resource, "id", 0) or 0)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(resource)

        return {
            "resource_id": resource_id,
            "status": "pending",
            "source": source,
        }

    async def get_generation_status(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        """读取任务总状态及已生成资源列表。"""
        resource = await self.get_resource(user_id, resource_id, allowed_sources=allowed_sources)
        if resource is None:
            return None
        db_items = await self.list_resource_items(user_id, resource_id)
        agent_snapshots = resource_event_bus.get_latest_snapshot(resource_id)
        merged_agent_snapshots = self._merge_persisted_items_into_snapshots(
            agent_snapshots.get("agent_snapshots", {}),
            db_items,
        )
        selected_agents = list(resource.selected_agents or [])
        return {
            "resource_id": resource_id,
            "status": resource.status,
            "selected_agents": selected_agents,
            "agent_snapshots": merged_agent_snapshots,
            "overall_progress": self._calculate_overall_progress(
                status=resource.status,
                selected_agents=selected_agents,
                agent_snapshots=merged_agent_snapshots,
            ),
            "current_message": agent_snapshots.get("current_message", ""),
            "resources": [
                self._db_item_to_resource_item(item).model_dump(mode="json")
                for item in db_items
            ],
        }

    async def update_resource_status(
        self,
        resource_id: int,
        status: str,
    ) -> None:
        """更新资源状态。"""
        async with self._get_write_lock(resource_id):
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource:
                resource.status = status
                resource.updated_at = datetime.now(timezone.utc)
                await self._commit(resource)

    async def _commit(self, obj: Any) -> None:
        """提交并刷新数据库对象。"""
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise exc
        await self.session.refresh(obj)

    async def save_agent_result(
        self,
        *,
        resource_id: int,
        user_id: int,
        result: AgentResult,
    ) -> GeneratedResourceItemModel:
        """单个 Agent 成功后立即发布其数据库资源项。"""
        if not result.success or not result.content:
            raise ValueError("仅能保存已成功生成且含内容的资源")
        agent_id = str(result.metadata.get("agent_id") or "")
        title = result.title or f"{agent_id} 资源"
        content_json, content_text = content_envelope(result)
        resource_item = GeneratedResourceItemModel(
            resource_id=resource_id,
            user_id=user_id,
            agent_type=agent_id,
            content_format=result.file_type,
            title=title,
            summary=result.summary,
            generated_by=agent_id,
            content_json=content_json,
            content_text=content_text,
            metadata_json=result.metadata,
            metrics=result.metrics,
            downstream_context=result.downstream_context.model_dump(mode="json") if result.downstream_context else None,
            status="finished",
            updated_at=datetime.now(timezone.utc),
        )
        async with self._get_write_lock(resource_id):
            self.session.add(resource_item)
            await self._commit(resource_item)
        return resource_item

    async def list_resource_items(
        self,
        user_id: int,
        resource_id: int,
    ) -> list[GeneratedResourceItemModel]:
        """列出指定资源的资源明细。"""
        statement = (
            select(GeneratedResourceItemModel)
            .where(GeneratedResourceItemModel.user_id == user_id)
            .where(GeneratedResourceItemModel.resource_id == resource_id)
            .order_by(col(GeneratedResourceItemModel.id).asc())
        )
        result = await self.session.exec(statement)
        return list(result.all())

    async def list_resource_type_summary(
        self,
        user_id: int,
        resource_ids: list[int],
    ) -> dict[int, list[str]]:
        """按资源汇总已保存的 Agent 类型。"""
        if not resource_ids:
            return {}
        statement = (
            select(GeneratedResourceItemModel.resource_id, GeneratedResourceItemModel.agent_type)
            .where(GeneratedResourceItemModel.user_id == user_id)
            .where(col(GeneratedResourceItemModel.resource_id).in_(resource_ids))
            .order_by(
                col(GeneratedResourceItemModel.resource_id).asc(),
                col(GeneratedResourceItemModel.agent_type).asc(),
            )
        )
        result = await self.session.exec(statement)
        summary: dict[int, list[str]] = {resource_id: [] for resource_id in resource_ids}
        for resource_id, agent_type in result.all():
            if agent_type not in summary[resource_id]:
                summary[resource_id].append(agent_type)
        return summary

    async def results_for_review(
        self,
        user_id: int,
        resource_id: int,
        failures: dict[str, AgentResult],
    ) -> dict[str, AgentResult]:
        """从已入库资源构造审阅输入，并附加本轮失败项。"""
        db_items = await self.list_resource_items(user_id, resource_id)
        persisted = {
            item.agent_type: self._db_item_to_agent_result(item)
            for item in db_items
        }
        return {**persisted, **failures}

    async def save_generation_results(
        self,
        *,
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        results: dict[str, AgentResult],
        review_result: ReviewResult,
        teaching_plan: TeachingPlan,
    ) -> None:
        """保存审阅元数据和终态；Agent 结果已在完成节点逐条入库。"""
        saved_items = await self.list_resource_items(user_id, resource_id)
        failed_agents = [agent_id for agent_id, result in results.items() if not result.success]
        for agent_id in review_result.failed_agents:
            if agent_id and agent_id not in failed_agents:
                failed_agents.append(agent_id)
        if not review_result.passed and "review" not in failed_agents:
            failed_agents.append("review")
        successful = len(saved_items)
        if failed_agents and successful:
            status = "partial_completed"
        elif failed_agents:
            status = "failed"
        else:
            status = "completed"
        async with self._get_write_lock(resource_id):
            resource = await self.session.get(GeneratedResource, resource_id)
            if resource is None or resource.user_id != user_id:
                raise ValueError("资源不存在或无权限")

            resource.teaching_plan = teaching_plan.model_dump(mode="json")
            resource.review_result = review_result.model_dump(mode="json")
            resource.failed_agents = failed_agents
            resource.workflow_metadata = {
                "selected_agents": request.enabled_agent_ids(),
            }
            resource.status = status
            resource.updated_at = datetime.now(timezone.utc)
            await self._commit(resource)

    async def get_resource_bundle(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ) -> ResourceBundle | None:
        """从数据库读取并组装前端资源包。"""
        resource = await self.get_resource(user_id, resource_id, allowed_sources=allowed_sources)
        if resource is None:
            return None

        db_items = await self.list_resource_items(user_id, resource_id)

        review_result = (
            ReviewResult.model_validate(resource.review_result)
            if isinstance(resource.review_result, dict)
            else None
        )

        metadata = {
            "source": "database",
            "failed_agents": resource.failed_agents or [],
            "teaching_plan": resource.teaching_plan or {},
        }

        return ResourceBundle(
            id=str(resource.id),
            task_id=str(resource.id),
            title="个性化学习资源包",
            learning_need=resource.learning_need or "",
            selected_agents=resource.selected_agents or [],
            resources=[self._db_item_to_resource_item(item) for item in db_items],
            review_result=review_result,
            status=resource.status,
            created_at=resource.created_at.isoformat() if resource.created_at else "",
            updated_at=resource.updated_at.isoformat() if resource.updated_at else "",
            metadata=metadata,
        )

    def _db_item_to_resource_item(self, item: GeneratedResourceItemModel) -> GeneratedResourceItem:
        return db_item_to_resource_item(item)

    def _db_item_to_agent_result(self, item: GeneratedResourceItemModel) -> AgentResult:
        return db_item_to_agent_result(item)

    @staticmethod
    def _merge_persisted_items_into_snapshots(
        agent_snapshots: dict[str, Any],
        db_items: list[GeneratedResourceItemModel],
    ) -> dict[str, Any]:
        merged = {
            agent_id: dict(snapshot)
            for agent_id, snapshot in agent_snapshots.items()
        }
        for item in db_items:
            previous = dict(merged.get(item.agent_type, {}))
            previous.update({
                "event_type": previous.get("event_type", "agent.artifact_ready"),
                "agent_id": item.agent_type,
                "status": "finished",
                "message": previous.get("message") or f"{item.agent_type} 资源已保存，可在产物坞预览",
                "progress": 100,
                "phase": "artifact_saved",
                "artifact_id": str(item.id),
            })
            merged[item.agent_type] = previous
        return merged

    @staticmethod
    def _calculate_overall_progress(
        *,
        status: str | None,
        selected_agents: list[str],
        agent_snapshots: dict[str, Any],
    ) -> int:
        if status in {"completed", "partial_completed"}:
            return 100
        if status == "pending" and not agent_snapshots:
            return 0

        def progress_for(agent_id: str) -> int:
            raw = agent_snapshots.get(agent_id, {}).get("progress", 0)
            try:
                return max(0, min(100, int(raw)))
            except (TypeError, ValueError):
                return 0

        worker_agents = [
            agent_id
            for agent_id in selected_agents
            if agent_id not in AGGREGATION_AGENT_IDS
        ]
        stages = [
            (15, progress_for("planning")),
            (
                45,
                round(sum(progress_for(agent_id) for agent_id in worker_agents) / len(worker_agents))
                if worker_agents else 0,
            ),
            (10, progress_for(PRE_REVIEW_AGENT_ID)),
            (10, progress_for(BUNDLE_AGENT_ID)),
        ]
        if PPT_AGENT_ID in selected_agents:
            stages.extend([
                (15, progress_for(PPT_AGENT_ID)),
                (5, progress_for(PPT_REVIEW_AGENT_ID)),
            ])
        if VIDEO_AGENT_ID in selected_agents:
            stages.extend([
                (15, progress_for(VIDEO_AGENT_ID)),
                (5, progress_for(VIDEO_REVIEW_AGENT_ID)),
            ])
        weight_total = sum(weight for weight, _ in stages)
        if weight_total <= 0:
            return 0
        return max(0, min(100, round(sum(weight * progress for weight, progress in stages) / weight_total)))

    async def get_resource(
        self,
        user_id: int,
        resource_id: int,
        *,
        allowed_sources: tuple[str, ...] | None = None,
    ) -> GeneratedResource | None:
        """获取资源详情。"""
        resource = await self.session.get(GeneratedResource, resource_id)
        if resource and resource.user_id == user_id and self._source_allowed(resource.source, allowed_sources):
            return resource
        return None

    async def list_resources(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        *,
        sources: tuple[str, ...] | None = None,
    ) -> list[GeneratedResource]:
        """列出用户资源。"""
        statement = select(GeneratedResource).where(GeneratedResource.user_id == user_id)
        if sources:
            statement = statement.where(col(GeneratedResource.source).in_(sources))
        statement = statement.order_by(col(GeneratedResource.id).desc()).offset(offset).limit(limit)
        result = await self.session.exec(statement)
        return list(result.all())

    async def count_resources(
        self,
        user_id: int,
        *,
        sources: tuple[str, ...] | None = None,
    ) -> int:
        """统计用户资源总数。"""
        from sqlmodel import func
        statement = select(func.count(GeneratedResource.id)).where(GeneratedResource.user_id == user_id)
        if sources:
            statement = statement.where(col(GeneratedResource.source).in_(sources))
        result = await self.session.exec(statement)
        return result.one()

    @staticmethod
    def _source_allowed(source: str | None, allowed_sources: tuple[str, ...] | None) -> bool:
        if not allowed_sources:
            return True
        return (source or "standalone") in allowed_sources


async def run_multi_agent_generation(
    user_id: int,
    request: ResourceGenerationRequest,
    profile: dict[str, Any],
    resource_id: int,
) -> None:
    """【核心编排引擎】在后台执行多智能体资源生成任务 (Multi-Agent DAG Workflow)。

    此函数是整个多智能体系统的"总导演"，它按以下 DAG (有向无环图) 流程调度各个智能体：

    [ 阶段 1 ] : PlanningAgent (规划智能体) — 串行，必须先完成
                 ↓
                 生成全局 TeachingPlan（教学方向、概要、大纲和边界）
                 ↓
    [ 阶段 2 ] : 并行调度所有启用的 Worker Agents (如 Content, Quiz, Code, Mindmap 等)
                 (各个 Worker 基于 TeachingPlan 生成资源和 DownstreamContext)
                 ↓
    [ 阶段 3 ] : 前置审核、PPT、Video 聚合生成并行执行
                 - 前置审核与 PPT、Video 生成并行启动
                 - 审核发现问题不拦截，记录到 issues 中供前端展示提示
                 ↓
    [ 阶段 4 ] : 组装并落库 (Assembler / Save)
    """
    from app.infra.database import session_scope
    from app.resource.agents import AGENT_REGISTRY

    async with session_scope() as session:
        usecases = ResourceService(session)
        enabled_agents = request.enabled_agent_ids()

        run_id = f"resource-{resource_id}-{uuid4().hex[:8]}"
        emitter = AgentEventEmitter(resource_id=resource_id, run_id=run_id)

        success = False
        done_emitted = False
        start_time = time.perf_counter()
        try:
            logger.info(
                "启动资源生成: run_id=%s user_id=%s, resource_id=%s, agents=%s",
                run_id, user_id, resource_id, enabled_agents,
            )
            await usecases.update_resource_status(resource_id, "generating")

            # ==========================================
            # 阶段 1: 规划阶段 (Planning Agent)
            # ==========================================
            planning_input = ResourceInput(
                resource_id=resource_id,
                learning_need=request.learning_need,
                learning_scenario=request.learning_scenario,
                profile=profile,
                agent_config={"enabled_agents": enabled_agents},
            )
            async with AgentRunTracker(
                emitter=emitter,
                agent_id="planning",
                phase="planning",
                message="正在规划教学方向与大纲",
                progress=5,
            ) as planning_tracker:
                planning_result = await AGENT_REGISTRY["planning"](emitter).generate_resource(planning_input)
                await planning_tracker.finish(
                    "教学方向与大纲已生成" if planning_result.success else (planning_result.error or "规划失败"),
                    success=planning_result.success,
                    metrics={"enabled_agents": len(enabled_agents)},
                )

            teaching_plan = None
            if planning_result.success and planning_result.metadata:
                plan_data = planning_result.metadata.get("teaching_plan")
                if isinstance(plan_data, dict):
                    teaching_plan = TeachingPlan.model_validate(plan_data)

            planning_elapsed = time.perf_counter() - start_time
            if planning_result.success:
                logger.info("Planning 完成: %.2fs", planning_elapsed)
            else:
                logger.error(
                    "Planning 失败，终止整个生成流程: resource_id=%s run_id=%s error=%s 耗时=%.2fs",
                    resource_id, run_id, planning_result.error, planning_elapsed,
                )
                await emitter.emit_done(success=False, message=f"规划阶段失败: {planning_result.error or '未知错误'}")
                done_emitted = True
                success = False
                return

            if teaching_plan is None:
                logger.error("Planning 未返回 teaching_plan，终止生成: resource_id=%s run_id=%s", resource_id, run_id)
                await emitter.emit_done(success=False, message="规划阶段未返回教学计划")
                done_emitted = True
                success = False
                return

            # ==========================================
            # 阶段 2: 基础资源并行生成阶段 (Parallel Worker Agents)
            # ==========================================
            await emitter.emit_agent(COORDINATOR_AGENT_ID, status="running", message="并行生成基础资源", progress=18)
            results: dict[str, AgentResult] = {}

            worker_agents = _select_worker_agents(enabled_agents, AGENT_REGISTRY)

            async def run_one(agent_id: str, agent_config_extra: dict[str, Any] | None = None, upstream_handoffs_override: dict[str, DownstreamContext] | None = None) -> None:
                """独立运行单个 Worker Agent 的协程函数"""
                agent_start = time.perf_counter()
                try:
                    handoffs = upstream_handoffs_override if upstream_handoffs_override is not None else {}
                    resource_input = _build_agent_resource_input(
                        request=request,
                        resource_id=resource_id,
                        agent_id=agent_id,
                        teaching_plan=teaching_plan,
                        profile=profile,
                        upstream_handoffs=handoffs,
                        agent_config_extra=agent_config_extra,
                    )
                    logger.info(
                        "Agent[%s] 启动: run_id=%s resource_id=%s config=%s",
                        agent_id, run_id, resource_id,
                        {k: v for k, v in resource_input.agent_config.items() if k in ("page_count", "slide_count", "difficulty", "question_count")},
                    )
                    agent = AGENT_REGISTRY[agent_id](emitter)
                    async with AgentRunTracker(
                        emitter=emitter,
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
                    results[agent_id] = result

                    agent_elapsed = time.perf_counter() - agent_start
                    if result.success:
                        logger.info(
                            "Agent[%s] 完成: %.2fs summary=%s metrics=%s",
                            agent_id, agent_elapsed, result.summary,
                            result.metrics or {},
                        )
                    else:
                        logger.warning(
                            "Agent[%s] 失败: %.2fs error=%s",
                            agent_id, agent_elapsed, result.error,
                        )

                    if result.success and result.content:
                        resource_item = await usecases.save_agent_result(
                            user_id=user_id,
                            resource_id=resource_id,
                            result=result,
                        )
                        await emitter.emit_artifact_ready(
                            agent_id,
                            message=f"{agent_id} 资源已保存，可在产物坞预览",
                            artifact_id=str(resource_item.id),
                            metrics=result.metrics,
                        )
                except Exception as exc:
                    agent_elapsed = time.perf_counter() - agent_start
                    logger.error("Agent[%s] 异常: %.2fs", agent_id, agent_elapsed, exc_info=True)
                    results[agent_id] = AgentResult(
                        success=False,
                        error=str(exc),
                        metadata={"agent_id": agent_id},
                    )

            logger.info("开始并行基础 Worker 生成: run_id=%s agents=%s", run_id, worker_agents)
            await asyncio.gather(*(run_one(agent_id) for agent_id in worker_agents))

            worker_elapsed = time.perf_counter() - start_time
            success_count = sum(1 for r in results.values() if r.success)
            fail_count = sum(1 for r in results.values() if not r.success)
            logger.info("基础 Worker 完成: 成功=%s, 失败=%s, 耗时=%.2fs", success_count, fail_count, worker_elapsed)
            coordinator_status = "failed" if worker_agents and success_count == 0 else "finished"
            await emitter.emit_agent(
                COORDINATOR_AGENT_ID,
                status=coordinator_status,
                message=f"基础资源并行生成完成：成功 {success_count} 个，失败 {fail_count} 个",
                progress=70,
            )

            # ==========================================
            # 阶段 3: 审核 + PPT 并行执行（非决阻塞审核）
            # ==========================================

            base_results = dict(results)

            pre_review_result = ReviewResult(passed=True, overall_score=100)
            review_result = pre_review_result

            review_results_to_merge: list[ReviewResult] = []

            def remember_review_result(result: ReviewResult) -> None:
                review_results_to_merge.append(result)

            def merge_review_results(items: list[ReviewResult]) -> ReviewResult:
                if not items:
                    return ReviewResult(passed=True, overall_score=100)

                merged = ReviewResult(passed=all(item.passed for item in items))
                merged.overall_score = min(item.overall_score for item in items)
                merged.consistency_score = min(item.consistency_score for item in items)
                merged.personalization_score = min(item.personalization_score for item in items)

                for item in items:
                    merged.issues.extend(item.issues)
                    merged.suggestions.extend(item.suggestions)
                    for agent_id in item.failed_agents:
                        if agent_id not in merged.failed_agents:
                            merged.failed_agents.append(agent_id)
                return merged

            # 准备审核数据
            failed_results = {aid: r for aid, r in results.items() if not r.success}
            review_results = await usecases.results_for_review(user_id, resource_id, failed_results)
            pre_audit_envelope, missing_resources = build_pre_audit_envelope(
                request=request,
                results=review_results,
                profile=profile,
                teaching_plan=teaching_plan,
            )
            source_audit_required = bool(pre_audit_envelope["deep_audit_resources"])

            # 收集并行任务
            phase3_tasks: list[asyncio.Task] = []

            # --- 3a: 前置审核（后台执行，不阻塞 PPT）---
            async def run_pre_review() -> None:
                nonlocal pre_review_result, review_result
                if missing_resources:
                    pre_review_result = failed_review_result(
                        status="needs_revision",
                        message=f"资源生成不完整: {', '.join(missing_resources)}",
                        revision_targets=missing_resources,
                        review_mode="pre_audit",
                    )
                    remember_review_result(pre_review_result)
                    await emitter.emit_agent(
                        PRE_REVIEW_AGENT_ID,
                        status="finished",
                        message=f"审核发现资源不完整: {', '.join(missing_resources)}（已放行，请留意提示）",
                        progress=80,
                        metrics={"review_warning": True, "missing_resources": missing_resources},
                    )
                    logger.warning("前置审核发现缺失资源（已放行）: missing_resources=%s", missing_resources)
                elif source_audit_required and "review" in AGENT_REGISTRY:
                    review_input = ResourceInput(
                        resource_id=resource_id,
                        learning_need=request.learning_need,
                        learning_scenario=request.learning_scenario,
                        profile=profile,
                        agent_config={
                            "review_envelope": pre_audit_envelope,
                            "progress_agent_id": PRE_REVIEW_AGENT_ID,
                        },
                    )
                    async with AgentRunTracker(
                        emitter=emitter,
                        agent_id=PRE_REVIEW_AGENT_ID,
                        phase="reviewing_sources",
                        message="正在审核基础资源事实性与安全性",
                        progress=72,
                    ) as pre_review_tracker:
                        pre_review_agent_result = await AGENT_REGISTRY["review"](emitter).generate_resource(review_input)
                        await pre_review_tracker.finish(
                            "前置审核完成",
                            success=pre_review_agent_result.success,
                            metrics={"review_status": pre_review_agent_result.metadata.get("review_status")},
                        )
                    pre_review_result = review_result_from_agent(pre_review_agent_result)
                    remember_review_result(pre_review_result)
                    logger.info(
                        "Pre Review 完成: success=%s, status=%s",
                        pre_review_agent_result.success,
                        pre_review_agent_result.metadata.get("review_status"),
                    )
                    if not pre_review_result.passed:
                        await emitter.emit_agent(
                            PRE_REVIEW_AGENT_ID,
                            status="finished",
                            message=f"审核发现问题: {len(pre_review_result.issues)} 项（已放行，请留意提示）",
                            progress=80,
                            metrics={"review_warning": True, "issue_count": len(pre_review_result.issues)},
                        )
                elif source_audit_required:
                    pre_review_result = failed_review_result(
                        status="blocked",
                        message="审核智能体不可用，无法完成前置安全审核",
                        revision_targets=["review"],
                        review_mode="pre_audit",
                    )
                    remember_review_result(pre_review_result)
                    await emitter.emit_agent(
                        PRE_REVIEW_AGENT_ID,
                        status="finished",
                        message="审核智能体不可用，前置安全审核已跳过",
                        progress=80,
                        metrics={"review_warning": True, "reason": "agent_unavailable"},
                    )
                else:
                    await emitter.emit_agent(
                        PRE_REVIEW_AGENT_ID,
                        status="skipped",
                        message="无需深度审核，跳过前置审核",
                        progress=80,
                    )
                    logger.info("未选择 content/reading 或 review agent 不可用，跳过前置 LLM 审核")

            # --- 3b: PPT 生成 + PPT 审核（与 pre_review 并行）---
            async def run_ppt_pipeline() -> None:
                if PPT_AGENT_ID not in enabled_agents or PPT_AGENT_ID not in AGENT_REGISTRY:
                    return

                await emitter.emit_agent(
                    "ppt",
                    status="running",
                    message="正在生成 PPT",
                    progress=80,
                    phase="ppt_generating",
                )

                # PPT 使用 upstream handoffs 构建素材
                base_handoffs = _collect_successful_handoffs(base_results)
                material_bundle = build_resource_material(ResourceInput(
                    resource_id=resource_id,
                    learning_need=request.learning_need,
                    learning_scenario=request.learning_scenario,
                    agent_name=PPT_AGENT_ID,
                    agent_config=request.agent_configs.get(PPT_AGENT_ID, {}),
                    teaching_plan=teaching_plan,
                    profile=profile,
                    upstream_handoffs=base_handoffs,
                ))
                await run_one(PPT_AGENT_ID, {
                    "material_bundle": material_bundle.model_dump(mode="json"),
                    "upstream_handoff_agent_ids": list(base_handoffs.keys()),
                }, upstream_handoffs_override=base_handoffs)

                # PPT 审核（非阻塞，记录问题但不拦截）
                await emitter.emit_agent("ppt_review", status="running", message="PPT 内容审核中", progress=90)
                ppt_result = results.get(PPT_AGENT_ID)
                if not ppt_result or not ppt_result.success:
                    await emitter.emit_agent(
                        PPT_REVIEW_AGENT_ID,
                        status="skipped",
                        message="PPT 未成功生成，跳过 PPT 审核",
                        progress=95,
                    )
                    return

                ppt_failed_results = {aid: r for aid, r in results.items() if not r.success}
                ppt_review_results = await usecases.results_for_review(user_id, resource_id, ppt_failed_results)
                ppt_audit_envelope, ppt_missing_resources = build_ppt_audit_envelope(
                    request=request,
                    results=ppt_review_results,
                    profile=profile,
                    teaching_plan=teaching_plan,
                )
                if ppt_missing_resources:
                    ppt_review_result = failed_review_result(
                        status="needs_revision",
                        message=f"PPT 生成不完整: {', '.join(ppt_missing_resources)}",
                        revision_targets=ppt_missing_resources,
                        review_mode="ppt_audit",
                    )
                    remember_review_result(ppt_review_result)
                    await emitter.emit_agent(
                        PPT_REVIEW_AGENT_ID,
                        status="finished",
                        message=f"PPT 审核发现问题: {', '.join(ppt_missing_resources)}（已放行，请留意提示）",
                        progress=95,
                        metrics={"review_warning": True, "missing_resources": ppt_missing_resources},
                    )
                    logger.warning("PPT 审核发现缺失（已放行）: missing_resources=%s", ppt_missing_resources)
                elif "review" in AGENT_REGISTRY:
                    ppt_review_input = ResourceInput(
                        resource_id=resource_id,
                        learning_need=request.learning_need,
                        learning_scenario=request.learning_scenario,
                        profile=profile,
                        agent_config={
                            "review_envelope": ppt_audit_envelope,
                            "progress_agent_id": PPT_REVIEW_AGENT_ID,
                        },
                    )
                    async with AgentRunTracker(
                        emitter=emitter,
                        agent_id=PPT_REVIEW_AGENT_ID,
                        phase="reviewing_ppt",
                        message="正在审核 PPT 内容安全与事实一致性",
                        progress=92,
                    ) as ppt_review_tracker:
                        ppt_review_agent_result = await AGENT_REGISTRY["review"](emitter).generate_resource(ppt_review_input)
                        await ppt_review_tracker.finish(
                            "PPT 审核完成",
                            success=ppt_review_agent_result.success,
                            metrics={"review_status": ppt_review_agent_result.metadata.get("review_status")},
                        )
                    ppt_review_result = review_result_from_agent(ppt_review_agent_result)
                    remember_review_result(ppt_review_result)
                    logger.info(
                        "PPT Review 完成: success=%s, status=%s",
                        ppt_review_agent_result.success,
                        ppt_review_agent_result.metadata.get("review_status"),
                    )
                    if not ppt_review_result.passed:
                        await emitter.emit_agent(
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
                    remember_review_result(ppt_review_result)
                    await emitter.emit_agent(
                        PPT_REVIEW_AGENT_ID,
                        status="finished",
                        message="审核智能体不可用，PPT 安全审核已跳过",
                        progress=95,
                        metrics={"review_warning": True, "reason": "agent_unavailable"},
                    )

            # --- 3c: Video 生成 + Video 审核 ---
            async def run_video_pipeline() -> None:
                if VIDEO_AGENT_ID not in enabled_agents or VIDEO_AGENT_ID not in AGENT_REGISTRY:
                    return

                await emitter.emit_agent(
                    VIDEO_AGENT_ID,
                    status="running",
                    message="正在生成讲解视频配置与分镜",
                    progress=80,
                    phase="video_generating",
                )

                await run_one(VIDEO_AGENT_ID, upstream_handoffs_override=_collect_successful_handoffs(base_results))

                await emitter.emit_agent("video_review", status="running", message="讲解视频内容审核中", progress=90)
                video_result = results.get(VIDEO_AGENT_ID)
                if not video_result or not video_result.success:
                    await emitter.emit_agent(
                        VIDEO_REVIEW_AGENT_ID,
                        status="skipped",
                        message="讲解视频未成功生成，跳过审核",
                        progress=95,
                    )
                    return

                video_failed_results = {aid: r for aid, r in results.items() if not r.success}
                video_review_results = await usecases.results_for_review(user_id, resource_id, video_failed_results)
                video_audit_envelope, video_missing_resources = build_video_audit_envelope(
                    request=request,
                    results=video_review_results,
                    profile=profile,
                    teaching_plan=teaching_plan,
                )
                if video_missing_resources:
                    video_review_result = failed_review_result(
                        status="needs_revision",
                        message=f"视频生成不完整: {', '.join(video_missing_resources)}",
                        revision_targets=video_missing_resources,
                        review_mode="video_audit",
                    )
                    remember_review_result(video_review_result)
                    await emitter.emit_agent(
                        VIDEO_REVIEW_AGENT_ID,
                        status="finished",
                        message=f"视频审核发现问题: {', '.join(video_missing_resources)}（已放行，请留意提示）",
                        progress=95,
                        metrics={"review_warning": True, "missing_resources": video_missing_resources},
                    )
                    logger.warning("视频审核发现缺失（已放行）: missing_resources=%s", video_missing_resources)
                elif "review" in AGENT_REGISTRY:
                    video_review_input = ResourceInput(
                        resource_id=resource_id,
                        learning_need=request.learning_need,
                        learning_scenario=request.learning_scenario,
                        profile=profile,
                        agent_config={
                            "review_envelope": video_audit_envelope,
                            "progress_agent_id": VIDEO_REVIEW_AGENT_ID,
                        },
                    )
                    async with AgentRunTracker(
                        emitter=emitter,
                        agent_id=VIDEO_REVIEW_AGENT_ID,
                        phase="reviewing_video",
                        message="正在审核讲解视频内容安全与事实一致性",
                        progress=92,
                    ) as video_review_tracker:
                        video_review_agent_result = await AGENT_REGISTRY["review"](emitter).generate_resource(video_review_input)
                        await video_review_tracker.finish(
                            "讲解视频审核完成",
                            success=video_review_agent_result.success,
                            metrics={"review_status": video_review_agent_result.metadata.get("review_status")},
                        )
                    video_review_result = review_result_from_agent(video_review_agent_result)
                    remember_review_result(video_review_result)
                    if not video_review_result.passed:
                        await emitter.emit_agent(
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
                    remember_review_result(video_review_result)
                    await emitter.emit_agent(
                        VIDEO_REVIEW_AGENT_ID,
                        status="finished",
                        message="审核智能体不可用，视频安全审核已跳过",
                        progress=95,
                        metrics={"review_warning": True, "reason": "agent_unavailable"},
                    )

            # 并行启动 pre_review 和 PPT pipeline
            if source_audit_required:
                phase3_tasks.append(asyncio.create_task(run_pre_review()))
            else:
                await emitter.emit_agent(
                    PRE_REVIEW_AGENT_ID,
                    status="skipped",
                    message="无需深度审核，跳过前置审核",
                    progress=80,
                )

            if PPT_AGENT_ID in enabled_agents and PPT_AGENT_ID in AGENT_REGISTRY:
                phase3_tasks.append(asyncio.create_task(run_ppt_pipeline()))
            elif PPT_AGENT_ID in enabled_agents:
                await emitter.emit_agent(
                    PPT_AGENT_ID,
                    status="skipped",
                    message="PPT 智能体不可用",
                    progress=80,
                )
                await emitter.emit_agent(
                    PPT_REVIEW_AGENT_ID,
                    status="skipped",
                    message="PPT 未生成，跳过 PPT 审核",
                    progress=80,
                )

            if VIDEO_AGENT_ID in enabled_agents and VIDEO_AGENT_ID in AGENT_REGISTRY:
                phase3_tasks.append(asyncio.create_task(run_video_pipeline()))
            elif VIDEO_AGENT_ID in enabled_agents:
                await emitter.emit_agent(
                    VIDEO_AGENT_ID,
                    status="skipped",
                    message="讲解视频智能体不可用",
                    progress=80,
                )
                await emitter.emit_agent(
                    VIDEO_REVIEW_AGENT_ID,
                    status="skipped",
                    message="视频未生成，跳过审核",
                    progress=80,
                )

            # 等待阶段 3 全部完成
            if phase3_tasks:
                await asyncio.gather(*phase3_tasks)

            # 合并所有审查结果为最终 review_result
            review_result = merge_review_results(review_results_to_merge)

            # ==========================================
            # 阶段 4: 持久化与打包 (Save Final Results)
            # ==========================================
            await emitter.emit_agent(
                BUNDLE_AGENT_ID,
                status="running",
                message="正在组装资源包并保存结果",
                progress=95,
                phase="bundling",
            )
            try:
                await usecases.save_generation_results(
                    user_id=user_id,
                    resource_id=resource_id,
                    request=request,
                    results=results,
                    review_result=review_result,
                    teaching_plan=teaching_plan,
                )

                saved_items = await usecases.list_resource_items(user_id, resource_id)
                resource = await usecases.get_resource(user_id, resource_id)
                current_status = resource.status if resource else "failed"
                success = current_status in ("completed", "partial_completed") and len(saved_items) > 0
                await emitter.emit_agent(
                    BUNDLE_AGENT_ID,
                    status="finished" if success else "failed",
                    message="资源包组装完成" if success else "资源包组装失败",
                    progress=100,
                )
            except Exception:
                await emitter.emit_agent(BUNDLE_AGENT_ID, status="failed", message="资源包组装异常", progress=0)
                raise
            await emitter.emit_done(
                success=success,
                message="资源生成完成" if success else "资源生成失败",
            )
            done_emitted = True
            total_elapsed = time.perf_counter() - start_time
            logger.info("资源生成结束: resource_id=%s, success=%s, 耗时=%.2fs", resource_id, success, total_elapsed)
        except Exception:
            total_elapsed = time.perf_counter() - start_time
            logger.error("资源生成异常: resource_id=%s, 耗时=%.2fs", resource_id, total_elapsed, exc_info=True)

        usecases._release_write_lock(resource_id)

        if not success:
            await usecases.update_resource_status(resource_id, "failed")
            if not done_emitted:
                await emitter.emit_done(success=False, message="资源生成失败")
