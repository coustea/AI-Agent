"""Runtime input/output models for agent execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.resource.schemas.plan import DownstreamContext, TeachingPlan
from app.resource.schemas.request import LearningScenario


class AgentResult(BaseModel):
    """统一 Agent 输出结果，用于 standalone resource 和 path node resource。"""
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    content: str = ""
    file_type: str = "markdown"
    title: str = ""
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_context: DownstreamContext | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ResourceInput(BaseModel):
    """standalone 多智能体资源生成输入。"""
    model_config = ConfigDict(extra="forbid")

    resource_id: int | None = None
    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    teaching_plan: TeachingPlan | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    upstream_handoffs: dict[str, DownstreamContext] = Field(default_factory=dict)


class NodeInput(BaseModel):
    """路径规划当前节点资源生成输入。"""
    model_config = ConfigDict(extra="forbid")

    path_id: int
    node_id: int
    node_key: str
    path_title: str
    path_goal: str
    stage_id: str | None = None
    node_title: str
    difficulty: str | None = None
    mastery_target: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    generation_focus: list[str] = Field(default_factory=list)
    tutorial_title: str
    tutorial_summary: str | None = None
    tutorial_markdown: str
    profile: dict[str, Any] = Field(default_factory=dict)
    existing_resources: dict[str, AgentResult] = Field(default_factory=dict)
    agent_config: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    """Review Agent 的审查结果。"""
    passed: bool = True
    overall_score: int = Field(default=100, ge=0, le=100)
    consistency_score: int = Field(default=100, ge=0, le=100, description="知识一致性评分")
    personalization_score: int = Field(default=100, ge=0, le=100, description="个性化匹配度评分")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
