from datetime import datetime
import uuid

from sqlalchemy import Text, Column
from sqlmodel import SQLModel, Field


class ChatSession(SQLModel, table=True):
    """会话表：管理多会话隔离"""
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)  # UUID 形式的会话 ID
    user_id: int = Field(index=True)   # 所属用户
    module: str = Field(index=True)    # 所属模块 (如 "mentor", "profile_builder")
    title: str = Field(default="新对话", max_length=100) # 会话标题（可以用 LLM 根据第一句话自动生成）
    is_archived: bool = Field(default=False) # 是否已归档/删除

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    # 自上次长期记忆提取后的累计 token（近似值）
    memory_token_count: int = Field(default=0)
    # 自上次画像更新后的累计 token（近似值）
    profile_token_count: int = Field(default=0)




class ChatMessage(SQLModel, table=True):
    """短期记忆表：存储用户的原始聊天记录，达到阈值后总结为长期记忆并清理"""
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    user_id: int = Field(index=True)  # 关联用户 ID
    session_id: str = Field(index=True)  # 对话会话 ID，强关联到 ChatSession.id
    module: str = Field(default="profile_builder", index=True)  # 所属模块：profile_builder / tutor / ...
    role: str  # 消息角色：user / assistant / tool
    content: str = Field(sa_column=Column(Text))  # 消息内容
    attachments: str | None = Field(default=None, sa_column=Column(Text))  # JSON: [{"url": "/uploads/1/abc.pdf", "type": "document", "name": "report.pdf"}]
    tool_calls: str | None = Field(default=None, sa_column=Column(Text))  # JSON: 记录该消息触发的工具调用链
    resource_cards: str | None = Field(default=None, sa_column=Column(Text))  # JSON: 面向前端展示的资源卡片
    # 格式: [{"tool": "read_uploaded_file", "args": {"file_url": "/uploads/1/a.pdf"}, "result": "文件内容...", "status": "success"}]
    created_at: datetime = Field(default_factory=datetime.now, index=True)  # 创建时间
