# -*- coding: utf-8 -*-
"""LLM 规划器 (MasterAgent)。

使用 LLM 进行分层任务规划，支持单次规划和分层规划两种模式。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.logging import get_logger
from app.infra.llm import get_llm_manager
from app.resource.registry import (
    DEPENDS,
    LAYER_AGENTS,
    agent_name,
    agent_output,
    get_agent_planning_catalog,
    layer_name,
)
from app.resource.schemas import (
    AgentTask,
    LayerPlan,
    PlanningContext,
)
from app.utils.json import parse_first_json_object

logger = get_logger(__name__)


class LLMPlanner:
    """LLM 规划器：使用 LLM 进行分层任务规划。

    只负责当前层资源生成任务规划，不生成资源正文。
    """

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm or get_llm_manager().get_model("spark_max")

    async def plan(self, context: PlanningContext) -> LayerPlan:
        """使用 LLM 规划当前层；失败则抛出异常。"""
        layer = LAYER_AGENTS.get(context.layer, [])
        candidates = [a for a in layer if a in context.user_explicit_selection]
        explicit_set = set(context.user_explicit_selection)

        if not candidates:
            return LayerPlan(
                layer=context.layer,
                agents=[],
                reasoning="本层无待执行 Agent",
                fallback_used=False,
            )

        raw_plan = await self._get_plan(context=context, candidates=candidates)
        return self._sanitize(raw_plan, candidates, explicit_set, context)

    def plan_fallback(self, context: PlanningContext) -> LayerPlan:
        """规则兜底规划：当 LLM 规划失败时使用。"""
        layer = LAYER_AGENTS.get(context.layer, [])
        candidates = [a for a in layer if a in context.user_explicit_selection]
        explicit_set = set(context.user_explicit_selection)

        if not candidates:
            return LayerPlan(
                layer=context.layer,
                agents=[],
                reasoning="本层无待执行 Agent",
                fallback_used=True,
            )

        tasks = self._default_tasks(candidates, explicit_set, context)
        return LayerPlan(
            layer=context.layer,
            agents=tasks,
            reasoning=f"{layer_name(context.layer)} 使用规则兜底规划",
            fallback_used=True,
        )

    async def _get_plan(
        self,
        *,
        context: PlanningContext,
        candidates: list[str],
    ) -> dict[str, Any]:
        """调用 LLM 获取层规划。"""
        prompt = self._build_prompt(context=context, candidates=candidates)
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        logger.info("[LLMPlanner] 规划响应: %s", content)
        return parse_first_json_object(content)

    def _sanitize(
        self,
        plan: dict[str, Any],
        candidates: list[str],
        explicit_set: set[str],
        context: PlanningContext,
    ) -> LayerPlan:
        """清洗 LLM 规划结果。"""
        if int(plan.get("layer", context.layer)) != context.layer:
            logger.warning("[LLMPlanner] LLM 返回跨层规划: %s", plan.get("layer"))
            raise ValueError(
                f"LLM 返回了非当前层规划: 期望 layer={context.layer}, "
                f"实际 layer={plan.get('layer')}"
            )

        agents = plan.get("agents", [])
        if not isinstance(agents, list) or not agents:
            raise ValueError("LLM 返回空规划")

        allowed_deps = self._allowed_deps(context)
        sanitized: list[AgentTask] = []
        seen: set[str] = set()

        for index, raw_task in enumerate(agents):
            if not isinstance(raw_task, dict):
                continue

            agent_id = str(raw_task.get("agent_id") or "").strip()
            if agent_id in seen or agent_id not in candidates or agent_id not in explicit_set:
                continue

            # 合并依赖
            raw_deps = raw_task.get("depends_on")
            deps = raw_deps if isinstance(raw_deps, list) else []
            deps = [*DEPENDS.get(agent_id, []), *deps]
            deduped: list[str] = []
            for dep in deps:
                if isinstance(dep, str) and dep not in deduped:
                    deduped.append(dep)
            allowed = [dep for dep in deduped if dep in allowed_deps]

            # 合并配置
            default_config = context.question.agent_configs.model_dump().get(agent_id, {})
            llm_config = raw_task.get("config") if isinstance(raw_task.get("config"), dict) else {}
            input_params = raw_task.get("input_params") if isinstance(raw_task.get("input_params"), dict) else {}
            config = {**llm_config, **input_params, **default_config}

            try:
                priority = int(raw_task.get("priority", index))
            except (TypeError, ValueError):
                priority = index
            priority = max(0, priority)

            task_desc = str(
                raw_task.get("task_description")
                or self._default_desc(agent_id, context.question.learning_need)
            )
            constraints = raw_task.get("personalized_constraints", [])
            if not isinstance(constraints, list):
                constraints = []
            constraints = [*constraints, *self._profile_constraints(context)]

            output_req = raw_task.get("output_requirements")
            if not isinstance(output_req, dict):
                output_req = agent_output(agent_id)

            sanitized.append(AgentTask(
                agent_id=agent_id,
                layer=context.layer,
                layer_name=layer_name(context.layer),
                enabled=bool(raw_task.get("enabled", True)),
                resource_type=str(raw_task.get("resource_type") or agent_id),
                task_description=task_desc,
                depends_on=allowed,
                is_explicit=True,
                priority=priority,
                config=config,
                input_params=input_params,
                output_requirements=output_req,
                personalized_constraints=self._dedupe_constraints(str(item) for item in constraints if item),
                planning_reason=str(raw_task.get("planning_reason") or ""),
                failure_policy=str(raw_task.get("failure_policy") or "skip_on_dependency_failed"),
            ))
            seen.add(agent_id)

        sanitized = [task for task in sanitized if task.enabled]
        sanitized.sort(key=lambda item: item.priority)
        for index, task in enumerate(sanitized):
            task.priority = index

        if not sanitized:
            raise ValueError("LLM 规划校验后无合法 Agent")

        return LayerPlan(
            layer=context.layer,
            agents=sanitized,
            reasoning=str(
                plan.get("reasoning")
                or f"{layer_name(context.layer)} 规划完成"
            ),
            fallback_used=False,
        )

    def _default_tasks(
        self,
        candidates: list[str],
        explicit_set: set[str],
        context: PlanningContext,
    ) -> list[AgentTask]:
        """默认 Agent 任务规划。"""
        learning_need = context.question.learning_need
        tasks = []

        for i, agent_id in enumerate(candidates):
            agent_config = context.question.agent_configs.model_dump().get(agent_id, {})
            task_desc = self._default_desc(agent_id, learning_need)

            tasks.append(AgentTask(
                agent_id=agent_id,
                layer=context.layer,
                layer_name=layer_name(context.layer),
                task_description=task_desc,
                depends_on=[
                    dep for dep in DEPENDS.get(agent_id, [])
                    if dep in self._allowed_deps(context)
                ],
                is_explicit=agent_id in explicit_set,
                priority=i,
                config=agent_config,
                resource_type=agent_id,
                input_params={"topic": learning_need},
                output_requirements=agent_output(agent_id),
                personalized_constraints=self._dedupe_constraints([
                    "结合学习者画像",
                    *self._profile_constraints(context),
                ]),
                planning_reason=f"{agent_name(agent_id)}适合支撑{layer_name(context.layer)}的学习目标。",
                failure_policy="skip_on_dependency_failed",
            ))

        return tasks

    def _build_prompt(
        self,
        *,
        context: PlanningContext,
        candidates: list[str],
    ) -> str:
        """构造 LLM 提示词。"""
        current_agent_catalog = get_agent_planning_catalog(candidates)
        payload = {
            "layer": context.layer,
            "layer_name": layer_name(context.layer),
            "candidate_agents": candidates,
            "available_agent_catalog_for_current_layer": current_agent_catalog,
            "enabled_agents": context.user_explicit_selection,
            "completed_upstream_agents": list(context.upstream_results.keys()),
            "upstream_reports": context.upstream_reports,
            "learning_need": context.question.learning_need,
            "learning_scenario": context.question.learning_scenario.value,
            "agent_configs": context.question.agent_configs.model_dump(),
            "learner_profile_constraints": self._profile_constraints(context),
        }

        example_agent = candidates[0] if candidates else "content"
        format_example = {
            "layer": context.layer,
            "reasoning": "本层规划理由",
            "agents": [
                {
                    "agent_id": example_agent,
                    "enabled": True,
                    "task_description": "...",
                    "depends_on": [],
                    "priority": 0,
                    "resource_type": example_agent,
                    "input_params": {},
                    "output_requirements": {},
                    "personalized_constraints": [],
                    "planning_reason": "...",
                    "failure_policy": "skip_on_dependency_failed",
                }
            ],
        }

        return (
            "你是 MasterAgent，只负责规划当前 layer 的多智能体资源生成任务。\n"
            "你不能生成学习资源正文，不能规划其他 layer，不能选择 candidate_agents 之外的 Agent，"
            "也不能选择用户未启用的 Agent。\n"
            "请根据 available_agent_catalog_for_current_layer 理解每个 Agent 的职责：role 是 Agent 类名，"
            "description 是能力说明，best_for 是适用场景，depends_on 是推荐依赖，"
            "output 是输出格式和必须包含内容，planning_hint 是规划提示。\n"
            f'JSON 格式中的 "layer" 必须返回 {context.layer}，不能照抄其他层示例。\n'
            "输出必须是严格 JSON，不允许 Markdown、解释文本或代码块。\n"
            f"JSON 格式：{json.dumps(format_example, ensure_ascii=False)}\n\n"
            f"当前规划上下文：{json.dumps(payload, ensure_ascii=False)}"
        )

    def _allowed_deps(self, context: PlanningContext) -> set[str]:
        """当前层 Agent 只允许依赖已启用的更低层 Agent。"""
        lower: set[str] = set()
        for layer, agents in LAYER_AGENTS.items():
            if layer < context.layer:
                lower.update(agents)
        return lower & set(context.user_explicit_selection)

    def _default_desc(self, agent_id: str, learning_need: str) -> str:
        """构建默认任务描述。"""
        base = f"根据用户学习需求生成{agent_name(agent_id)}。"
        if learning_need:
            base = f"根据用户需求「{learning_need[:100]}」生成{agent_name(agent_id)}。"
        return base

    def _profile_constraints(self, context: PlanningContext) -> list[str]:
        """从画像维度生成规划约束。"""
        profile = context.learner_profile or {}
        profile_json = profile.get("profile_json") if isinstance(profile, dict) else None
        source = profile_json if isinstance(profile_json, dict) else profile
        if not isinstance(source, dict):
            return []

        constraints: list[str] = []
        dimensions = source.get("dimensions")
        if isinstance(dimensions, dict):
            for key, label in (
                ("weakness_points", "优先覆盖薄弱点"),
                ("knowledge_foundation", "匹配知识基础"),
                ("interaction_preference", "贴合交互偏好"),
                ("cognitive_style", "贴合认知风格"),
                ("learning_goal", "服务学习目标"),
            ):
                value = dimensions.get(key)
                if isinstance(value, dict) and value.get("summary"):
                    constraints.append(f"{label}: {str(value['summary'])[:120]}")
        return constraints[:6]

    def _dedupe_constraints(self, constraints: Any) -> list[str]:
        result: list[str] = []
        for item in constraints:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result
