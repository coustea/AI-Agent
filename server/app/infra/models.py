"""
统一 SQLModel 表定义。

合并自 models/ 目录下所有模型文件：
  user.py, auth.py, chat.py, memory.py, profile.py, resource.py
"""

import uuid
from datetime import datetime

from sqlalchemy import Text, Column
from sqlmodel import SQLModel, Field


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    """用户基础信息表"""
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, index=True, unique=True)
    password: str = Field(max_length=255, exclude=True)
    email: str | None = Field(default=None, max_length=100)
    avatar: str | None = Field(default=None, max_length=500)
    major: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    school: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class ActiveToken(SQLModel, table=True):
    """活跃 Token 白名单表"""
    __tablename__ = "active_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatSession(SQLModel, table=True):
    """会话表：管理多会话隔离"""
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(index=True)
    title: str = Field(default="新对话", max_length=100)
    is_archived: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    memory_token_count: int = Field(default=0)
    profile_token_count: int = Field(default=0)


class ChatMessage(SQLModel, table=True):
    """短期记忆表：存储用户的原始聊天记录"""
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    module: str = Field(default="profile_builder", index=True)
    role: str
    content: str = Field(sa_column=Column(Text))
    attachments: str | None = Field(default=None, sa_column=Column(Text))
    tool_calls: str | None = Field(default=None, sa_column=Column(Text))
    resource_cards: str | None = Field(default=None, sa_column=Column(Text))
    message_type: str | None = Field(default=None, index=True)
    tool_name: str | None = Field(default=None, index=True)
    tool_call_id: str | None = Field(default=None, index=True)
    tool_args: str | None = Field(default=None, sa_column=Column(Text))
    tool_result: str | None = Field(default=None, sa_column=Column(Text))
    status: str | None = Field(default=None, index=True)
    sequence_no: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class UserMemory(SQLModel, table=True):
    """统一长期记忆表"""
    __tablename__ = "user_memory"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(default="", index=True)
    content: str = Field(sa_column=Column(Text))
    memory_type: str = Field(index=True)
    dimension: str | None = None
    importance: float = Field(default=0.5)
    source: str = Field(default="conversation", index=True)
    source_message_count: int = Field(default=0)
    expires_at: datetime | None = Field(default=None)
    evidence_count: int = Field(default=1)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    attachments: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class UserProfile(SQLModel, table=True):
    """用户画像表：存储用户当前的学习画像状态"""
    __tablename__ = "user_profiles"

    user_id: int = Field(primary_key=True)

    knowledge_level: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_level_score: int | None = Field(default=None)
    learning_goal: str | None = Field(default=None, sa_column=Column(Text))
    learning_goal_score: int | None = Field(default=None)
    learning_history: str | None = Field(default=None, sa_column=Column(Text))
    learning_history_score: int | None = Field(default=None)
    cognitive_style: str | None = Field(default=None, sa_column=Column(Text))
    cognitive_style_score: int | None = Field(default=None)
    error_pattern: str | None = Field(default=None, sa_column=Column(Text))
    error_pattern_score: int | None = Field(default=None)
    learning_pace: str | None = Field(default=None, sa_column=Column(Text))
    learning_pace_score: int | None = Field(default=None)
    interest_preference: str | None = Field(default=None, sa_column=Column(Text))
    interest_preference_score: int | None = Field(default=None)
    cognitive_level: str | None = Field(default=None, sa_column=Column(Text))
    cognitive_level_score: int | None = Field(default=None)

    profile_summary: str | None = Field(default=None, sa_column=Column(Text))

    updated_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)


class UserProfileHistory(SQLModel, table=True):
    """用户画像历史表：记录每次画像变更的快照"""
    __tablename__ = "user_profile_history"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    version: int = Field(index=True)

    knowledge_level: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_level_score: int | None = Field(default=None)
    learning_goal: str | None = Field(default=None, sa_column=Column(Text))
    learning_goal_score: int | None = Field(default=None)
    learning_history: str | None = Field(default=None, sa_column=Column(Text))
    learning_history_score: int | None = Field(default=None)
    cognitive_style: str | None = Field(default=None, sa_column=Column(Text))
    cognitive_style_score: int | None = Field(default=None)
    error_pattern: str | None = Field(default=None, sa_column=Column(Text))
    error_pattern_score: int | None = Field(default=None)
    learning_pace: str | None = Field(default=None, sa_column=Column(Text))
    learning_pace_score: int | None = Field(default=None)
    interest_preference: str | None = Field(default=None, sa_column=Column(Text))
    interest_preference_score: int | None = Field(default=None)
    cognitive_level: str | None = Field(default=None, sa_column=Column(Text))
    cognitive_level_score: int | None = Field(default=None)

    profile_summary: str | None = Field(default=None, sa_column=Column(Text))

    change_reason: str | None = Field(default=None, sa_column=Column(Text))
    source_memory_ids: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------

class GeneratedResource(SQLModel, table=True):
    """生成资源记录表"""
    __tablename__ = "generated_resources"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    course: str = Field(max_length=200)
    gap: str = Field(sa_column=Column(Text))
    need: str = Field(default="review", max_length=50)
    extra: str | None = Field(default=None, sa_column=Column(Text))

    mindmap_result: str | None = Field(default=None, sa_column=Column(Text))
    content_result: str | None = Field(default=None, sa_column=Column(Text))
    code_result: str | None = Field(default=None, sa_column=Column(Text))
    quiz_result: str | None = Field(default=None, sa_column=Column(Text))
    reading_result: str | None = Field(default=None, sa_column=Column(Text))
    ppt_result: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Model registration (for init_db)
# ---------------------------------------------------------------------------

REGISTERED_MODELS = (
    ActiveToken,
    ChatSession,
    ChatMessage,
    UserMemory,
    UserProfile,
    UserProfileHistory,
    GeneratedResource,
    User,
)


def import_all_models() -> tuple[type, ...]:
    """Return the registered model classes and ensure imports stay explicit."""
    return REGISTERED_MODELS
