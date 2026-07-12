# 认证模块请求模型：定义注册、登录、更新用户信息等接口的请求体 Schema（基于 Pydantic 校验）
"""认证模块请求数据模型。

定义注册、登录、更新用户信息等接口的请求体 Schema。
使用 Pydantic BaseModel 进行数据验证和序列化。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# 用户注册请求体模型
class UserRegister(BaseModel):
    """用户注册请求体。"""
    # 用户名：2-50 个字符
    username: str = Field(min_length=2, max_length=50)
    # 密码：5-100 个字符
    password: str = Field(min_length=5, max_length=100)
    # 邮箱：可选
    email: str | None = None


# 用户登录请求体模型
class UserLogin(BaseModel):
    """用户登录请求体。"""
    # 用户名
    username: str
    # 密码
    password: str


# 用户信息更新请求体模型（PATCH 语义，字段可选）
class UserUpdate(BaseModel):
    """更新用户信息请求体。

    所有字段均为可选，只更新提交的字段（PATCH 语义）。
    """
    # 新用户名（可选）
    username: str | None = None
    # 新邮箱（可选）
    email: str | None = None
    # 头像 URL（可选）
    avatar: str | None = None
    # 是否首次登录标记（可选，用于控制 onboarding 弹窗）
    is_first_login: bool | None = None

    # ── 基础信息（原 profile base_info，onboarding 填写）──
    school: str | None = None
    school_level: str | None = None
    major: str | None = None
    grade: str | None = None
    daily_study_time: str | None = None
    global_learning_goal: str | None = None
    programming_languages: list[str] | None = None
    courses: list[str] | None = None
