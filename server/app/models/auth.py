from datetime import datetime

from sqlmodel import SQLModel, Field


class ActiveToken(SQLModel, table=True):
    """活跃 Token 白名单表：存储当前有效的 JWT，支持主动吊销（登出）"""
    __tablename__ = "active_tokens"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    user_id: int = Field(index=True)  # 关联用户 ID
    token: str = Field(unique=True, index=True)  # JWT 字符串
    expires_at: datetime  # Token 过期时间
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间
