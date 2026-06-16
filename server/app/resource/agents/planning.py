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
from app.resource.schemas import AgentResult, ExecutionPlan, NodeInput, ResourceInput
from app.resource.utils import format_learner_profile_for_prompt


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求，生成教学蓝图和各 Agent 个性化指令。"""

    agent_id = "planning"
    agent_name = "规划"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：分析学习需求，生成教学蓝图和执行计划。"""
        await self.emit_start("正在分析学习需求并构建执行计划", progress=10)

        prompt = prompts.get("resource").get("planning")
        input_text = self._build_planning_input(input_data)

        await self.emit_start("正在调用大模型生成教学蓝图与各智能体指令", progress=25)

        plan = await self.llm.ainvoke_json(
            ExecutionPlan,
            f"{prompt}\n\n{input_text}",
            temperature=INFERENCE_TEMPERATURE,
        )

        await self.emit_start("蓝图已生成，正在提取各智能体个性化指令", progress=85)

        result = AgentResult(
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
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点场景不支持 PlanningAgent。"""
        return AgentResult(
            success=False,
            error="planning agent 不用于路径节点资源生成",
            title="",
            summary="not supported",
            metadata={"agent_id": "planning"},
        )

    def _build_planning_input(self, input_data: ResourceInput) -> str:
        """构建规划阶段的 LLM 输入文本。"""
        parts = [
            f"## 学习需求\n{input_data.learning_need}",
            f"## 学习场景\n{input_data.learning_scenario}",
        ]
        profile_text = format_learner_profile_for_prompt(input_data.profile)
        if profile_text:
            parts.append(f"## 学习者画像\n{profile_text}")
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        if agents:
            parts.append(f"## 需要生成的资源类型\n{', '.join(agents)}")
        return "\n\n".join(parts)
