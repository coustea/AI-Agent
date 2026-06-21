"""规划智能体 — 分析学习需求，生成总体教学大纲（TeachingPlan）。

PlanningAgent 是多智能体模式的入口，它的唯一输出是 TeachingPlan，定义了全局教学方向与大纲。
"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput, TeachingPlan


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求，生成全局教学大纲（TeachingPlan）。"""

    agent_id = "planning"
    agent_name = "规划"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：分析学习需求，生成总体教学方向、概要和大纲。"""
        await self.emitter.emit_agent_step(self.agent_id, phase="start", message="正在分析学习需求并构建教学方向与大纲", progress=10)

        prompt = prompts.get("resource").get("planning")
        input_text = self._build_planning_input(input_data)

        await self.emitter.emit_agent_step(self.agent_id, phase="start", message="正在调用大模型生成教学方向与大纲", progress=25)

        plan = await self.llm.ainvoke_json(
            TeachingPlan,
            f"{prompt}\n\n{input_text}",
            temperature=INFERENCE_TEMPERATURE,
        )

        if plan.agent_assignments:
            expected_agents = set(input_data.agent_config.get("enabled_agents", []))
            assigned_agents = {assignment.agent_id for assignment in plan.agent_assignments}
            if assigned_agents != expected_agents:
                raise ValueError(
                    "TeachingPlan assignments do not match selected base Agents: "
                    f"missing={sorted(expected_agents - assigned_agents)} "
                    f"unexpected={sorted(assigned_agents - expected_agents)}"
                )

        await self.emitter.emit_agent_step(self.agent_id, phase="start", message="教学方向与大纲已生成", progress=85)

        result = AgentResult(
            success=True,
            content=plan.model_dump_json(indent=2),
            file_type="json",
            title="教学方向与大纲",
            summary="PlanningAgent 生成了总体教学方向、概要和大纲",
            metrics={"outline_count": len(plan.outline)},
            metadata={
                "agent_id": "planning",
                "teaching_plan": plan.model_dump(mode="json"),
            },
        )
        await self.emitter.emit_agent_snapshot(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result


    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点场景不支持 PlanningAgent — 规划 agent 仅用于多智能体入口。"""
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
        # profile 已经是 Markdown 格式，直接使用
        if input_data.profile:
            parts.append(input_data.profile)
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        if agents:
            parts.append(f"## 需要生成的资源类型\n{', '.join(agents)}")
        return "\n\n".join(parts)
