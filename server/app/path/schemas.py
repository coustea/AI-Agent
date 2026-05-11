"""Path planning schemas.

定义学习路径规划相关的数据模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


NodeStatus = Literal["success", "processing", "wait"]
StageStatus = Literal["success", "processing", "wait"]


class PathNode(BaseModel):
    """学习路径节点。"""
    id: str
    title: str
    status: NodeStatus = "wait"
    progress: int = Field(default=0, ge=0, le=100)
    priority: int = Field(default=50, ge=0, le=100)
    desc: str | None = None
    recommendation_reason: str | None = None
    resource_id: int | None = None
    resource_item_id: int | None = None
    resource_type: str | None = None
    resource_title: str | None = None
    resource_summary: str | None = None
    resource_format: str | None = None
    resource_status: Literal["available", "missing", "pending", "failed"] | None = None


class PathStage(BaseModel):
    """学习路径阶段。"""
    id: str
    title: str
    status: StageStatus = "wait"
    progress: int = Field(default=0, ge=0, le=100)
    nodes: list[PathNode] = Field(default_factory=list)


class PathProgress(BaseModel):
    """学习路径进度。"""
    overall: int = Field(default=0, ge=0, le=100)
    current_stage_id: str | None = None
    current_node_id: str | None = None
    confidence: int = Field(default=60, ge=0, le=100)
    eta_days: int = Field(default=14, ge=1)


class Adjustment(BaseModel):
    """路径调整记录。"""
    at: datetime
    reason: str
    impacted_nodes: list[str] = Field(default_factory=list)


class PathPlan(BaseModel):
    """学习路径计划。"""
    version: int = 1
    generated_at: datetime
    knowledge_level: str | None = None
    learning_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)
    stages: list[PathStage] = Field(default_factory=list)
    progress: PathProgress
    adjustments: list[Adjustment] = Field(default_factory=list)
    profile_dimensions: dict[str, Any] | None = None


class PathSummary(BaseModel):
    """路径摘要。"""
    overall_progress: int = Field(default=0, ge=0, le=100)
    current_stage: str | None = None
    current_node: str | None = None
    knowledge_level: str | None = None
    eta_days: int = Field(default=14, ge=1)
    confidence: int = Field(default=60, ge=0, le=100)


class PathInsight(BaseModel):
    """路径洞察。"""
    adjustment_reason: str
    next_action: str
    recommended_nodes: list[dict[str, Any]] = Field(default_factory=list)


class PathPlanMeta(BaseModel):
    """路径元数据。"""
    generated_at: datetime
    data_sources: list[str] = Field(default_factory=list)
    resource_id: int | None = None
    plan_version: int = 1
    profile_version: int | None = None


class PathPlanData(BaseModel):
    """路径计划响应数据。"""
    summary: PathSummary
    stages: list[PathStage]
    insights: PathInsight
    meta: PathPlanMeta


class PathRebuildRequest(BaseModel):
    """路径重建请求。"""
    resource_id: int | None = Field(default=None, ge=1)
    force_refresh_profile: bool = Field(default=False)


class PathFeedbackRequest(BaseModel):
    """路径反馈请求。"""
    feedback: str = Field(..., min_length=1, max_length=1000)
    weak_points: list[str] = Field(default_factory=list)
    resource_id: int | None = Field(default=None, ge=1)


class NodeRecommendation(BaseModel):
    """节点推荐。"""
    node_id: str
    title: str
    priority: int = Field(ge=0, le=100)
    stage_id: str
    reason: str
    estimated_duration_minutes: int | None = None


class PathRecommendationResponse(BaseModel):
    """路径推荐响应。"""
    recommendations: list[NodeRecommendation]
    total_candidates: int
    profile_based: bool
