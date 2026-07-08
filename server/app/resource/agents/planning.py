"""规划智能体 — 生成 Markdown 格式的教学资源协同计划。"""

from __future__ import annotations

import json
import time

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import (
    AgentResult,
    NodeInput,
    ResourceInput,
    ResourcePlan,
    PlanValidationError,
    validate_resource_plan,
)

logger = get_logger(__name__)

_MAX_PLAN_ATTEMPTS = 2


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求，生成 Markdown 格式的教学资源协同计划。"""

    agent_id = "planning"
    agent_name = "规划"
    research_enabled = False  # 规划阶段不需要搜索

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：分析学习需求，生成教学资源协同计划。"""
        title_prefix = input_data.learning_need[:32]
        logger.info("Agent[%s] 开始生成: learning_need=%s", self.agent_id, title_prefix)
        started = time.perf_counter()

        await self.emitter.send(self.agent_id, "running", "正在分析学习需求并构建协同计划", 10)

        prompt = prompts.get("resource").get("planning")
        input_text = self._build_planning_input(input_data)
        full_prompt = f"{prompt}\n\n{input_text}"

        await self.emitter.send(self.agent_id, "running", "正在生成协同计划", 25)

        # 提取预期的 agent IDs 用于校验
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []

        attempt_prompt = full_prompt
        plan: ResourcePlan | None = None

        for attempt in range(_MAX_PLAN_ATTEMPTS):
            try:
                logger.info("Agent[%s] LLM 调用: input_len=%d", self.agent_id, len(attempt_prompt))
                llm_started = time.perf_counter()
                response = await self.llm.ainvoke(attempt_prompt)
                content = response.content if hasattr(response, "content") else str(response)
                llm_elapsed = int((time.perf_counter() - llm_started) * 1000)

                # 提取标题：取第一行 # 标题
                title = ""
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("# "):
                        title = stripped[2:].strip()
                        break

                plan = ResourcePlan(content=content, title=title)
                logger.info(
                    "Agent[%s] LLM 完成: plan_len=%d agents=%s elapsed_ms=%d",
                    self.agent_id, len(plan.content), plan.agent_ids, llm_elapsed,
                )

                # 后端校验：非空 + agent 覆盖
                validate_resource_plan(plan, expected_agent_ids=agents if agents else None)
                break
            except (ValueError, PlanValidationError) as exc:
                if attempt + 1 >= _MAX_PLAN_ATTEMPTS:
                    raise
                attempt_elapsed = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "Agent[planning] 规划校验失败, 正在重试: attempt=%d error=%s elapsed_ms=%d",
                    attempt + 1, exc, attempt_elapsed,
                )
                await self.emitter.send(
                    self.agent_id,
                    "running",
                    "计划未通过校验，正在重新规划...",
                    50,
                )
                attempt_prompt = (
                    f"{full_prompt}\n\n"
                    "## 上次输出的校验错误\n"
                    f"{str(exc)[:1200]}\n\n"
                    "请重新生成完整计划，修正上述错误。"
                )

        if plan is None:
            raise ValueError("PlanningAgent did not produce a valid plan")

        await self.emitter.send(self.agent_id, "running", "协同计划已生成", 85)

        agent_ids = plan.agent_ids
        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: agent_count=%d plan_len=%d elapsed_ms=%d → %s",
            self.agent_id, len(agent_ids), len(plan.content), total_elapsed,
            plan.content[:200].replace("\n", " "),
        )
        result = AgentResult(
            success=True,
            content=plan.content,
            file_type="markdown",
            title=plan.title or input_data.learning_need[:32],
            summary=f"生成了包含 {len(agent_ids)} 个 Agent 任务的协同计划",
            metrics={
                "agent_count": len(agent_ids),
                "plan_length": len(plan.content),
            },
            metadata={
                "agent_id": "planning",
                "teaching_plan": plan.content,
            },
        )
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
        if input_data.profile:
            from app.resource.agents.common import _format_profile
            profile_text = _format_profile(input_data.profile)
            if profile_text:
                parts.append("## 学习者画像\n" + profile_text)
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []
        if agents:
            agent_lines = ["## 本次必须生成的 Agent 协同任务（硬性约束）"]
            agent_lines.append("")
            agent_lines.append("必须且只能包含以下 Agent 的 `### [agent_id]` 段落：")
            agent_role_map = {
                "content": "讲解 Agent — 生成结构化教学讲解",
                "mindmap": "思维导图 Agent — 生成知识结构可视化",
                "quiz": "题目 Agent — 生成练习题和测试题",
                "code": "代码示例 Agent — 生成代码示例和编程练习",
                "reading": "阅读材料 Agent — 生成延伸阅读材料",
                "ppt": "PPT Agent — 基于基础资源生成课件",
                "video": "视频 Agent — 基于基础资源生成讲解视频",
                "cartoon": "动画 Agent — 基于基础资源生成动画讲解",
            }
            for agent_id in agents:
                role = agent_role_map.get(agent_id, agent_id)
                agent_lines.append(f"- `### [{agent_id}]`：{role}")
            agent_lines.append("")
            agent_lines.append(
                f"你必须为上述 {len(agents)} 个 Agent 各生成一个 `### [agent_id]` 段落。"
            )
            parts.append("\n".join(agent_lines))
        # 注入各 Agent 的用户配置参数，供规划时参考
        agent_configs = input_data.agent_config.get("agent_configs") if input_data.agent_config else None
        if agent_configs and isinstance(agent_configs, dict):
            # 只保留本次启用的 Agent 的配置
            filtered = {k: v for k, v in agent_configs.items() if k in agents} if agents else agent_configs
            if filtered:
                parts.append("## 各 Agent 用户配置参数\n" + json.dumps(filtered, ensure_ascii=False, indent=2))
        return "\n\n".join(parts)
