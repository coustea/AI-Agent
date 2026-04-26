"""
Coordinator Agent：画像加载 + 任务规划 + 分阶段编排 + SSE 实时推送。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from app.infra.llm import get_deepseek_reasoner_llm

from app.config import DEEPSEEK_REASONER_MODEL
from app.infra.logging import get_logger
from app.resource.events import AgentEventEmitter
from app.resource.exceptions import PlanningError
from app.resource.schemas import LearnerProfileSnapshot, PersonalizedTaskContext, ResourcePlan
from app.resource.utils import (
    AgentEntry,
    get_agent_registry,
    iter_plan_phases,
    build_default_resource_plan,
    merge_planned_tasks_into_plan,
    normalize_selected_resources,
    filter_tasks_by_selection,
    merge_extra,
    core_ready,
    save_resource,
    load_profile_snapshot,
    build_personalized_context,
)

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"
PLANNER_PROMPT_PATH = PROMPT_DIR / "planner.md"


class PlannerTaskParameterSchema(BaseModel):
    topic: str = ""
    major: str = ""
    course: str = ""
    gap: str = ""
    need: str = ""
    extra: str = ""
    target_md_path: str = ""
    edit_instruction: str = ""
    output_md_path: str = ""


class PlannerTaskSchema(BaseModel):
    agent: str
    description: str = ""
    parameters: PlannerTaskParameterSchema = Field(default_factory=PlannerTaskParameterSchema)


class PlannerPlanOutput(BaseModel):
    tasks: list[PlannerTaskSchema] = Field(default_factory=list)


class CoordinatorAgent:
    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_deepseek_reasoner_llm(streaming=False)
        self._planner_llm = self.llm.with_structured_output(PlannerPlanOutput)
        logger.info("[Coordinator] 初始化完成: planner_model=%s", DEEPSEEK_REASONER_MODEL)

    async def run(
        self,
        user_id: int,
        task: dict,
        selected_resources: list[str] | None = None,
    ) -> dict:
        logger.info(
            "[Coordinator] 开始执行资源生成: user_id=%s course=%r need=%r selected_resources=%s",
            user_id,
            task.get("course", ""),
            task.get("need", "review"),
            selected_resources,
        )
        await self.emitter.emit_workflow("profile_loading", "正在读取学习者画像...")
        snapshot = await self._safe_load_profile(user_id)
        personalized_context = build_personalized_context(snapshot, task)
        logger.info(
            "[Coordinator] 个性化上下文已生成: difficulty=%s styles=%s emphasis_count=%s",
            personalized_context.target_difficulty,
            personalized_context.explanation_style,
            len(personalized_context.emphasis),
        )

        allowed_agents = self._normalize_selected_resources(selected_resources)
        logger.info("[Coordinator] 归一化资源范围: %s", allowed_agents or "ALL")
        await self.emitter.emit_workflow("planning", "正在生成个性化资源计划...")
        resource_plan = await self._safe_build_plan(
            task=task,
            snapshot=snapshot,
            personalized_context=personalized_context,
            allowed_agents=allowed_agents,
        )
        logger.info(
            "[Coordinator] 资源计划已确定: core=%s enhancement=%s presentation=%s requested=%s execution=%s visible=%s hidden=%s",
            resource_plan.core_agents,
            resource_plan.enhancement_agents,
            resource_plan.presentation_agents,
            resource_plan.requested_agents,
            resource_plan.execution_agents,
            resource_plan.visible_agents,
            resource_plan.hidden_dependency_agents,
        )

        final: dict[str, dict] = {}
        context_bag: dict[str, dict] = {}
        completed_count = 0
        total_agents = len(resource_plan.ordered_agents)
        visible_set = set(resource_plan.visible_agents)
        hidden_set = set(resource_plan.hidden_dependency_agents)
        visible_completed_count = 0
        visible_total = len(resource_plan.visible_agents)

        for stage_key, stage_label, stage_agents in iter_plan_phases(resource_plan):
            if not stage_agents:
                logger.info("[Coordinator] 跳过空阶段: stage=%s", stage_key)
                continue

            # 每个阶段都只读取当前已完成的黑板结果，避免下游拿到半成品。
            logger.info(
                "[Coordinator] 进入阶段: stage=%s label=%s agents=%s shared_memory_keys=%s",
                stage_key,
                stage_label,
                stage_agents,
                list(context_bag.keys()),
            )
            await self.emitter.emit_workflow(
                stage_key,
                f"阶段 [{stage_label}] 已启动，正在分配 {len(stage_agents)} 个智能体...",
            )
            for agent_name in stage_agents:
                await self.emitter.emit_agent_status(
                    agent_name,
                    "queued",
                    f"等待进入 {stage_label}",
                    stage=stage_key,
                    visible=agent_name in visible_set,
                    dependency_only=agent_name in hidden_set,
                )

            futures = [
                asyncio.create_task(
                    self._run_agent_with_name(
                        agent_name=agent_name,
                        params=resource_plan.agent_parameters.get(agent_name, {}),
                        profile=snapshot.as_agent_profile(),
                        personalized_context=personalized_context,
                        shared_memory=context_bag,
                        visible_agents=visible_set,
                    )
                )
                for agent_name in stage_agents
            ]

            for future in asyncio.as_completed(futures):
                agent_name, result = await future
                final[agent_name] = result
                if result.get("success"):
                    # 只有成功产物才写回黑板，避免坏结果污染后续依赖链。
                    context_bag[agent_name] = result
                    logger.info("[Coordinator] 黑板已更新: agent=%s keys=%s", agent_name, list(context_bag.keys()))
                else:
                    logger.warning(
                        "[Coordinator] Agent 未产出可用结果: agent=%s error=%r",
                        agent_name,
                        result.get("error"),
                    )
                completed_count += 1
                if agent_name in visible_set:
                    visible_completed_count += 1
                await self.emitter.emit_bundle_update(
                    completed=completed_count,
                    total=total_agents,
                    core_ready=self._core_ready(resource_plan, final),
                    latest_agent=agent_name,
                    visible_completed=visible_completed_count,
                    visible_total=visible_total,
                )
            logger.info("[Coordinator] 阶段结束: stage=%s completed=%s/%s", stage_key, completed_count, total_agents)

        await self.emitter.emit_workflow("persisting", "正在保存本次资源包...")
        try:
            await self._save_resource(user_id, task, resource_plan, final)
            await self.emitter.emit_agent_log("coordinator", "资源包已入库")
        except Exception as exc:
            logger.error("[Coordinator] 保存资源记录失败: %s", exc, exc_info=exc)
            await self.emitter.emit_agent_log("coordinator", f"资源包保存失败，将仅保留本次流式结果：{exc}")

        logger.info("[Coordinator] 执行结束: user_id=%s completed_agents=%s visible_agents=%s", user_id, list(final.keys()), resource_plan.visible_agents)
        await self.emitter.emit_done("资源包构建完成")
        visible_final = {
            agent: final[agent]
            for agent in resource_plan.visible_agents
            if agent in final
        }
        return visible_final

    async def _safe_load_profile(self, user_id: int) -> LearnerProfileSnapshot:
        try:
            snapshot = await load_profile_snapshot(user_id)
            summary = snapshot.profile_summary or "暂无长期画像"
            logger.info(
                "[Coordinator] 画像快照加载成功: user_id=%s major=%r knowledge_score=%r",
                user_id,
                snapshot.major,
                snapshot.knowledge_level_score,
            )
            await self.emitter.emit_agent_log("coordinator", f"画像加载成功：{summary}")
            return snapshot
        except Exception as exc:
            logger.error("[Coordinator] 画像加载失败: %s", exc, exc_info=exc)
            await self.emitter.emit_agent_log("coordinator", f"画像加载失败，将使用默认画像上下文：{exc}")
            return LearnerProfileSnapshot(user_id=user_id)

    async def _safe_build_plan(
        self,
        task: dict,
        snapshot: LearnerProfileSnapshot,
        personalized_context: PersonalizedTaskContext,
        allowed_agents: list[str] | None,
    ) -> ResourcePlan:
        base_plan = build_default_resource_plan(task, allowed_agents)
        logger.info(
            "[Coordinator] 默认资源计划已构建: ordered_agents=%s requested=%s execution=%s visible=%s hidden=%s",
            base_plan.ordered_agents,
            base_plan.requested_agents,
            base_plan.execution_agents,
            base_plan.visible_agents,
            base_plan.hidden_dependency_agents,
        )
        for parameters in base_plan.agent_parameters.values():
            # 这里先补齐画像增强参数，Planner 失败时也能继续执行默认流程。
            parameters["major"] = snapshot.major or parameters.get("major", "")
            parameters["extra"] = self._merge_extra(
                parameters.get("extra", ""),
                personalized_context,
            )

        try:
            planned_tasks = await self._plan(
                task=task,
                snapshot=snapshot,
                personalized_context=personalized_context,
                allowed_agents=base_plan.execution_agents,
                requested_agents=base_plan.requested_agents,
                hidden_dependency_agents=base_plan.hidden_dependency_agents,
            )
            logger.info("[Coordinator] Planner 规划成功，开始合并参数")
            return merge_planned_tasks_into_plan(base_plan, planned_tasks)
        except PlanningError as exc:
            logger.error("[Coordinator] 规划失败: %s", exc)
            await self.emitter.emit_agent_log("coordinator", f"规划失败，使用默认资源计划：{exc}")
            return base_plan
        except Exception as exc:
            logger.error("[Coordinator] 规划异常: %s", exc, exc_info=exc)
            await self.emitter.emit_agent_log("coordinator", "规划异常，使用默认资源计划")
            return base_plan

    async def _plan(
        self,
        task: dict,
        snapshot: LearnerProfileSnapshot,
        personalized_context: PersonalizedTaskContext,
        allowed_agents: list[str] | None,
        requested_agents: list[str] | None = None,
        hidden_dependency_agents: list[str] | None = None,
    ) -> list[dict]:
        if not PLANNER_PROMPT_PATH.exists():
            raise PlanningError(f"Planner prompt 不存在: {PLANNER_PROMPT_PATH}")

        resource_scope = (
            "未指定，默认生成全部资源类型。"
            if allowed_agents is None
            else (
                f"执行范围(含依赖补全): {', '.join(allowed_agents)}；"
                f"用户请求返回: {', '.join(requested_agents or [])}；"
                f"依赖补全(默认不返回前端): {', '.join(hidden_dependency_agents or []) or '无'}"
            )
        )
        prompt_text = PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
        formatted = prompt_text.format(
            user_input=json.dumps(task, ensure_ascii=False),
            profile=json.dumps(snapshot.as_agent_profile(), ensure_ascii=False),
            personalized_context=json.dumps(personalized_context.as_prompt_context(), ensure_ascii=False),
            resource_scope=resource_scope,
        )
        messages = [
            SystemMessage(content=formatted),
            HumanMessage(content="请根据以上信息生成资源任务规划。"),
        ]
        logger.info(
            "[Coordinator] 正在调用 Planner (structured_output): course=%r allowed_agents=%s prompt_path=%s",
            task.get("course", ""),
            allowed_agents or "ALL",
            PLANNER_PROMPT_PATH,
        )
        response = await self._planner_llm.ainvoke(messages)
        if not isinstance(response, PlannerPlanOutput):
            raise PlanningError(f"Planner 返回类型异常: {type(response).__name__}")

        tasks = [t.model_dump() for t in response.tasks]

        logger.info("[Coordinator] Planner 返回 %s 个任务", len(tasks))
        return self._filter_tasks_by_selection(tasks, allowed_agents)

    async def _run_agent(
        self,
        agent_name: str,
        params: dict,
        profile: dict,
        personalized_context: PersonalizedTaskContext,
        shared_memory: dict,
        visible_agents: set[str] | None = None,
    ) -> dict:
        entry = get_agent_registry()[agent_name]
        is_visible = True if visible_agents is None else (agent_name in visible_agents)
        logger.info(
            "[Coordinator] Agent 启动: agent=%s stage=%s visible=%s params_keys=%s shared_memory_keys=%s",
            agent_name,
            entry.stage,
            is_visible,
            list(params.keys()),
            list(shared_memory.keys()),
        )
        await self.emitter.emit_agent_status(
            agent_name,
            "running",
            f"{entry.role} 正在执行 {entry.desc}",
            visible=is_visible,
            dependency_only=not is_visible,
        )

        profile_summary = profile.get("profile_summary") or "暂无稳定画像摘要"
        await self.emitter.emit_agent_log(agent_name, f"已注入学习画像：{profile_summary}")
        if shared_memory:
            await self.emitter.emit_agent_log(agent_name, f"已读取上游成果：{', '.join(shared_memory.keys())}")
        else:
            await self.emitter.emit_agent_log(agent_name, "当前作为首批智能体启动，无上游成果依赖")

        kwargs: dict[str, Any] = {
            "topic": params.get("topic", ""),
            "course": params.get("course", ""),
            "major": params.get("major", ""),
            "gap": params.get("gap", ""),
            "user_profile": profile,
            "shared_memory": shared_memory,
            **entry.extra_kwargs,
        }
        for key in (
            "target_md_path",
            "edit_instruction",
            "output_md_path",
            "template_id",
            "template_source_url",
            "template_config_url",
        ):
            if key in params:
                kwargs[key] = params.get(key)
        if agent_name == "mindmap":
            # 导图 Agent 需要额外的学习目标和补充说明来调整导图粒度。
            kwargs["need"] = params.get("need", "review")
            kwargs["extra"] = params.get("extra", "")

        try:
            logger.info("[Coordinator] 调用 Agent 方法: agent=%s method=%s", agent_name, entry.method)
            fn = getattr(entry.agent_loader(), entry.method)
            result = await fn(**kwargs)
        except Exception as exc:
            logger.error("[Coordinator] Agent %s 执行失败: %s", agent_name, exc, exc_info=exc)
            message = str(exc)
            await self.emitter.emit_agent_status(agent_name, "failed", message)
            return {
                "success": False,
                "type": entry.type,
                "title": entry.role,
                "content": "",
                "error": message,
            }

        success = bool(result.get("success"))
        if success:
            summary = entry.result_summary(result)
            logger.info("[Coordinator] Agent 执行成功: agent=%s summary=%s", agent_name, summary)
            await self.emitter.emit_agent_status(
                agent_name,
                "success",
                f"生成完成：{summary}",
                visible=is_visible,
                dependency_only=not is_visible,
            )
            if is_visible:
                await self.emitter.emit_artifact_ready(agent_name, result)
            else:
                await self.emitter.emit_agent_log(
                    agent_name,
                    "该资源属于依赖补全产物，已用于下游执行，默认不对前端返回。",
                    visible=False,
                    dependency_only=True,
                )
        else:
            logger.warning(
                "[Coordinator] Agent 执行完成但未成功: agent=%s error=%r",
                agent_name,
                result.get("error"),
            )
            await self.emitter.emit_agent_status(
                agent_name,
                "failed",
                result.get("error", "生成失败"),
                visible=is_visible,
                dependency_only=not is_visible,
            )
        return result

    async def _run_agent_with_name(
        self,
        agent_name: str,
        params: dict,
        profile: dict,
        personalized_context: PersonalizedTaskContext,
        shared_memory: dict,
        visible_agents: set[str] | None = None,
    ) -> tuple[str, dict]:
        result = await self._run_agent(
            agent_name=agent_name,
            params=params,
            profile=profile,
            personalized_context=personalized_context,
            shared_memory=shared_memory,
            visible_agents=visible_agents,
        )
        return agent_name, result

    @staticmethod
    def _merge_extra(existing_extra: str, personalized_context: PersonalizedTaskContext) -> str:
        return merge_extra(existing_extra, personalized_context)

    @staticmethod
    def _normalize_selected_resources(selected_resources: list[str] | None) -> list[str] | None:
        return normalize_selected_resources(selected_resources)

    @staticmethod
    def _filter_tasks_by_selection(tasks: list[dict], allowed_agents: list[str] | None) -> list[dict]:
        return filter_tasks_by_selection(tasks, allowed_agents)

    @staticmethod
    def _core_ready(plan: ResourcePlan, results: dict[str, dict]) -> bool:
        return core_ready(plan, results)

    @staticmethod
    async def _save_resource(user_id: int, task: dict, resource_plan: ResourcePlan, results: dict) -> None:
        await save_resource(user_id, task, resource_plan, results)
