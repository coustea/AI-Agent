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


class ChatMessage(SQLModel, table=True):
    """短期记忆表：存储用户的原始聊天记录，达到阈值后总结为长期记忆并清理"""
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    user_id: int = Field(index=True)  # 关联用户 ID
    session_id: str = Field(default="", index=True)  # 对话会话 ID
    module: str = Field(default="profile_builder", index=True)  # 所属模块：profile_builder / tutor / ...
    role: str  # 消息角色：user / assistant / system
    content: str  # 消息内容
    created_at: datetime = Field(default_factory=datetime.now, index=True)  # 创建时间


class UserMemory(SQLModel, table=True):
    """长期记忆表：存储 LLM 对短期聊天记录的总结，供画像构建和智能辅导共用"""
    __tablename__ = "user_memory"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    user_id: int = Field(index=True)  # 关联用户 ID
    session_id: str = Field(default="", index=True)  # 本次总结对应的会话 ID
    content: str  # 长期记忆内容（LLM 总结）
    memory_type: str  # 记忆类型：knowledge / error / behavior / interest / question / answer
    dimension: str | None = None  # 对应的画像维度（辅导模块可为 None）
    importance: float = Field(default=0.5)  # 重要性评分，0~1
    source: str = Field(default="conversation", index=True)  # 来源模块：conversation=画像构建, tutor_chat=辅导对话, tutor_material=辅导生成资源
    source_message_count: int = Field(default=0)  # 本次总结覆盖的短期消息条数
    attachments: str | None = None  # JSON 数组，关联资源 [{"type":"docx","url":"...","title":"..."}]
    created_at: datetime = Field(default_factory=datetime.now)  # 创建时间