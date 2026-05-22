"""Chat request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="消息角色: user / assistant / system")
    content: str = Field(..., description="消息文本内容")
