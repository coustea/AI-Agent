"""
虚拟人请求数据模型。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# 虚拟人生成请求数据模型
class AvatarGenerateRequest(BaseModel):
    """虚拟人生成请求模型。"""

    description: str = Field(..., min_length=1, max_length=1000, description="头像描述")
    style: str | None = Field(default=None, description="风格: cartoon / realistic / anime")
    session_id: str | None = Field(default=None, description="关联会话 ID")
