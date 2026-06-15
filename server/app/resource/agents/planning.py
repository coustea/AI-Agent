"""规划智能体 — 分析学习需求，生成教学蓝图和各 Agent 个性化指令。

PlanningAgent 是多智能体模式的入口，它的输出（ExecutionPlan）包含：
  - blueprint: 教学蓝图（全局教学策略）
  - agent_instructions: 每个子 Agent 的个性化执行指令
"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
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
        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在分析学习需求并构建执行计划",
                progress=10,
            )

        prompt = prompts.get("resource").get("planning")
        # 自定义构建规划输入（包含学习需求、画像、场景、资源类型列表）
        input_text = self._build_planning_input(state)

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在调用大模型生成教学蓝图与各智能体指令",
                progress=25,
            )

        # LLM 结构化输出 → ExecutionPlan（含 blueprint + agent_instructions）
        plan = await self.llm.ainvoke_json(
            ExecutionPlan,
            f"{prompt}\n\n{input_text}",
            temperature=INFERENCE_TEMPERATURE,
        )

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="蓝图已生成，正在提取各智能体个性化指令",
                progress=85,
            )

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="finished",
                message="教学蓝图与执行计划已生成",
                progress=100,
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

    def _build_planning_input(self, state: WorkerState) -> str:
        """构建规划阶段的 LLM 输入文本。"""
        parts = [
            f"## 学习需求\n{state.learning_need}",
            f"## 学习场景\n{getattr(state, 'learning_scenario', 'self_study')}",
        ]
        # 添加学习者画像
        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像\n{profile_text}")
        # 添加需要生成的资源类型列表
        agents = list(state.agent_config.get("enabled_agents", [])) if state.agent_config else []
        if agents:
            parts.append(f"## 需要生成的资源类型\n{', '.join(agents)}")
        return "\n\n".join(parts)
