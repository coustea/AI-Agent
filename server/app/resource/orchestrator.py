"""
资源生成编排器 — 简化的 2 层架构。

Orchestrator 直接内联规划、执行、组装，不再拆分为独立模块。
执行策略: content outline-first → 并行启动下游 Agent → content 完整生成 → 组装。
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.infra.logging import get_logger
from app.resource.agents import AGENT_CLASSES
from app.resource.events import AgentEventEmitter
from app.resource.schemas import (
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
    StudyPathStep,
    WorkerResult,
    WorkerState,
)
from app.resource.utils import load_user_profile

logger = get_logger(__name__)

# Agent 依赖关系: content 先生成大纲，下游 Agent 依赖大纲
_DEPENDS_ON_CONTENT: set[str] = {"mindmap", "diagram", "quiz", "code", "reading"}

# Agent 元信息 (用于 /agents 接口)
AGENT_META: dict[str, dict[str, Any]] = {
    "content": {
        "name": "课程内容",
        "description": "生成专业课程讲解文档",
        "icon": "Document",
        "layer": 0,
        "layer_name": "核心内容层",
        "default_enabled": True,
    },
    "mindmap": {
        "name": "思维导图",
        "description": "生成知识结构思维导图",
        "icon": "Mindmap",
        "layer": 0,
        "layer_name": "核心内容层",
        "default_enabled": True,
    },
    "diagram": {
        "name": "图表",
        "description": "生成 Mermaid 图表",
        "icon": "Diagram",
        "layer": 1,
        "layer_name": "辅助理解层",
        "default_enabled": True,
    },
    "quiz": {
        "name": "习题",
        "description": "生成练习习题",
        "icon": "Quiz",
        "layer": 1,
        "layer_name": "辅助理解层",
        "default_enabled": True,
    },
    "code": {
        "name": "代码",
        "description": "生成代码示例",
        "icon": "Code",
        "layer": 1,
        "layer_name": "辅助理解层",
        "default_enabled": False,
    },
    "reading": {
        "name": "阅读推荐",
        "description": "推荐学习资源",
        "icon": "Reading",
        "layer": 2,
        "layer_name": "拓展学习层",
        "default_enabled": True,
    },
}


class Orchestrator:
    """资源生成编排器。"""

    def __init__(self, user_id: int, resource_id: int, emitter: AgentEventEmitter):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter

    async def run(self, request: ResourceGenerationRequest) -> list[WorkerResult]:
        """执行资源生成流程。"""
        profile = await self._load_profile()

        # 1. 规划: 确定启用的 Agent 及执行顺序
        plan = self._plan(request)
        if not plan:
            await self.emitter.emit_error("没有启用的 Agent")
            return []

        await self.emitter.emit_workflow("planning", "规划完成", progress=10)

        # 2. 执行: content outline-first + 并行
        results = await self._execute(plan, request, profile)

        # 3. 组装: 检查结果 + 返回
        bundle = self._assemble(results)
        await self.emitter.emit_bundle(bundle, progress=95)

        return bundle

    # ------------------------------------------------------------------
    # 规划 (内联)
    # ------------------------------------------------------------------

    def _plan(self, request: ResourceGenerationRequest) -> list[dict[str, Any]]:
        """
        根据前端配置规划执行顺序。

        返回有序的 Agent 执行计划列表，每项包含:
          agent_id, agent_config, layer_index
        """
        enabled_agents = self._resolve_enabled_agents(request)
        if not enabled_agents:
            return []

        # 分层: content 在前，其余按 layer 排序
        plan: list[dict[str, Any]] = []
        for agent_id in enabled_agents:
            meta = AGENT_META.get(agent_id, {})
            agent_config = request.agent_configs.get(agent_id, {})
            plan.append({
                "agent_id": agent_id,
                "agent_config": agent_config,
                "layer_index": meta.get("layer", 0),
            })

        # 排序: content 最先，然后按 layer 升序
        plan.sort(key=lambda x: (0 if x["agent_id"] == "content" else 1, x["layer_index"]))

        return plan

    def _resolve_enabled_agents(self, request: ResourceGenerationRequest) -> list[str]:
        """解析前端启用的 Agent 列表。"""
        if not request.selected_agents:
            # 默认全部启用
            return list(AGENT_CLASSES.keys())

        enabled = [
            sel.agent_id.value
            for sel in request.selected_agents
            if sel.enabled and sel.agent_id.value in AGENT_CLASSES
        ]
        return enabled

    # ------------------------------------------------------------------
    # 执行 (content outline-first + 并行)
    # ------------------------------------------------------------------

    async def _execute(
        self,
        plan: list[dict[str, Any]],
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
    ) -> dict[str, WorkerResult]:
        """执行 Agent 列表，返回 agent_id → WorkerResult 映射。"""
        results: dict[str, WorkerResult] = {}
        has_content = any(p["agent_id"] == "content" for p in plan)

        if has_content:
            # Content outline-first 模式
            await self._execute_content_first(plan, request, profile, results)
        else:
            # 无 content，直接并行执行所有 Agent
            await self._execute_parallel(plan, request, profile, results)

        return results

    async def _execute_content_first(
        self,
        plan: list[dict[str, Any]],
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
        results: dict[str, WorkerResult],
    ) -> None:
        """Content outline-first 执行模式。"""
        content_plan = next(p for p in plan if p["agent_id"] == "content")
        downstream_plans = [p for p in plan if p["agent_id"] != "content"]

        # Phase 1: Content 生成大纲
        await self.emitter.emit_workflow("layer_0", "正在生成内容大纲", progress=15)
        content_state = self._build_state(content_plan, request, profile, results)
        content_state.outline_only = True

        content_agent = AGENT_CLASSES["content"](
            self.user_id, self.resource_id, self.emitter
        )
        outline_result = await content_agent.run(content_state)
        results["content"] = outline_result

        if not outline_result.success:
            logger.warning("[Orchestrator] Content 大纲生成失败，下游 Agent 将无大纲参考")

        outline_text = outline_result.content if outline_result.success else None

        # Phase 2: 并行执行 — content 完整生成 + 下游 Agent
        await self.emitter.emit_workflow("layer_1", "并行生成所有资源", progress=30)

        tasks = []

        # Content 完整生成 (带大纲)
        content_full_state = self._build_state(content_plan, request, profile, results)
        content_full_state.outline_only = False
        content_full_state.outline = outline_text
        content_agent_full = AGENT_CLASSES["content"](
            self.user_id, self.resource_id, self.emitter
        )
        tasks.append(self._run_agent("content", content_agent_full, content_full_state, results))

        # 下游 Agent (带大纲参考)
        for p in downstream_plans:
            agent_id = p["agent_id"]
            state = self._build_state(p, request, profile, results)
            state.outline = outline_text
            agent = AGENT_CLASSES[agent_id](self.user_id, self.resource_id, self.emitter)
            tasks.append(self._run_agent(agent_id, agent, state, results))

        await asyncio.gather(*tasks)

    async def _execute_parallel(
        self,
        plan: list[dict[str, Any]],
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
        results: dict[str, WorkerResult],
    ) -> None:
        """无 content 时的纯并行执行。"""
        await self.emitter.emit_workflow("layer_0", "并行生成所有资源", progress=20)

        tasks = []
        for p in plan:
            agent_id = p["agent_id"]
            state = self._build_state(p, request, profile, results)
            agent = AGENT_CLASSES[agent_id](self.user_id, self.resource_id, self.emitter)
            tasks.append(self._run_agent(agent_id, agent, state, results))

        await asyncio.gather(*tasks)

    async def _run_agent(
        self,
        agent_id: str,
        agent,
        state: WorkerState,
        results: dict[str, WorkerResult],
    ) -> None:
        """运行单个 Agent 并保存结果。"""
        try:
            result = await agent.run(state)
            results[agent_id] = result

            # 发送资源事件
            if result.success:
                await self.emitter.emit_resource(
                    agent_id=agent_id,
                    title=result.title,
                    file_type=result.file_type,
                    content=result.content,
                    summary=result.summary,
                    summary_data=result.summary_data,
                    metadata=result.metadata,
                )
            else:
                logger.warning("[Orchestrator] Agent %s 执行失败: %s", agent_id, result.error)

        except Exception as exc:
            logger.exception("[Orchestrator] Agent %s 异常", agent_id)
            results[agent_id] = WorkerResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # 组装 (内联)
    # ------------------------------------------------------------------

    def _assemble(self, results: dict[str, WorkerResult]) -> list[WorkerResult]:
        """组装最终结果: 过滤失败项，按 layer 排序。"""
        bundle = []
        for agent_id, result in results.items():
            if not result.success:
                logger.warning("[Orchestrator] 跳过失败的 Agent: %s (%s)", agent_id, result.error)
                continue
            if not result.content:
                logger.warning("[Orchestrator] 跳过空内容的 Agent: %s", agent_id)
                continue
            bundle.append(result)

        # 按 layer 排序
        def _layer_key(r: WorkerResult) -> int:
            aid = r.metadata.get("agent_id", "")
            return AGENT_META.get(aid, {}).get("layer", 99)

        bundle.sort(key=_layer_key)
        return bundle

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_state(
        self,
        plan_item: dict[str, Any],
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
        results: dict[str, WorkerResult],
    ) -> WorkerState:
        """构建 Agent 执行状态。"""
        agent_id = plan_item["agent_id"]
        # 收集上游依赖结果
        deps = []
        if agent_id in _DEPENDS_ON_CONTENT and "content" in results:
            dep = results["content"].model_dump()
            dep["agent_id"] = "content"
            dep["agent_name"] = "content"
            deps.append(dep)

        return WorkerState(
            task={
                "learning_need": request.learning_need,
                "learning_scenario": request.learning_scenario,
                "selected_agents": request.enabled_agent_ids(),
                "output_options": request.output_options.model_dump(mode="json"),
            },
            agent_name=agent_id,
            agent_config=plan_item.get("agent_config", {}),
            learning_scenario=request.learning_scenario,
            layer_index=AGENT_META.get(agent_id, {}).get("layer", 0),
            dependencies=deps,
            profile=profile,
        )

    async def _load_profile(self) -> dict[str, Any]:
        """加载学习者画像，失败时不阻断资源生成。"""
        try:
            return await load_user_profile(self.user_id)
        except Exception as exc:
            logger.warning("[Orchestrator] 学习者画像加载失败: %s", exc)
            return {}


class ResourceWorkflow:
    """资源生成工作流适配层。

    连接 HTTP service、数据库存储、轻量 Orchestrator 和前端 SSE 契约。
    """

    def __init__(self, emitter: AgentEventEmitter, resource_store: object) -> None:
        self.emitter = emitter
        self.store = resource_store

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, Any]:
        """执行资源生成并返回前端 bundle。"""
        resource_record = await self.store.create_resource(user_id=user_id, request=request)
        resource_id = int(getattr(resource_record, "id", 0) or 0)
        self.emitter.resource_id = resource_id

        await self.emitter.emit_workflow(
            "created",
            "资源生成任务已创建",
            progress=0,
        )

        try:
            orchestrator = Orchestrator(
                user_id=user_id,
                resource_id=resource_id,
                emitter=self.emitter,
            )
            results = await orchestrator.run(request)
            resources = await self._persist_results(
                user_id=user_id,
                resource_id=resource_id,
                results=results,
            )
            failed_agents = self._failed_agent_ids(results)
            bundle = self._build_bundle(
                resource_id=resource_id,
                request=request,
                resources=resources,
                failed_agents=failed_agents,
            )
            await self.store.update_resource_status(resource_id=resource_id, status=bundle.status)
            await self.emitter.emit_bundle(bundle, progress=99)
            await self.emitter.emit_done(bundle=bundle)
            return {"success": bundle.status != "failed", "bundle": bundle.model_dump(mode="json")}
        except Exception as exc:
            logger.exception("[ResourceWorkflow] 执行失败")
            await self.store.update_resource_status(resource_id=resource_id, status="failed")
            await self.emitter.emit_error(str(exc))
            await self.emitter.emit_done(bundle=None)
            return {"success": False, "error": str(exc)}

    async def _persist_results(
        self,
        *,
        user_id: int,
        resource_id: int,
        results: list[WorkerResult],
    ) -> list[GeneratedResourceItem]:
        resources: list[GeneratedResourceItem] = []
        for result in results:
            resource = self._to_resource_item(result)
            saved = await self.store.save_resource_item(
                resource_id=resource_id,
                user_id=user_id,
                item=resource,
            )
            saved_id = getattr(saved, "id", None)
            if saved_id is not None:
                resource.id = str(saved_id)
            resources.append(resource)
        return resources

    def _to_resource_item(self, result: WorkerResult) -> GeneratedResourceItem:
        agent_id = str(result.metadata.get("agent_id") or "")
        return GeneratedResourceItem(
            id=f"{self.emitter.resource_id}-{agent_id}" if agent_id else "",
            type=agent_id,
            title=result.title or f"{agent_id} 资源",
            format=result.file_type,
            content=result.content,
            summary=result.summary,
            summary_data=result.summary_data,
            metadata=result.metadata,
        )

    def _build_bundle(
        self,
        *,
        resource_id: int,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        failed_agents: list[str],
    ) -> ResourceBundle:
        selected_agents = request.enabled_agent_ids()
        status = "completed"
        if failed_agents and resources:
            status = "partial_completed"
        elif failed_agents and not resources:
            status = "failed"

        return ResourceBundle(
            id=str(resource_id),
            task_id=str(resource_id),
            topic=request.learning_need,
            learning_need=request.learning_need,
            selected_agents=selected_agents,
            resources=resources,
            study_path=self._build_study_path(resources),
            review_result=ReviewResult(
                passed=not failed_agents,
                score=100 if not failed_agents else max(40, 100 - len(failed_agents) * 10),
                failed_agents=failed_agents,
                suggestions=["部分资源生成失败，可调整 Agent 选择后重新生成。"] if failed_agents else [],
            ),
            status=status,
            metadata={"source": "resource_workflow", "selected_agents": selected_agents},
        )

    def _build_study_path(self, resources: list[GeneratedResourceItem]) -> list[StudyPathStep]:
        reasons = {
            "content": "先建立核心概念和知识背景。",
            "mindmap": "再用结构图梳理知识关系。",
            "diagram": "通过图解强化流程和关系理解。",
            "code": "用实操案例把知识落到实践。",
            "quiz": "通过练习检测掌握情况。",
            "reading": "最后用拓展阅读补充视野。",
        }
        return [
            StudyPathStep(
                order=index + 1,
                resource_type=resource.type,
                title=resource.title,
                reason=reasons.get(resource.type.value, "按当前学习目标推进。"),
            )
            for index, resource in enumerate(resources)
        ]

    def _failed_agent_ids(self, results: list[WorkerResult]) -> list[str]:
        failed: list[str] = []
        for result in results:
            if result.success:
                continue
            agent_id = str(result.metadata.get("agent_id") or "")
            if agent_id:
                failed.append(agent_id)
        return failed
