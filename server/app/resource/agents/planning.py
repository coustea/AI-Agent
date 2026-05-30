"""
规划智能体 — 分析学习需求和画像，生成结构化教学蓝图和各 Agent 的个性化指令。
"""

from __future__ import annotations

import time

from typing import Any

from app.infra.llm import get_llm
from app.infra.logging import get_module_logger
from app.prompts import registry
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.events import AgentEventEmitter
from app.resource.schemas import ExecutionPlan, WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt

logger = get_module_logger("resource", sub="planning")


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求和画像，生成教学蓝图和各 Agent 的个性化指令。"""

    agent_id = "planning"
    agent_name = "规划"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        """PlanningAgent uses its own run() because it has a different input/output contract."""
        start = time.perf_counter()
        logger.info("Agent[planning] 启动: learning_need=%s", state.learning_need[:50])

        await self.emitter.emit_agent("planning", status="running", message="正在分析你的学习需求")
        await self.emitter.emit_agent_action(
            "planning", "analyze", detail="正在分析你的学习需求",
            current_step=1, total_steps=3, step_label="分析需求", progress=10,
        )

        prompt = registry.get("resource/planning")
        input_text = self._build_planning_input(
            state.learning_need,
            state.learning_scenario if hasattr(state, 'learning_scenario') else "self_study",
            state.profile,
            list(state.agent_config.get("enabled_agents", [])) if state.agent_config else [],
        )

        await self.emitter.emit_agent_action(
            "planning", "plan", detail="正在梳理知识点结构",
            current_step=2, total_steps=3, step_label="梳理结构", progress=40,
        )

        plan = await self.llm.ainvoke_json(
            ExecutionPlan,
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )

        elapsed = time.perf_counter() - start
        logger.debug("Agent[planning] LLM 调用完成: %.2fs", elapsed)

        await self.emitter.emit_agent_action(
            "planning", "done", detail="教学蓝图规划完成",
            current_step=3, total_steps=3, step_label="规划完成", progress=100,
        )
        await self.emitter.emit_agent("planning", status="success", message="教学蓝图规划完成", progress=100)

        elapsed = time.perf_counter() - start
        logger.info("Agent[planning] 完成: %.2fs", elapsed)

        return WorkerResult(
            success=True,
            content=plan.model_dump_json(indent=2),
            file_type="json",
            title="教学蓝图与执行计划",
            summary="PlanningAgent 生成了教学蓝图和各 Agent 个性化指令",
            metadata={"agent_id": "planning", "blueprint": plan.blueprint.model_dump(mode="json"), "instructions": {inst.agent_id: inst.model_dump(mode="json") for inst in plan.agent_instructions}},
        )

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """Fallback — PlanningAgent uses run() directly."""
        return await self.run(state)

    def _build_planning_input(
        self,
        need: str,
        scenario: str,
        profile: dict[str, Any],
        agents: list[str],
    ) -> str:
        parts = [
            f"## 学习需求\n{need}",
            f"## 学习场景\n{scenario}",
        ]
        profile_text = format_learner_profile_for_prompt(profile)
        if profile_text:
            parts.append(f"## 学习者画像\n{profile_text}")
        parts.append(f"## 需要生成的资源类型\n{', '.join(agents)}")
        return "\n\n".join(parts)
