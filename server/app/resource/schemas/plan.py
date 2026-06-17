"""Teaching blueprint and planning models — PlanningAgent output."""

from __future__ import annotations

from typing import Any, Literal

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


class TeachingPlan(BaseModel):
    """PlanningAgent 的唯一输出：总体方向、概要、大纲和边界。"""

    topic: str
    learning_goal: str = ""
    audience: str = ""
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    teaching_strategy: str = ""
    summary: str = ""
    outline: list[TeachingOutlineItem] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)


class ReusableAssets(BaseModel):
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    visual_ideas: list[str] = Field(default_factory=list)
    practice_refs: list[str] = Field(default_factory=list)
    code_refs: list[str] = Field(default_factory=list)


class DownstreamMaterial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outline_id: str = ""
    type: Literal["explanation", "structure", "practice", "code", "reading", "example", "visual"] = "explanation"
    summary: str = Field(default="", max_length=500)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    evidence_excerpt: str = Field(default="", max_length=180)
    priority: int = Field(default=3, ge=1, le=5)


class DownstreamContext(BaseModel):
    """基础 agent 给 PPT/Video/Review 的短交接摘要。"""
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["resource_handoff/v1"] = "resource_handoff/v1"
    source_agent: str
    title: str = ""
    one_sentence_summary: str = Field(default="", max_length=180)
    covered_outline_ids: list[str] = Field(default_factory=list)
    materials: list[DownstreamMaterial] = Field(default_factory=list, max_length=8)
    reusable_assets: ReusableAssets = Field(default_factory=ReusableAssets)
    cautions: list[str] = Field(default_factory=list, max_length=6)
