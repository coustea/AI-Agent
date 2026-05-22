"""Path response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PathNodeStatus:
    SUCCESS = "success"
    PROCESSING = "processing"
    WAIT = "wait"


class PathPlanSummary(BaseModel):
    overall_progress: float = 0.0
    current_stage: str | None = None
    current_node: str | None = None
    knowledge_level: str | None = None
    eta_days: int = 0
    confidence: float = 0.0


class PathRecommendedNode(BaseModel):
    node_id: str
    title: str
    priority: int = 0
    stage_id: str
    reason: str = ""


class PathPlanInsights(BaseModel):
    adjustment_reason: str = ""
    next_action: str = ""
    recommended_nodes: list[PathRecommendedNode] = Field(default_factory=list)


class PathPlanMeta(BaseModel):
    generated_at: str = ""
    data_sources: list[str] = Field(default_factory=list)
    resource_id: int | None = None
    plan_version: int = 1


class PathPlanResponse(BaseModel):
    summary: PathPlanSummary
    stages: list[dict] = Field(default_factory=list)
    insights: PathPlanInsights
    meta: PathPlanMeta
