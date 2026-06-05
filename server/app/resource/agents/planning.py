"""规划智能体 — 分析学习需求，生成教学蓝图和各 Agent 个性化指令。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import ExecutionPlan, WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求，生成教学蓝图和各 Agent 个性化指令。"""

    agent_id = "planning"
    agent_name = "规划"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        """PlanningAgent 自行构建输入，不走通用 build_worker_base_context。"""
        from app.prompts import registry

        prompt = registry.get("resource/planning")
        input_text = self._build_planning_input(state)
        plan = await self.llm.ainvoke_json(
            ExecutionPlan,
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )

        return WorkerResult(
            success=True,
            content=plan.model_dump_json(indent=2),
            file_type="json",
            title="教学蓝图与执行计划",
            summary="PlanningAgent 生成了教学蓝图和各 Agent 个性化指令",
            metadata={
                "agent_id": "planning",
                "blueprint": plan.blueprint.model_dump(mode="json"),
                "instructions": {
                    inst.agent_id: inst.model_dump(mode="json")
                    for inst in plan.agent_instructions
                },
            },
        )
        
    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        # PlanningAgent overrides run directly, so this is just to satisfy ABC.
        raise NotImplementedError

    def _build_planning_input(self, state: WorkerState) -> str:
        parts = [
            f"## 学习需求\n{state.learning_need}",
            f"## 学习场景\n{getattr(state, 'learning_scenario', 'self_study')}",
        ]
        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像\n{profile_text}")
        agents = list(state.agent_config.get("enabled_agents", [])) if state.agent_config else []
        if agents:
            parts.append(f"## 需要生成的资源类型\n{', '.join(agents)}")
        return "\n\n".join(parts)
