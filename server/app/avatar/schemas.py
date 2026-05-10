# -*- coding: utf-8 -*-
"""AvatarAgent schemas — 请求/响应数据模型"""

from pydantic import BaseModel


class StopRequest(BaseModel):
    """Stop request body (reserved). user_id comes from JWT."""


class SwitchSessionRequest(BaseModel):
    """Switch session request."""

    session_id: str
