"""教学计划模型 — PlanningAgent 的输出结构。

TeachingPlan 是单一输出类型，只负责：
- 规定教学策略
- 规定全局教学大纲（outline）
- 为每个选中的 Agent 生成指派（agent_assignments）

学习画像、用户输入、Agent 配置等由代码层直接传递给子 Agent，不经过 LLM。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeachingPlan(BaseModel):
    """PlanningAgent 的唯一输出：教学策略、大纲和 Agent 指派。"""

    model_config = ConfigDict(extra="ignore")

    teaching_strategy: str = ""
    outline: list[dict] = Field(
        default_factory=list,
        description="教学大纲，每项含 id/title/key_points/must_not_miss",
    )
    agent_assignments: list[dict] = Field(
        default_factory=list,
        description="Agent 指派，每项含 agent_id/assigned_outline_ids/focus_instruction",
    )

    @model_validator(mode="after")
    def validate_plan_contract(self) -> "TeachingPlan":
        # 校验 outline 项
        outline_ids: list[str] = []
        for item in self.outline:
            oid = item.get("id", "")
            if oid in outline_ids:
                raise ValueError(f"TeachingPlan outline IDs must be unique, duplicate: {oid}")
            outline_ids.append(oid)

        if not self.agent_assignments:
            return self

        # 校验 agent_assignments
        assignment_agent_ids: list[str] = []
        for assignment in self.agent_assignments:
            aid = assignment.get("agent_id", "")
            if aid in assignment_agent_ids:
                raise ValueError(f"TeachingPlan agent assignments must be unique, duplicate: {aid}")
            assignment_agent_ids.append(aid)

            assigned_ids = assignment.get("assigned_outline_ids", [])
            if len(assigned_ids) != len(set(assigned_ids)):
                raise ValueError(f"TeachingPlan assignment contains duplicate outline IDs: {aid}")
            unknown_ids = set(assigned_ids) - set(outline_ids)
            if unknown_ids:
                raise ValueError(
                    f"TeachingPlan assignment references unknown outline IDs: "
                    f"agent={aid!r} ids={sorted(unknown_ids)}"
                )

        # 所有 must_not_miss 的大纲项必须被覆盖
        must_not_miss_ids = {
            item["id"] for item in self.outline if item.get("must_not_miss")
        }
        covered_ids: set[str] = set()
        for assignment in self.agent_assignments:
            covered_ids.update(assignment.get("assigned_outline_ids", []))
        missing = must_not_miss_ids - covered_ids
        if missing:
            raise ValueError(f"TeachingPlan leaves required outline IDs unassigned: {sorted(missing)}")

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
