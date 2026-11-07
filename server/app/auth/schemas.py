"""认证模块数据模型（请求与响应 Schema）。"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """用户注册请求体。"""

    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=5, max_length=100)
    email: str | None = None


class UserLogin(BaseModel):
    """用户登录请求体。"""

    username: str
    password: str


class UserUpdate(BaseModel):
    """更新用户信息请求体（PATCH 语义，字段可选）。"""

    username: str | None = None
    email: str | None = None
    avatar: str | None = None
    onboarding_completed: bool | None = None

    # 基础信息（原 profile base_info，onboarding 填写）
    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    programming_languages: list[str] | None = None
    courses: list[str] | None = None


class UserRead(BaseModel):
    """用户信息响应体（排除密码等敏感字段）。"""

    id: int
    username: str
    email: str | None = None
    avatar: str | None = None
    onboarding_completed: bool = False

    # 基础信息
    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    programming_languages: list[str] | None = None
    courses: list[str] | None = None

    created_at: datetime | None = None

    model_config = {"from_attributes": True}


__all__ = ["UserRegister", "UserLogin", "UserUpdate", "UserRead"]
