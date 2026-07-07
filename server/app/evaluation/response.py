"""评估响应模式定义。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LearningEventItem(BaseModel):
    """学习事件响应项 — 仅返回前端展示所需字段。"""

    id: int
    module: str
    entity_id: str | None = None
    event_type: str
    score: float | None = None
    course: str | None = None
    topic: str | None = None
    event_metadata: dict = Field(default_factory=dict)
    created_at: datetime


class EvaluationSummaryResponse(BaseModel):
    event_count: int
    average_score: float | None = None
    completed_resources: int = 0
    viewed_resources: int = 0
    weak_topics: list[str] = Field(default_factory=list)
    preferred_resources: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    recent_events: list[LearningEventItem] = Field(default_factory=list)


class DailyTimeEntry(BaseModel):
    date: str
    seconds: int = Field(default=0, ge=0)


class LearningTimeStatsResponse(BaseModel):
    today_seconds: int = Field(default=0, ge=0)
    total_seconds: int = Field(default=0, ge=0)
    streak_days: int = Field(default=0, ge=0)
    daily_breakdown: list[DailyTimeEntry] = Field(default_factory=list)
    context_breakdown: dict[str, int] = Field(default_factory=dict)
