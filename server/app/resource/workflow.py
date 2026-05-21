"""
资源生成工作流。

统一串联前端请求、Planning、多智能体资源生成、Review、资源保存和资源读取。
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.infra.logging import get_logger
from app.resource.agents import AGENT_CLASSES, PlanningAgent, ReviewAgent
from app.resource.events import AgentEventEmitter
from app.resource.schemas import (
    ExecutionPlan,
    KnowledgeGraph,
    ResourceGenerationRequest,
    ReviewResult,
    StudyPathStep,
    WorkerResult,
    WorkerState,
)
from app.resource.utils import load_user_profile

logger = get_logger(__name__)


class ResourceGenerationWorkflow:
    """资源生成主工作流。"""

    def __init__(self, emitter: AgentEventEmitter, resource_service: object) -> None:
        self.emitter = emitter
        self.resource_service = resource_service

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, Any]:
        """执行资源生成并返回前端资源包。"""
        resource_record = await self.resource_service.create_resource(user_id=user_id, request=request)
        resource_id = int(getattr(resource_record, "id", 0) or 0)
        self.emitter.resource_id = resource_id

        await self.emitter.emit_workflow("created", "资源生成任务已创建", progress=0)

        try:
            profile = await self._load_profile(user_id)
            enabled_agents = self._enabled_agents(request)
            if not enabled_agents:
                await self.resource_service.update_resource_status(resource_id=resource_id, status="failed")
                await self.emitter.emit_error("没有启用的 Agent")
                await self.emitter.emit_done(bundle=None)
                return {"success": False, "error": "没有启用的 Agent"}

            plan = await self._run_planning(request=request, profile=profile, enabled_agents=enabled_agents)
            results = await self._run_resource_agents(
                resource_id=resource_id,
                enabled_agents=enabled_agents,
                request=request,
                profile=profile,
                plan=plan,
            )
            review_result, study_path = await self._run_review(
                request=request,
                profile=profile,
                plan=plan,
                results=results,
            )

            await self.resource_service.save_generation_results(
                user_id=user_id,
                resource_id=resource_id,
                request=request,
                results=results,
                review_result=review_result,
                study_path=study_path,
                plan=plan,
            )

            bundle = await self.resource_service.get_resource_bundle(user_id, resource_id)
            if bundle is None:
                raise ValueError("资源保存后无法读取")
            await self.emitter.emit_bundle(bundle, progress=99)
            await self.emitter.emit_done(bundle=bundle)
            return {
                "success": bundle.status != "failed",
                "bundle": bundle.model_dump(mode="json"),
            }
        except Exception as exc:
            logger.exception("[ResourceGenerationWorkflow] 执行失败")
            await self.resource_service.update_resource_status(resource_id=resource_id, status="failed")
            await self.emitter.emit_error(str(exc))
            await self.emitter.emit_done(bundle=None)
            return {"success": False, "error": str(exc)}

    async def _run_planning(
        self,
        *,
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
        enabled_agents: list[str],
    ) -> ExecutionPlan:
        await self.emitter.emit_workflow("planning", "正在分析学习需求", progress=5)
        planner = PlanningAgent(self.emitter)
        try:
            plan = await planner.run(
                learning_need=request.learning_need,
                learning_scenario=request.learning_scenario,
                profile=profile,
                enabled_agents=enabled_agents,
            )
            await self.emitter.emit_workflow("planning_done", "知识图谱生成完成", progress=15)
            return plan
        except Exception as exc:
            error = str(exc)
            logger.exception("[ResourceGenerationWorkflow] PlanningAgent 异常")
            await self._emit_agent_failure("planning", error)
            await self.emitter.emit_workflow(
                "planning_fallback",
                "规划智能体失败，使用基础知识图谱继续生成",
                progress=15,
            )
            return ExecutionPlan(
                knowledge_graph=KnowledgeGraph(
                    topic=request.learning_need,
                    summary="PlanningAgent 失败，工作流使用学习需求生成基础知识图谱继续执行。",
                ),
                agent_instructions=[],
                personalization_summary=f"PlanningAgent 失败，已使用基础知识图谱继续生成: {error}",
            )

    async def _run_resource_agents(
        self,
        *,
        resource_id: int,
        enabled_agents: list[str],
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
        plan: ExecutionPlan,
    ) -> dict[str, WorkerResult]:
        await self.emitter.emit_workflow("generating", "并行生成资源", progress=20)
        instruction_map = {instruction.agent_id: instruction for instruction in plan.agent_instructions}
        results: dict[str, WorkerResult] = {}

        async def run_one(agent_id: str) -> None:
            try:
                state = WorkerState(
                    resource_id=resource_id,
                    learning_need=request.learning_need,
                    learning_scenario=request.learning_scenario,
                    agent_name=agent_id,
                    agent_config=request.agent_configs.get(agent_id, {}),
                    knowledge_graph=plan.knowledge_graph,
                    instruction=instruction_map.get(agent_id),
                    profile=profile,
                )
                agent = AGENT_CLASSES[agent_id](self.emitter)
                result = await agent.run(state)
                results[agent_id] = result
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
                    logger.warning("[ResourceGenerationWorkflow] Agent %s 执行失败: %s", agent_id, result.error)
                    await self._emit_agent_failure(agent_id, result.error or "Agent 返回失败")
            except Exception as exc:
                logger.exception("[ResourceGenerationWorkflow] Agent %s 异常", agent_id)
                error = str(exc)
                results[agent_id] = WorkerResult(
                    success=False,
                    error=error,
                    metadata={"agent_id": agent_id},
                )
                await self._emit_agent_failure(agent_id, error)

        await asyncio.gather(*(run_one(agent_id) for agent_id in enabled_agents))
        return results

    async def _emit_agent_failure(self, agent_id: str, error: str) -> None:
        await self.emitter.emit_agent(
            agent_id,
            status="failed",
            message=f"Agent {agent_id} 执行失败: {error}",
            payload={"error": error},
        )

    async def _run_review(
        self,
        *,
        request: ResourceGenerationRequest,
        profile: dict[str, Any],
        plan: ExecutionPlan,
        results: dict[str, WorkerResult],
    ) -> tuple[ReviewResult, list[StudyPathStep]]:
        await self.emitter.emit_workflow("reviewing", "质量审查中", progress=85)
        reviewer = ReviewAgent(self.emitter)
        try:
            return await reviewer.run(
                results=results,
                knowledge_graph=plan.knowledge_graph,
                profile=profile,
                learning_need=request.learning_need,
            )
        except Exception as exc:
            error = str(exc)
            logger.exception("[ResourceGenerationWorkflow] ReviewAgent 异常")
            await self._emit_agent_failure("review", error)
            failed_agents = [agent_id for agent_id, result in results.items() if not result.success]
            if "review" not in failed_agents:
                failed_agents.append("review")
            review_result = ReviewResult(
                passed=False,
                overall_score=0,
                consistency_score=0,
                personalization_score=0,
                issues=[f"ReviewAgent 执行失败: {error}"],
                suggestions=["已保留成功生成的资源，请优先人工检查资源一致性。"],
                failed_agents=failed_agents,
            )
            study_path = [
                StudyPathStep(
                    order=index + 1,
                    resource_type=agent_id,
                    title=result.title or f"{agent_id} 资源",
                    reason="审核智能体失败，按成功生成顺序保留资源。",
                )
                for index, (agent_id, result) in enumerate(results.items())
                if result.success
            ]
            return review_result, study_path

    def _enabled_agents(self, request: ResourceGenerationRequest) -> list[str]:
        if not request.selected_agents:
            return list(AGENT_CLASSES.keys())
        return [
            selection.agent_id.value
            for selection in request.selected_agents
            if selection.enabled and selection.agent_id.value in AGENT_CLASSES
        ]

    async def _load_profile(self, user_id: int) -> dict[str, Any]:
        try:
            return await load_user_profile(user_id)
        except Exception as exc:
            logger.warning("[ResourceGenerationWorkflow] 学习者画像加载失败: %s", exc)
            return {}
