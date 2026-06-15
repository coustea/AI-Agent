"""认证模块响应数据模型。

定义用户信息的响应格式，用于序列化返回给前端。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserRead(BaseModel):
    """用户信息响应体。

    用于返回给前端的用户数据，排除了密码等敏感字段。
    """
    # 用户 ID
    id: int
    # 用户名
    username: str
    # 邮箱（可选）
    email: str | None = None
    # 头像 URL（可选）
    avatar: str | None = None
    # 账号创建时间
    created_at: datetime | None = None
    # 是否首次登录（False=未完成 onboarding，True=已完成）
    is_first_login: bool = False

    # 允许从 ORM 对象（如 SQLModel 实例）直接创建
    model_config = {"from_attributes": True}
