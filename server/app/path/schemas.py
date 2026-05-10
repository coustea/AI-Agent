"""Path planning schemas.

定义学习路径规划相关的数据模型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


NodeStatus = Literal["success", "processing", "wait"]
StageStatus = Literal["success", "processing", "wait"]


class PathNode(BaseModel):
    id: str
    title: str
    status: NodeStatus = "wait"
    progress: int = Field(default=0, ge=0, le=100)
    priority: int = Field(default=50, ge=0, le=100)
    desc: str | None = None


class PathStage(BaseModel):
    id: str
    title: str
    status: StageStatus = "wait"
    progress: int = Field(default=0, ge=0, le=100)
    nodes: list[PathNode] = Field(default_factory=list)


class PathProgress(BaseModel):
    overall: int = Field(default=0, ge=0, le=100)
    current_stage_id: str | None = None
    confidence: int = Field(default=60, ge=0, le=100)
    eta_days: int = Field(default=14, ge=1)


class Adjustment(BaseModel):
    at: datetime
    reason: str
    impacted_nodes: list[str] = Field(default_factory=list)


class PathPlan(BaseModel):
    version: int = 1
    generated_at: datetime
    knowledge_level: str | None = None
    learning_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)
    stages: list[PathStage] = Field(default_factory=list)
    progress: PathProgress
    adjustments: list[Adjustment] = Field(default_factory=list)


class PathSummary(BaseModel):
    overall_progress: int = Field(default=0, ge=0, le=100)
    current_stage: str | None = None
    knowledge_level: str | None = None
    eta_days: int = Field(default=14, ge=1)
    confidence: int = Field(default=60, ge=0, le=100)


class PathInsight(BaseModel):
    adjustment_reason: str
    next_action: str


class PathPlanMeta(BaseModel):
    generated_at: datetime
    data_sources: list[str] = Field(default_factory=list)
    resource_id: int | None = None
    plan_version: int = 1


class PathPlanData(BaseModel):
    summary: PathSummary
    stages: list[PathStage]
    insights: PathInsight
    meta: PathPlanMeta


class PathRebuildRequest(BaseModel):
    resource_id: int | None = Field(default=None, ge=1)


class PathFeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=1000)
    weak_points: list[str] = Field(default_factory=list)
    resource_id: int | None = Field(default=None, ge=1)
