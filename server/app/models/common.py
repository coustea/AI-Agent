from datetime import datetime

from sqlmodel import SQLModel,Field


class UserMemory(SQLModel, table=True):
    """用户记忆表：记录用户交互中产生的原始事实片段"""
    __tablename__ = "user_memory"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    user_id: int = Field(index=True)  # 关联用户 ID
    content: str  # 记忆内容
    memory_type: str  # 记忆类型：knowledge / error / behavior / interest
    dimension: str | None = None  # 对应的画像维度
    importance: float = Field(default=0.5)  # 重要性评分，0~1
    source: str | None = None  # 来源（如对话、测试、资源学习等）
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间