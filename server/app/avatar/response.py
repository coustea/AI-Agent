"""Avatar response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AvatarBridgeResponse(BaseModel):
    """Avatar bridge generation response."""

    avatar_url: str | None = Field(default=None, description="生成的头像 URL")
    status: str = Field(default="pending", description="生成状态: pending / completed / failed")
    error: str | None = Field(default=None, description="错误信息")
