"""规划智能体 — 生成全局教学计划和可直接派发的 Worker 任务。"""

from __future__ import annotations

import json

from app.config import DEFAULT_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import (
    AgentResult,
    NodeInput,
    ResourceInput,
    TeachingPlan,
)

logger = get_logger(__name__)

_MAX_PLAN_ATTEMPTS = 2


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
        await self.emitter.send(self.agent_id, "running", "正在分析学习需求并构建教学方向与大纲", 10)

        prompt = prompts.get("resource").get("planning")
        input_text = self._build_planning_input(input_data)
        full_prompt = f"{prompt}\n\n{input_text}"

        await self.emitter.send(self.agent_id, "running", "正在生成教学方向与大纲", 25)

        attempt_prompt = full_prompt
        plan: TeachingPlan | None = None

        for attempt in range(_MAX_PLAN_ATTEMPTS):
            try:
                plan = await self.llm.ainvoke_json(
                    TeachingPlan,
                    attempt_prompt,
                    temperature=DEFAULT_TEMPERATURE,
                )
                break
            except ValueError as exc:
                if attempt + 1 >= _MAX_PLAN_ATTEMPTS:
                    raise
                logger.warning(
                    "Agent[planning] 计划契约校验失败，正在重试: %s",
                    exc,
                )
                await self.emitter.send(
                    self.agent_id,
                    "running",
                    "计划任务契约未通过校验，正在重新规划...",
                    50,
                )
                attempt_prompt = (
                    f"{full_prompt}\n\n"
                    "## 上次输出的校验错误\n"
                    f"{str(exc)[:1200]}\n\n"
                    "请重新生成完整计划，修正上述错误。不要省略或猜测任何 Worker 键。"
                )

        if plan is None:
            raise ValueError("PlanningAgent did not produce a valid TeachingPlan")

        await self.emitter.send(self.agent_id, "running", "教学方向与大纲已生成", 85)

        result = AgentResult(
            success=True,
            content=plan.model_dump_json(indent=2),
            file_type="json",
            title="教学方向与大纲",
            summary="PlanningAgent 生成了总体教学方向、概要和大纲",
            metrics={
                "outline_count": len(plan.outline),
                "worker_task_count": len(plan.worker_tasks),
            },
            metadata={
                "agent_id": "planning",
                "teaching_plan": plan.model_dump(mode="json"),
            },
        )
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
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
        if input_data.profile:
            profile_text = (
                json.dumps(input_data.profile, ensure_ascii=False, indent=2)
                if isinstance(input_data.profile, dict)
                else input_data.profile
            )
            parts.append(f"## 学习者画像\n{profile_text}")
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        if agents:
            agent_lines = ["## 本次必须生成的 Worker Tasks（硬性约束）"]
            agent_lines.append("")
            agent_lines.append("`worker_tasks` 必须且只能包含以下键，不多不少：")
            agent_role_map = {
                "content": ("讲解 Agent — 生成结构化教学讲解", "markdown"),
                "mindmap": ("思维导图 Agent — 生成知识结构可视化", "markdown"),
                "quiz": ("题目 Agent — 生成练习题和测试题", "json"),
                "code": ("代码示例 Agent — 生成代码示例和编程练习", "markdown"),
                "reading": ("阅读材料 Agent — 生成延伸阅读材料", "json"),
            }
            for agent_id in agents:
                role, output_format = agent_role_map[agent_id]
                agent_lines.append(
                    f"- `{agent_id}`：{role}；`deliverable.format` 必须为 `{output_format}`"
                )
            agent_lines.append("")
            agent_lines.append(
                f"你必须为上述 {len(agents)} 个 Agent 各生成一个完整 WorkerTask 对象；"
                "`worker_tasks` 是对象映射，不是数组，不要输出 agent_id 字段。"
            )
            parts.append("\n".join(agent_lines))
        return "\n\n".join(parts)
