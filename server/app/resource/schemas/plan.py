"""多智能体资源规划 — Markdown 格式。

PlanningAgent 输出纯 Markdown 协同计划，不再使用结构化 JSON schema。

设计原则：
- LLM 生成 Markdown 远比生成复杂 JSON schema 可靠
- 计划只在 Agent 之间传递，不需要展示给用户
- 每个 Agent 从完整 Markdown 中提取自己的任务段落
- 后端只做最轻量的校验：非空 + agent_id 覆盖检查
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field


# ── 资源规划 ────────────────────────────────────────────────────────────


class ResourcePlan(BaseModel):
    """PlanningAgent 输出的 Markdown 协同计划。

    content 是完整的 Markdown 文本，包含 7 个标准段落：
    1. 用户需求理解
    2. 整体资源生成纲要
    3. 统一学习主线
    4. 资源之间的协同关系
    5. Agent 协同任务（每个 Agent 一个子段落）
    6. 聚合资源整合要求
    7. 全局一致性要求

    agent_ids 从 content 中的 `### [agent_id]` 标题自动提取。
    """

    model_config = ConfigDict(extra="ignore")

    content: str = Field(min_length=1, description="完整的 Markdown 协同计划")
    title: str = Field(default="", max_length=200, description="资源包标题")

    @property
    def agent_ids(self) -> list[str]:
        """从 Markdown 中提取所有 Agent 协同任务段落对应的 agent_id。

        匹配格式：### [content] 或 ### [mindmap] 等
        """
        return re.findall(r"^###\s*\[(\w+)\]", self.content, re.MULTILINE)

    def has_agent(self, agent_id: str) -> bool:
        """检查计划中是否包含指定 Agent 的协同任务段落。"""
        return f"[{agent_id}]" in self.content

    def extract_agent_section(self, agent_id: str) -> str:
        """提取指定 Agent 的协同任务段落内容。

        从 ### [agent_id] 开始，到下一个 ### 或文档结束。
        """
        pattern = rf"^###\s*\[{re.escape(agent_id)}\]\s*$"
        lines = self.content.splitlines()
        in_section = False
        section_lines: list[str] = []

        for line in lines:
            if re.match(pattern, line.strip()):
                in_section = True
                section_lines.append(line)
                continue
            if in_section:
                # 下一个 ### 开头表示新段落开始
                if line.strip().startswith("### "):
                    break
                section_lines.append(line)

        return "\n".join(section_lines).strip()


# ── 交接与下游 ─────────────────────────────────────────────────────────


class DownstreamContext(BaseModel):
    """基础 Agent 给聚合 Agent 的交接内容。"""

    model_config = ConfigDict(extra="ignore")

    source_agent: str
    title: str = ""
    one_sentence_summary: str = ""
    materials: list[str] = Field(default_factory=list, max_length=12)


# ── 后端校验 ────────────────────────────────────────────────────────────


class PlanValidationError(ValueError):
    """ResourcePlan 校验失败。"""


def validate_resource_plan(plan: ResourcePlan, expected_agent_ids: list[str] | None = None) -> ResourcePlan:
    """对 PlanningAgent 输出的 Markdown 计划执行后端校验。

    校验规则：
    1. content 非空
    2. 如果提供了 expected_agent_ids，检查计划中是否包含所有预期的 Agent
    """
    errors: list[str] = []

    if not plan.content.strip():
        errors.append("计划内容为空")

    if expected_agent_ids:
        plan_ids = set(plan.agent_ids)
        expected_ids = set(expected_agent_ids)
        missing = expected_ids - plan_ids
        if missing:
            errors.append(f"计划缺少以下 Agent 的协同任务段落: {sorted(missing)}")

    if errors:
        raise PlanValidationError("; ".join(errors))

    return plan
