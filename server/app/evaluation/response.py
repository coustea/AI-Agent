"""评估响应模式定义。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LearningEventItem(BaseModel):
    """学习事件响应项 — 仅返回前端展示所需字段。"""

    id: int
    event_type: str
    course: str | None = None
    topic: str | None = None
    feedback: str | None = None
    score: int | None = None
    path_id: int | None = None
    path_node_id: int | None = None
    node_id: str | None = None
    resource_id: int | None = None
    resource_item_id: int | None = None
    created_at: datetime


class EvaluationSummaryResponse(BaseModel):
    """评估摘要响应 — 仅返回前端展示所需字段。"""

    event_count: int
    average_score: float | None = None
    completed_resources: int = 0
    viewed_resources: int = 0
    weak_topics: list[str] = Field(default_factory=list)
    preferred_resources: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    recent_events: list[LearningEventItem] = Field(default_factory=list)


class DailyTimeEntry(BaseModel):
    """每日学习时长记录。"""

    date: str
    seconds: int = Field(default=0, ge=0)


class LearningTimeStatsResponse(BaseModel):
    """学习时长统计响应 — 仅返回前端展示所需字段。"""

    today_seconds: int = Field(default=0, ge=0)
    total_seconds: int = Field(default=0, ge=0)
    streak_days: int = Field(default=0, ge=0)
    daily_breakdown: list[DailyTimeEntry] = Field(default_factory=list)
    context_breakdown: dict[str, int] = Field(default_factory=dict)
