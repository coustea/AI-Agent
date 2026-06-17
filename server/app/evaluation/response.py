"""评估响应模式定义。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LearningEventItem(BaseModel):
    """学习事件响应项。"""

    id: int
    event_type: str
    resource_id: int | None = None
    resource_item_id: int | None = None
    path_id: int | None = None
    path_node_id: int | None = None
    node_id: str | None = None
    course: str | None = None
    topic: str | None = None
    score: float | None = None
    feedback: str | None = None
    created_at: datetime


class EvaluationMetric(BaseModel):
    """评估指标项。"""

    label: str
    value: str
    trend: str = "stable"


class EvaluationSummaryResponse(BaseModel):
    """评估摘要响应。"""

    event_count: int
    average_score: float | None = None
    completed_resources: int = 0
    viewed_resources: int = 0
    active_minutes: int = 0
    weak_topics: list[str] = Field(default_factory=list)
    preferred_resources: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    recent_events: list[LearningEventItem] = Field(default_factory=list)


class DailyTimeEntry(BaseModel):
    """每日学习时长记录。"""

    date: str
    seconds: int = Field(default=0, ge=0)


class HourlyDistributionEntry(BaseModel):
    """每小时学习时长分布。"""

    hour: int = Field(ge=0, le=23)
    seconds: int = Field(default=0, ge=0)


class LearningTimeStatsResponse(BaseModel):
    """学习时长统计响应 — 从 LearningSession 表聚合。"""


    today_seconds: int = Field(default=0, ge=0)
    week_seconds: int = Field(default=0, ge=0)
    month_seconds: int = Field(default=0, ge=0)
    total_seconds: int = Field(default=0, ge=0)
    streak_days: int = Field(default=0, ge=0)
    daily_breakdown: list[DailyTimeEntry] = Field(default_factory=list)
    hourly_distribution: list[HourlyDistributionEntry] = Field(default_factory=list)
    context_breakdown: dict[str, int] = Field(default_factory=dict)
