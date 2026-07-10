"""
虚拟人响应数据模型。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# 虚拟人桥接生成响应数据模型
class AvatarBridgeResponse(BaseModel):
    """虚拟人桥接生成响应模型。"""

    avatar_url: str | None = Field(default=None, description="生成的头像 URL")
    status: str = Field(default="pending", description="生成状态: pending / completed / failed")
    error: str | None = Field(default=None, description="错误信息")
