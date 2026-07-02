"""规划智能体 — 分析学习需求，生成总体教学大纲（TeachingPlan）。

PlanningAgent 是多智能体模式的入口，它的唯一输出是 TeachingPlan，定义了全局教学方向与大纲。
当 LLM 返回空 agent_assignments 时自动重试一次。
"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput, TeachingPlan

logger = get_logger(__name__)

# 当 agent_assignments 为空时的最大重试次数
_MAX_EMPTY_ASSIGNMENTS_RETRIES = 1


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

        plan = await self.llm.ainvoke_json(
            TeachingPlan,
            full_prompt,
            temperature=INFERENCE_TEMPERATURE,
            max_attempts=2,
        )

        expected_agents = set(input_data.agent_config.get("enabled_agents", []))

        # LLM 返回空 agent_assignments 时重试一次（注入错误反馈）
        if not plan.agent_assignments and expected_agents:
            logger.warning(
                "Agent[planning] agent_assignments 为空，正在重试 (expected=%s)",
                sorted(expected_agents),
            )
            await self.emitter.send(
                self.agent_id, "running",
                "首次生成指派为空，正在重试...", 50,
            )
            retry_prompt = (
                f"{full_prompt}\n\n"
                "【错误反馈】你上一次返回了 agent_assignments: []（空数组），这是严重错误。\n"
                f"你必须为以下 Agent 各生成一条 assignment：{sorted(expected_agents)}。\n"
                "agent_assignments 绝不能为空数组 []。"
            )
            plan = await self.llm.ainvoke_json(
                TeachingPlan,
                retry_prompt,
                temperature=INFERENCE_TEMPERATURE,
                max_attempts=2,
            )

        # 校验 assignments 与 enabled_agents 一致
        if expected_agents:
            assigned_agents = {a.agent_id for a in plan.agent_assignments}
            if assigned_agents != expected_agents:
                raise ValueError(
                    "TeachingPlan assignments do not match selected base Agents: "
                    f"missing={sorted(expected_agents - assigned_agents)} "
                    f"unexpected={sorted(assigned_agents - expected_agents)}"
                )

        await self.emitter.send(self.agent_id, "running", "教学方向与大纲已生成", 85)

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
            parts.append(input_data.profile)
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        if agents:
            agent_lines = ["## 必须生成的 Agent 指派（硬性约束）"]
            agent_lines.append("")
            agent_lines.append("你必须且只能为以下 Agent 生成 agent_assignments，不多不少：")
            agent_role_map = {
                "content": "讲解 Agent — 生成结构化教学讲解",
                "mindmap": "思维导图 Agent — 生成知识结构可视化",
                "quiz": "题目 Agent — 生成练习题和测试题",
                "code": "代码示例 Agent — 生成代码示例和编程练习",
                "reading": "阅读材料 Agent — 生成延伸阅读材料",
            }
            for agent_id in agents:
                role = agent_role_map.get(agent_id, agent_id)
                agent_lines.append(f"- `{agent_id}`（{role}）")
            agent_lines.append("")
            agent_lines.append("每个 Agent 必须有且仅有一条 assignment，agent_id 必须与上述列表完全一致。")
            agent_lines.append("")
            agent_lines.append(
                "【严禁】agent_assignments 为空数组 []。"
                f"你必须为上述 {len(agents)} 个 Agent 各生成一条 assignment，"
                "缺少任何一个都是错误。"
            )
            parts.append("\n".join(agent_lines))
        return "\n\n".join(parts)
