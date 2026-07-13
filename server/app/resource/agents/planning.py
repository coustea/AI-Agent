"""规划智能体 — 生成版本化结构化协同计划。"""

from __future__ import annotations

import json
import time

from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.research import research_web
from app.resource.schemas import (
    AgentResult,
    ResourceInput,
    ResourcePlan,
    validate_resource_plan,
)

logger = get_logger(__name__)


class ResearchDecision(BaseModel):
    """规划前的临时研究判断，不进入工作流状态或持久化结果。"""

    needs_research: bool = Field(description="是否需要外部事实核验")
    query: str = Field(default="", description="需要核验时使用的简短网页查询")


@register_agent
class PlanningAgent(BaseResourceAgent):
    """分析学习需求，生成 Markdown 格式的教学资源协同计划。"""

    agent_id = "planning"
    agent_name = "规划"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：分析学习需求，生成教学资源协同计划。"""
        title_prefix = input_data.learning_need[:32]
        logger.info("Agent[%s] 开始生成: learning_need=%s", self.agent_id, title_prefix)
        started = time.perf_counter()

        await self.emitter.send(self.agent_id, "running", "正在分析学习需求并构建协同计划", 10)

        research_context = await self._research_if_needed(input_data)
        prompt = prompts.get("resource").get("planning")
        input_text = self._build_planning_input(input_data, research_context)
        full_prompt = f"{prompt}\n\n{input_text}"

        await self.emitter.send(self.agent_id, "running", "正在生成协同计划", 25)

        # 提取预期的 agent IDs 用于校验
        agents = list(input_data.agent_config.get("enabled_agents", [])) if input_data.agent_config else []

        logger.info("Agent[%s] LLM 调用: input_len=%d", self.agent_id, len(full_prompt))
        llm_started = time.perf_counter()
        plan = await self.llm.ainvoke_json(ResourcePlan, full_prompt)
        llm_elapsed = int((time.perf_counter() - llm_started) * 1000)
        validate_resource_plan(plan, expected_agent_ids=agents)
        logger.info(
            "Agent[%s] LLM 完成: plan_len=%d agents=%s elapsed_ms=%d",
            self.agent_id, len(plan.model_dump_json()), plan.agent_ids, llm_elapsed,
        )

        await self.emitter.send(self.agent_id, "running", "协同计划已生成", 85)

        agent_ids = plan.agent_ids
        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: agent_count=%d plan_len=%d elapsed_ms=%d → %s",
            self.agent_id, len(agent_ids), len(plan.model_dump_json()), total_elapsed,
            plan.title,
        )
        result = AgentResult(
            success=True,
            content=plan.model_dump_json(),
            file_type="json",
            title=plan.title,
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
        return result

    async def _research_if_needed(self, input_data: ResourceInput) -> str:
        """仅在规划 Agent 判断需要事实核验时检索，结果不离开本方法。"""
        decision_prompt = "\n".join([
            "判断下列学习主题在制定教学计划前是否必须进行网页事实核验。",
            "仅当主题包含陌生/歧义术语、当前版本或标准、政策法规、近期数据、具体事实断言时返回 true。",
            "普通且稳定的基础知识、通用学习计划返回 false。不要为了补充内容而检索。",
            f"学习需求：{input_data.learning_need}",
            f"学习场景：{input_data.learning_scenario}",
        ])
        decision = await self.llm.ainvoke_json(ResearchDecision, decision_prompt)
        if not decision.needs_research:
            logger.info("Agent[%s] 研究判断: 无需检索", self.agent_id)
            return ""

        query = decision.query.strip() or input_data.learning_need.strip()
        await self.emitter.send(self.agent_id, "running", "正在核验陌生或时效性信息...", 18)
        try:
            report = await research_web(
                query,
                objective="仅为教学规划核验不确定、歧义或时效性事实",
                event_handler=self._handle_research_event,
            )
        except Exception as exc:
            logger.warning("Agent[%s] 规划核验失败: %s", self.agent_id, exc)
            return ""

        if not report.has_results:
            logger.info("Agent[%s] 规划核验未返回有效资料", self.agent_id)
            return ""
        evidence = []
        for source in report.sources[:6]:
            if source.title or source.summary:
                evidence.append(f"- {source.title}: {source.summary[:360]}")
        return "\n".join(evidence)[:3600]

    async def _handle_research_event(self, event: dict) -> None:
        status = event.get("status", "running")
        action = event.get("action", "核验网页资料")
        tool_status = {"running": "running", "done": "completed", "failed": "failed"}.get(
            status,
            "running",
        )
        await self.emitter.send(
            self.agent_id,
            "running",
            f"正在{action}..." if status == "running" else f"{action}{'已完成' if status == 'done' else '未完成'}",
            data={
                "phase": "planning_research",
                "tool_name": event.get("tool_name"),
                "tool_status": tool_status,
            },
        )

    def _build_planning_input(self, input_data: ResourceInput, research_context: str = "") -> str:
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
            agent_lines.append("必须且只能为以下 Agent 输出一个 JSON tasks 项：")
            agent_role_map = {
                "content": "讲解 Agent — 生成结构化教学讲解",
                "mindmap": "思维导图 Agent — 生成知识结构可视化",
                "quiz": "题目 Agent — 生成练习题和测试题",
                "code": "代码示例 Agent — 生成代码示例和编程练习",
                "reading": "阅读材料 Agent — 生成延伸阅读材料",
                "ppt": "PPT Agent — 基于基础资源生成课件",
                "cartoon": "动画 Agent — 基于基础资源生成动画讲解",
            }
            for agent_id in agents:
                role = agent_role_map.get(agent_id, agent_id)
                agent_lines.append(f"- `{agent_id}`：{role}")
            agent_lines.append("")
            agent_lines.append(
                f"你必须为上述 {len(agents)} 个 Agent 各生成一个 tasks 项。"
            )
            parts.append("\n".join(agent_lines))
        # 注入各 Agent 的用户配置参数，供规划时参考
        agent_configs = input_data.agent_config.get("agent_configs") if input_data.agent_config else None
        if agent_configs and isinstance(agent_configs, dict):
            # 只保留本次启用的 Agent 的配置
            filtered = {k: v for k, v in agent_configs.items() if k in agents} if agents else agent_configs
            if filtered:
                parts.append("## 各 Agent 用户配置参数\n" + json.dumps(filtered, ensure_ascii=False, indent=2))
        if research_context:
            parts.append(
                "## 仅供本规划阶段核验的临时事实资料\n"
                "以下资料只用于纠正规划中的事实判断；不要输出 URL、引用列表或原始搜索内容，"
                "也不要把它作为下游 Agent 的额外输入。\n"
                + research_context
            )
        # 拼装为完整规划输入文本
        return "\n\n".join(parts)
