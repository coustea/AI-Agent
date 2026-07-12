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
