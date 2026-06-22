"""教学计划模型 — PlanningAgent 的输出结构。

TeachingPlan 是单一输出类型，只负责：
- 规定教学策略
- 规定全局教学大纲（outline）
- 为每个选中的 Agent 生成指派（agent_assignments）

学习画像、用户输入、Agent 配置等由代码层直接传递给子 Agent，不经过 LLM。
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeachingOutlineItem(BaseModel):
    """PlanningAgent 生成的全局教学大纲项，不绑定具体 agent。"""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default="", pattern=r"^o[0-9]*$", description="稳定大纲 ID，如 o1、o2")
    title: str = ""
    goal: str = ""
    key_points: list[str] = Field(default_factory=list, max_length=5)
    common_misconceptions: list[str] = Field(default_factory=list)
    suggested_examples: list[str] = Field(default_factory=list)
    suggested_visuals: list[str] = Field(default_factory=list)
    must_not_miss: bool = True

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)


class AgentAssignment(BaseModel):
    """Planning 为每个 Worker Agent 生成的精确指派合约。"""

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(min_length=1, description="Agent 标识，如 content, quiz")
    assigned_outline_ids: list[str] = Field(min_length=1, description="该 Agent 必须覆盖的大纲 ID 列表")
    focus_instruction: str = Field(min_length=1, description="聚焦指令：该 Agent 应重点做什么")
    style_constraint: str = Field(min_length=1, description="风格约束：如 '案例驱动，先直觉后形式化'")
    boundary_notes: list[str] = Field(default_factory=list, max_length=6, description="该 Agent 的边界提醒")
    key_points_emphasis: list[str] = Field(default_factory=list, max_length=8, description="该 Agent 应强调的知识点")
    avoid_overlap_with: list[str] = Field(default_factory=list, description="应避免内容重复的 Agent ID 列表")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)


class TeachingPlan(BaseModel):
    """PlanningAgent 的唯一输出：教学策略、大纲和 Agent 指派。

    topic/learning_goal 由前端上传，不再由 LLM 重复生成。
    """

    model_config = ConfigDict(extra="ignore")

    teaching_strategy: str = ""
    outline: list[TeachingOutlineItem] = Field(default_factory=list, max_length=8)
    agent_assignments: list[AgentAssignment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan_contract(self) -> "TeachingPlan":
        outline_ids = [item.id for item in self.outline]
        if len(outline_ids) != len(set(outline_ids)):
            raise ValueError("TeachingPlan outline IDs must be unique")

        if not self.agent_assignments:
            return self

        assignment_agent_ids = [assignment.agent_id for assignment in self.agent_assignments]
        if len(assignment_agent_ids) != len(set(assignment_agent_ids)):
            raise ValueError("TeachingPlan agent assignments must be unique")

        allowed_outline_ids = set(outline_ids)
        covered_outline_ids: set[str] = set()
        for assignment in self.agent_assignments:
            assigned_ids = assignment.assigned_outline_ids
            if len(assigned_ids) != len(set(assigned_ids)):
                raise ValueError(f"TeachingPlan assignment contains duplicate outline IDs: {assignment.agent_id}")
            unknown_ids = set(assigned_ids) - allowed_outline_ids
            if unknown_ids:
                raise ValueError(
                    f"TeachingPlan assignment references unknown outline IDs: "
                    f"agent={assignment.agent_id!r} ids={sorted(unknown_ids)}"
                )
            covered_outline_ids.update(assigned_ids)

        required_outline_ids = {item.id for item in self.outline if item.must_not_miss}
        missing_required_ids = required_outline_ids - covered_outline_ids
        if missing_required_ids:
            raise ValueError(f"TeachingPlan leaves required outline IDs unassigned: {sorted(missing_required_ids)}")
        return self


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
