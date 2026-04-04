from datetime import datetime
from sqlmodel import SQLModel, Field


class UserProfile(SQLModel, table=True):
    """用户画像表：存储用户当前的学习画像状态（与用户一对一）"""
    __tablename__ = "user_profiles"

    user_id: int = Field(primary_key=True)  # 关联用户 ID，同时作为主键

    # ===== 画像维度 =====
    knowledge_level: str | None = None  # 知识水平
    learning_goal: str | None = None  # 学习目标
    learning_history: str | None = None  # 学习历史
    cognitive_style: str | None = None  # 认知风格
    error_pattern: str | None = None  # 错误模式
    learning_pace: str | None = None  # 学习节奏
    interest_preference: str | None = None  # 兴趣偏好
    cognitive_level: str | None = None  # 认知水平

    profile_summary: str | None = None  # 画像总结

    updated_at: datetime = Field(default_factory=datetime.now)  # 更新时间
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间


class UserProfileHistory(SQLModel, table=True):
    """用户画像历史表：记录每次画像变更的快照，用于追溯变化过程"""
    __tablename__ = "user_profile_history"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    user_id: int = Field(index=True)  # 关联用户 ID
    version: int = Field(index=True)  # 版本号，每次画像更新 +1

    # ===== 画像维度快照 =====
    knowledge_level: str | None = None  # 知识水平
    learning_goal: str | None = None  # 学习目标
    learning_history: str | None = None  # 学习历史
    cognitive_style: str | None = None  # 认知风格
    error_pattern: str | None = None  # 错误模式
    learning_pace: str | None = None  # 学习节奏
    interest_preference: str | None = None  # 兴趣偏好
    cognitive_level: str | None = None  # 认知水平

    profile_summary: str | None = None  # 画像总结

    change_reason: str | None = None  # 变更原因，如"根据最近10条对话更新"
    source_memory_ids: str | None = None  # 关联的记忆 ID 列表（JSON 数组）

    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间