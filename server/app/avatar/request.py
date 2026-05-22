"""Avatar request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AvatarGenerateRequest(BaseModel):
    """Avatar generation request."""

    description: str = Field(..., min_length=1, max_length=1000, description="头像描述")
    style: str | None = Field(default=None, description="风格: cartoon / realistic / anime")
    session_id: str | None = Field(default=None, description="关联会话 ID")
