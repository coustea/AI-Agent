from datetime import datetime

from sqlalchemy import Text, Column
from sqlmodel import SQLModel, Field


class UserMemory(SQLModel, table=True):
    """统一长期记忆表：存储 LLM 总结、用户事实偏好等所有长期记忆。

    memory_type 区分类型：
      - summary: 对话批量总结（短期→长期压缩）
      - fact: 用户事实（如"专业是计算机"）
      - preference: 用户偏好（如"不要英文文档"）
      - goal: 用户目标（如"下周考数据结构"）
      - weakness: 用户弱点
      - knowledge / error / behavior / interest / question / answer: 画像相关
    """
    __tablename__ = "user_memory"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(default="", index=True)  # 来源会话 ID
    content: str = Field(sa_column=Column(Text))
    memory_type: str = Field(index=True)  # summary / fact / preference / goal / weakness / ...
    dimension: str | None = None  # 对应的画像维度（辅导模块可为 None）
    importance: float = Field(default=0.5)  # 重要性评分 0~1
    source: str = Field(default="conversation", index=True)  # 来源模块
    source_message_count: int = Field(default=0)  # 本次总结覆盖的短期消息条数
    expires_at: datetime | None = Field(default=None)  # 时效性，过期自动忽略
    attachments: str | None = Field(default=None, sa_column=Column(Text))  # JSON 关联资源
    created_at: datetime = Field(default_factory=datetime.now)
