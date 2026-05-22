"""Resource request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResourceGenerateRequest(BaseModel):
    """Resource generation request."""

    topic: str = Field(..., min_length=1, max_length=500, description="生成主题")
    resource_type: str = Field(default="mindmap", description="资源类型: mindmap / quiz / reading / code")
    session_id: str | None = Field(default=None, description="关联会话 ID")
    course: str | None = Field(default=None, max_length=200, description="课程名称")
    difficulty: str | None = Field(default=None, description="难度级别")
    extra_instructions: str | None = Field(default=None, max_length=2000, description="额外指令")
