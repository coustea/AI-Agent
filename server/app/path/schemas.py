"""路径规划模块 Pydantic 模型。

包含请求/响应/内部状态的所有数据结构。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.resource.schemas import AgentConfigs, AgentSelection, OutputOptions


# ======================================================================
# 请求模型
# ======================================================================


class GeneratePathRequest(BaseModel):
    """路径生成请求。"""

    goal: str = Field(description="学习目标")
    topic: str = Field(default="", description="学习主题")
    module: str = Field(default="mentor", description="模块名称")
    current_knowledge: list[str] = Field(default_factory=list, description="当前已掌握的知识点")
    preferences: dict[str, Any] = Field(default_factory=dict, description="学习偏好")


class PathNodeResourceRequest(BaseModel):
    """路径节点资源生成请求 — 不允许前端提交 learning_need、profile、user_id 或 node_id。"""
    model_config = ConfigDict(extra="forbid")

    selected_agents: list[AgentSelection] = Field(default_factory=list)
    agent_configs: AgentConfigs = Field(default_factory=AgentConfigs)
    output_options: OutputOptions = Field(default_factory=OutputOptions)


# ======================================================================
# Agent 结构化输出模型
# ======================================================================


class AgentPathNode(BaseModel):
    """规划 Agent 输出的单个路径节点。"""

    node_id: str = Field(description="节点唯一标识")
    stage_id: str = Field(description="阶段标识")
    title: str = Field(description="节点标题")
    prerequisites: list[str] = Field(default_factory=list, description="前置节点 ID")
    mastery_target: str = Field(default="", description="掌握目标")
    estimated_minutes: int = Field(default=30, description="预估学习时间(分钟)")
    difficulty: str = Field(default="intermediate", description="难度等级")
    recommendation_reason: str = Field(default="", description="推荐理由")
    priority: int = Field(default=0, description="优先级")


class AgentStage(BaseModel):
    """规划 Agent 输出的阶段。"""
    
    stage_id: str = Field(description="阶段标识，如'stage-1'")
    title: str = Field(description="阶段标题")
    description: str = Field(description="阶段描述")


class AgentCoursePathPlan(BaseModel):
    """规划 Agent 的结构化输出。"""

    title: str = Field(description="路径标题")
    eta_days: int = Field(default=14, description="预估学习天数")
    confidence: int = Field(default=60, ge=0, le=100, description="规划置信度百分比")
    adjustment_rationale: list[str] = Field(default_factory=list, description="调整理由列表")
    stages: list[AgentStage] = Field(default_factory=list, description="宏观阶段骨架列表")
    nodes: list[AgentPathNode] = Field(default_factory=list, description="所有阶段的具体学习节点列表")

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> Any:
        if isinstance(value, float) and 0 <= value <= 1:
            return round(value * 100)
        return value

    @field_validator("adjustment_rationale", mode="before")
    @classmethod
    def normalize_adjustment_rationale(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        return value


# ======================================================================
# 响应模型
# ======================================================================


class CoursePathNodeDTO(BaseModel):
    """课程路径节点 DTO。"""

    id: int | None = None
    node_id: str = ""
    stage_id: str = ""
    title: str = ""
    status: str = "pending"
    resource_status: str = "not_started"
    progress: float = 0.0
    priority: int = 0
    prerequisites: list[str] = Field(default_factory=list)
    mastery_target: str | None = None
    estimated_minutes: int | None = None
    difficulty: str | None = None
    recommendation_reason: str | None = None
    resource_id: int | None = None


class CoursePathResponse(BaseModel):
    """课程路径响应。"""

    id: int | None = None
    module: str = ""
    title: str = ""
    goal: str | None = None
    overall_progress: float = 0.0
    current_stage_id: str | None = None
    current_node_id: str | None = None
    eta_days: int = 0
    confidence: int = 0
    status: str = "pending"
    stages: list[dict[str, Any]] = Field(default_factory=list)
    nodes: list[CoursePathNodeDTO] = Field(default_factory=list)
    created_at: str = ""


class PathGenerationTaskResponse(BaseModel):
    """异步路径规划任务状态响应。"""

    task_id: int
    module: str = "mentor"
    goal: str = ""
    status: str = "pending"
    progress: int = 0
    latest_message: str = ""
    error_message: str | None = None
    generated_path_id: int | None = None


# ======================================================================
# Re-exports from request.py / response.py
# ======================================================================

from app.path.request import PathPlanFeedbackRequest  # noqa: E402
from app.path.response import (  # noqa: E402
    PathNodeStatus,
    PathPlanInsights,
    PathPlanMeta,
    PathRecommendedNode,
    PathPlanResponse,
    PathPlanSummary,
)

__all__ = [
    # Request
    "GeneratePathRequest",
    "PathNodeResourceRequest",
    "PathPlanFeedbackRequest",
    # Agent output
    "AgentPathNode",
    "AgentStage",
    "AgentCoursePathPlan",
    # Response
    "CoursePathNodeDTO",
    "CoursePathResponse",
    "PathGenerationTaskResponse",
    "PathNodeStatus",
    "PathPlanSummary",
    "PathRecommendedNode",
    "PathPlanInsights",
    "PathPlanMeta",
    "PathPlanResponse",
]
