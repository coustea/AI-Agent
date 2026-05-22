"""Path request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PathPlanFeedbackRequest(BaseModel):
    feedback: str = Field(..., description="用户反馈内容")
    weak_points: list[str] | None = Field(default=None, description="薄弱知识点")
    resource_id: int | None = Field(default=None, description="关联资源 ID")
