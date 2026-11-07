"""规划智能体 — 生成版本化结构化协同计划。"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, load_resource_prompt, register_agent
from app.resource.agents.common import _format_profile
from app.resource.schemas import (
    AgentResult,
    ResourceInput,
    ResourcePlan,
    validate_resource_plan,
)

if TYPE_CHECKING:
    from app.resource.event import ResourceEvents

logger = get_logger(__name__)

_AGENT_ROLE_MAP: dict[str, str] = {
    "content": "讲解 Agent — 生成结构化教学讲解",
    "mindmap": "思维导图 Agent — 生成知识结构可视化",
    "quiz": "题目 Agent — 生成练习题和测试题",
    "code": "代码示例 Agent — 生成代码示例和编程练习",
    "reading": "阅读材料 Agent — 生成延伸阅读材料",
    "ppt": "PPT Agent — 基于基础资源生成课件",
    "cartoon": "动画 Agent — 基于基础资源生成动画讲解",
}


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求，生成结构化的教学资源协同计划。"""

    agent_id = "planning"
    agent_name = "规划"

    def __init__(self, emitter: ResourceEvents | None = None) -> None:
        """初始化规划 Agent 及其 LLM 客户端。"""
        super().__init__(emitter=emitter)
        self.llm = LLM(temperature=0.1)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """分析学习需求与学习者画像，生成结构化的教学资源协同计划。"""
        title_prefix = input_data.learning_need[:32]
        logger.info("Agent[%s] 开始生成: learning_need=%s", self.agent_id, title_prefix)
        started = time.perf_counter()

        await self.emitter.send(self.agent_id, "running", "正在分析学习需求并构建协同计划", 20)

        prompt = load_resource_prompt("planning")
        input_text = self._build_planning_input(input_data)
        full_prompt = f"{prompt}\n\n{input_text}"

        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        plan = await self.llm.json(ResourcePlan, full_prompt)
        validate_resource_plan(plan, expected_agent_ids=agents)

        await self.emitter.send(self.agent_id, "running", "协同计划已生成", 85)

        agent_ids = plan.agent_ids
        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: agent_count=%d elapsed_ms=%d",
            self.agent_id,
            len(agent_ids),
            total_elapsed,
        )
        return AgentResult(
            success=True,
            content=plan.model_dump_json(),
            file_type="json",
            title=input_data.learning_need[:64],
            summary=f"生成了包含 {len(agent_ids)} 个 Agent 任务的协同计划",
            metrics={
                "agent_count": len(agent_ids),
                "plan_length": len(plan.model_dump_json()),
            },
            metadata={
                "agent_id": "planning",
                "teaching_plan": plan.model_dump(mode="json"),
            },
        )

    @staticmethod
    def _build_planning_input(input_data: ResourceInput) -> str:
        """构建规划提示词输入内容（学习需求、场景、画像与硬性协同任务）。"""
        parts = [
            f"## 学习需求\n{input_data.learning_need}",
            f"## 学习场景\n{input_data.learning_scenario}",
        ]
        if input_data.profile:
            profile_text = _format_profile(input_data.profile)
            if profile_text:
                parts.append("## 学习者画像\n" + profile_text)

        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        if agents:
            agent_lines = [
                "## 本次必须生成的 Agent 协同任务（硬性约束）",
                "",
                "必须且只能为以下 Agent 输出一个 JSON tasks 项：",
                *(f"- `{aid}`：{_AGENT_ROLE_MAP.get(aid, aid)}" for aid in agents),
                "",
                f"你必须为上述 {len(agents)} 个 Agent 各生成一个 tasks 项。",
            ]
            parts.append("\n".join(agent_lines))

        agent_configs = input_data.agent_config.get("agent_configs") if input_data.agent_config else None
        if isinstance(agent_configs, dict):
            filtered = {k: v for k, v in agent_configs.items() if k in agents} if agents else agent_configs
            if filtered:
                parts.append("## 各 Agent 用户配置参数\n" + json.dumps(filtered, ensure_ascii=False, indent=2))
        return "\n\n".join(parts)
