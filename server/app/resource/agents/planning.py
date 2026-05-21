"""
规划智能体 — 分析学习需求和画像，生成结构化知识图谱和各 Agent 的个性化指令。
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import ExecutionPlan
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)


class PlanningAgent:
    """分析学习需求和画像，生成知识图谱和各 Agent 的个性化指令。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(
        self,
        learning_need: str,
        learning_scenario: str,
        profile: dict[str, Any],
        enabled_agents: list[str],
    ) -> ExecutionPlan:
        await self.emitter.emit_agent("planning", status="running", message="正在生成知识图谱")

        prompt = registry.get("resource/planning")
        input_text = self._build_input(learning_need, learning_scenario, profile, enabled_agents)

        plan = await self.llm.ainvoke_json(
            ExecutionPlan,
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )

        await self.emitter.emit_agent("planning", status="success", message="知识图谱生成完成")
        return plan

    def _build_input(
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
