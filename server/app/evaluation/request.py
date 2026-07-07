"""学习事件请求模式定义。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


LearningEventType = Literal[
    "chat_dialogue",
    "resource_generated", "resource_viewed", "resource_completed", "resource_feedback",
    "path_node_started", "path_node_completed", "path_quiz_answered", "path_feedback",
    "quiz_submitted",
    "visualizer_run",
]


class LearningEventCreate(BaseModel):
    """学习事件创建请求 — unified 结构（module + entity_id + metadata）。"""

    module: str = Field(description="模块: chat / resource / path / quiz / visualizer")
    entity_id: str | None = Field(default=None, max_length=255, description="模块内实体 ID")
    event_type: str = Field(description="事件子类型")
    score: float | None = Field(default=None, ge=0, le=100)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    event_metadata: dict[str, Any] = Field(default_factory=dict)


class LearningSessionCreate(BaseModel):
    """学习会话上报请求 — 前端离开学习页面时一次性发送。"""

    source_page: str
    started_at: str
    ended_at: str
    duration_seconds: int = Field(ge=1, le=86400)
    module: str | None = Field(default=None, max_length=50)
    entity_id: str | None = Field(default=None, max_length=255)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    event_metadata: dict[str, Any] = Field(default_factory=dict)
