"""会话 API Schema。

模块职责：
- 定义会话相关的请求/响应模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """会话响应。"""
    id: str
    user_id: int
    module: str
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, session: Any) -> "SessionResponse":
        return cls(
            id=session.id,
            user_id=session.user_id,
            module=session.module,
            title=session.title,
            is_archived=session.is_archived,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
