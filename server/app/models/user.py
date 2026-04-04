from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """用户基础信息表"""
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    username: str = Field(max_length=50, index=True, unique=True)  # 用户名
    password: str = Field(max_length=255, exclude=True)  # 密码（bcrypt 哈希）
    email: str | None = Field(default=None, max_length=100)  # 邮箱
    avatar: str | None = Field(default=None, max_length=500)  # 头像 URL
    major: str | None = Field(default=None, max_length=100)  # 专业
    grade: str | None = Field(default=None, max_length=20)  # 年级
    school: str | None = Field(default=None, max_length=100)  # 学校
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = Field(default_factory=datetime.now)  # 更新时间
