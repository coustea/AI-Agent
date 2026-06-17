"""Teaching blueprint and planning models — PlanningAgent output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TeachingOutlineItem(BaseModel):
    """PlanningAgent 生成的全局教学大纲项，不绑定具体 agent。"""

    id: str = Field(pattern=r"^o[0-9]+$", description="稳定大纲 ID，如 o1、o2")
    title: str
    goal: str = ""
    key_points: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    suggested_examples: list[str] = Field(default_factory=list)
    suggested_visuals: list[str] = Field(default_factory=list)
    must_not_miss: bool = True


class AgentAssignment(BaseModel):
    """Planning 为每个 Worker Agent 生成的精确指派合约。"""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(description="Agent 标识，如 content, quiz, ppt")
    assigned_outline_ids: list[str] = Field(description="该 Agent 必须覆盖的大纲 ID 列表")
    focus_instruction: str = Field(default="", description="聚焦指令：该 Agent 应重点做什么")
    style_constraint: str = Field(default="", description="风格约束：如 '案例驱动，先直觉后形式化'")
    boundary_notes: list[str] = Field(default_factory=list, max_length=6, description="该 Agent 的边界提醒")
    key_points_emphasis: list[str] = Field(default_factory=list, max_length=8, description="该 Agent 应强调的知识点")
    avoid_overlap_with: list[str] = Field(default_factory=list, description="应避免内容重复的 Agent ID 列表")


class TeachingPlan(BaseModel):
    """PlanningAgent 的唯一输出：教学策略、大纲和 Agent 指派。

    topic/learning_goal 由前端上传，不再由 LLM 重复生成。
    """

    model_config = ConfigDict(extra="ignore")

    teaching_strategy: str = ""
    outline: list[TeachingOutlineItem] = Field(default_factory=list)
    agent_assignments: list[AgentAssignment] = Field(default_factory=list)


class ReusableAssets(BaseModel):
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    visual_ideas: list[str] = Field(default_factory=list)
    practice_refs: list[str] = Field(default_factory=list)
    code_refs: list[str] = Field(default_factory=list)


class DownstreamContext(BaseModel):
    """基础 agent 给 PPT/Video 的短交接摘要。"""
    model_config = ConfigDict(extra="forbid")

    source_agent: str
    title: str = ""
    one_sentence_summary: str = Field(default="", max_length=180)
    covered_outline_ids: list[str] = Field(default_factory=list)
    reusable_assets: ReusableAssets = Field(default_factory=ReusableAssets)
