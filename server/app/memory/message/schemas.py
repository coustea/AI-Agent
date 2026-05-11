"""消息 API Schema。

模块职责：
- 定义消息相关的请求/响应模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """消息响应。"""
    id: int
    role: str
    content: str
    attachments: dict | None
    tool_calls: list | None
    diagram: dict | None
    created_at: datetime

    @classmethod
    def from_model(cls, message: Any) -> "MessageResponse":
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            attachments=message.attachments,
            tool_calls=message.tool_calls,
            diagram=message.diagram,
            created_at=message.created_at,
        )
