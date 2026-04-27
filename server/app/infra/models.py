"""
统一 SQLModel 表定义。

所有数据库表集中在此文件中定义，按功能域分组：
  - User       用户基础信息
  - Auth       JWT Token 白名单
  - Chat       会话与消息（短期记忆）
  - Memory     长期记忆
  - Profile    用户画像及历史快照
  - Resource   生成资源记录

新表应添加到 REGISTERED_MODELS 元组中，以便 init_db() 自动创建。
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ARRAY, Integer, Text, Column, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlmodel import SQLModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# User — 用户基础信息
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    """用户基础信息表"""
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    username: str = Field(max_length=50, index=True, unique=True)  # 用户名，唯一索引
    password: str = Field(max_length=255, exclude=True)  # bcrypt 哈希密码，exclude=True 防止序列化泄露
    email: str | None = Field(default=None, max_length=100)
    avatar: str | None = Field(default=None, max_length=500)  # 头像 URL
    major: str | None = Field(default=None, max_length=100)  # 专业
    grade: str | None = Field(default=None, max_length=20)  # 年级
    school: str | None = Field(default=None, max_length=100)  # 学校
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Auth — JWT Token 白名单（登出时从白名单移除）
# ---------------------------------------------------------------------------

class ActiveToken(SQLModel, table=True):
    """活跃 Token 白名单表 — 用于支持登出失效和强制下线"""
    __tablename__ = "active_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)  # 关联用户，支持按用户批量清理 token
    token: str = Field(unique=True, index=True)  # JWT 字符串，唯一索引用于快速查找
    expires_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))  # token 过期时间，用于清理过期记录
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


# ---------------------------------------------------------------------------
# Chat — 会话与消息（短期记忆载体）
# ---------------------------------------------------------------------------

class ChatSession(SQLModel, table=True):
    """会话表 — 管理多会话隔离，每个用户可以有多个独立会话"""
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)  # UUID 字符串主键
    user_id: int = Field(index=True)
    module: str = Field(index=True)  # 所属功能模块（如 "profile_builder"）
    title: str = Field(default="新对话", max_length=100)  # 会话标题（取首条消息前 20 字符）
    is_archived: bool = Field(default=False)  # 软删除标记

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)  # 每次写入消息时更新
    memory_token_count: int = Field(default=0)  # 记忆提取 token 累计（达到阈值触发记忆抽取）
    profile_token_count: int = Field(default=0)  # 画像更新 token 累计（达到阈值触发画像构建）


class ChatMessage(SQLModel, table=True):
    """聊天消息表 — 保存用户与助手的原始聊天记录，是短期记忆、长期记忆抽取和画像更新的事实来源"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_session_module_created_at", "user_id", "session_id", "module", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)  # 关联 ChatSession
    module: str = Field(default="profile_builder", index=True)
    role: str  # 消息角色："user" | "assistant" | "system" | "tool"
    content: str = Field(sa_column=Column(Text))  # 消息正文，使用 Text 类型支持长文本
    attachments: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 附件信息
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 工具调用记录
    diagram: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 图解数据（Mermaid 源码等）
    created_at: datetime = Field(default_factory=datetime.now, index=True)  # 创建时间索引，用于过期清理


# ---------------------------------------------------------------------------
# Memory — 长期记忆
# ---------------------------------------------------------------------------

class UserMemory(SQLModel, table=True):
    """长期记忆表 — 存储经过提炼的 Markdown 记忆内容。

    注意：
    - 长期记忆主体只保存 Markdown。
    - 不保存 content_json / memory_json。
    - JSONB 只用于附件等程序元数据。
    """
    __tablename__ = "user_memory"
    __table_args__ = (
        Index("ix_user_memory_context_lookup", "user_id", "module", "memory_type", "last_seen_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(default="", index=True)  # 来源会话
    module: str = Field(default="mentor", index=True)  # 所属功能模块（"mentor" | "avatar"），用于长期记忆隔离

    title: str | None = Field(default=None, max_length=200)  # 记忆标题
    content_markdown: str = Field(sa_column=Column(Text))  # 记忆主体 Markdown

    memory_type: str = Field(index=True)  # 类型：preference | goal | weakness | fact | background | summary
    dimension: str | None = None  # 可选维度标签（画像维度关联）
    importance: float = Field(default=0.5)  # 重要性评分 0.0~1.0
    source: str = Field(default="conversation", index=True)  # 来源："memory_extraction" | "conversation" | module名
    source_message_count: int = Field(default=0)  # 来源消息条数（用于压缩溯源）
    expires_at: datetime | None = Field(default=None)  # 过期时间（null 表示永不过期）
    evidence_count: int = Field(default=1)  # 该记忆被观察到的次数（去重累加）
    last_seen_at: datetime = Field(default_factory=datetime.now)  # 最后一次出现时间
    attachments: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 附件信息
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Profile — 用户画像及历史快照
# ---------------------------------------------------------------------------

class UserProfile(SQLModel, table=True):
    """用户画像表 — 存储当前学生画像 Markdown。

    主键为 user_id，与 User 表一对一。
    画像主体由大模型生成 Markdown。
    前端可直接渲染 Markdown，或按二级标题 `##` 切分为画像卡片。
    """
    __tablename__ = "user_profiles"

    user_id: int = Field(primary_key=True)  # 与 User.id 一对一

    profile_markdown: str = Field(sa_column=Column(Text))  # 画像主体 Markdown

    version: int = Field(default=1, index=True)  # 画像版本号
    confidence: float = Field(default=0.7)  # 画像置信度

    source_session_ids: list[str] | None = Field(default=None, sa_column=Column(JSONB))  # 来源会话 ID 列表
    source_memory_ids: list[int] | None = Field(default=None, sa_column=Column(ARRAY(Integer)))  # 触发画像更新的长期记忆 ID
    updated_reason: str | None = Field(default=None, sa_column=Column(Text))  # 画像更新原因

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserProfileHistory(SQLModel, table=True):
    """用户画像历史表 — 保存每次画像变更的 Markdown 快照"""
    __tablename__ = "user_profile_history"
    __table_args__ = (
        Index("ix_user_profile_history_user_version", "user_id", "version"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    version: int = Field(index=True)  # 版本号，每次更新递增

    profile_markdown: str = Field(sa_column=Column(Text))  # 画像快照 Markdown

    change_reason: str | None = Field(default=None, sa_column=Column(Text))  # 变更原因（如"系统自动更新"）
    source_session_ids: list[str] | None = Field(default=None, sa_column=Column(JSONB))  # 来源会话 ID 列表
    source_memory_ids: list[int] | None = Field(default=None, sa_column=Column(ARRAY(Integer)))  # 触发变更的记忆 ID 列表

    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Resource — 生成资源记录
# ---------------------------------------------------------------------------

class GeneratedResource(SQLModel, table=True):
    """生成资源主表 — 记录每次多智能体资源生成的输入参数和整体状态"""
    __tablename__ = "generated_resources"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    course: str = Field(max_length=200)  # 课程/主题名称
    gap: str = Field(sa_column=Column(Text))  # 知识缺口描述
    need: str = Field(default="review", max_length=50)  # 需求类型（如 "review"、"learn"）
    request_extra: str | None = Field(default=None, sa_column=Column(Text))  # 用户附加要求
    status: str = Field(default="pending", max_length=50)  # 整体生成状态
    plan_result: str | None = Field(default=None, sa_column=Column(Text))  # DAG 规划结果（JSON）
    created_at: datetime = Field(default_factory=datetime.now)


class ResourceMindmap(SQLModel, table=True):
    """思维导图资源子表"""
    __tablename__ = "resource_mindmaps"

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    file_path: str | None = Field(default=None, max_length=500)  # HTML文件路径
    content: str | None = Field(default=None, sa_column=Column(Text))  # Markdown原文
    status: str = Field(default="pending", max_length=50)  # pending/success/failed
    error: str | None = Field(default=None, sa_column=Column(Text))  # 错误信息
    created_at: datetime = Field(default_factory=datetime.now)


class ResourceContent(SQLModel, table=True):
    """内容讲解资源子表"""
    __tablename__ = "resource_contents"

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    file_path: str | None = Field(default=None, max_length=500)  # 文件路径
    content: str | None = Field(default=None, sa_column=Column(Text))  # 内容文本
    status: str = Field(default="pending", max_length=50)
    error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)


class ResourceQuiz(SQLModel, table=True):
    """练习题资源子表"""
    __tablename__ = "resource_quizzes"

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    file_path: str | None = Field(default=None, max_length=500)  # 文件路径
    content: str | None = Field(default=None, sa_column=Column(Text))  # 题目内容（JSON或文本）
    status: str = Field(default="pending", max_length=50)
    error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)


class ResourceReading(SQLModel, table=True):
    """延伸阅读资源子表"""
    __tablename__ = "resource_readings"

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    file_path: str | None = Field(default=None, max_length=500)  # 文件路径
    content: str | None = Field(default=None, sa_column=Column(Text))  # 阅读列表内容（JSON或文本）
    status: str = Field(default="pending", max_length=50)
    error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)


class ResourceCode(SQLModel, table=True):
    """代码实操资源子表"""
    __tablename__ = "resource_codes"

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    file_path: str | None = Field(default=None, max_length=500)  # 文件路径
    content: str | None = Field(default=None, sa_column=Column(Text))  # 分步讲解内容
    full_code: str | None = Field(default=None, sa_column=Column(Text))  # 完整代码
    language: str | None = Field(default=None, max_length=50)  # 编程语言
    status: str = Field(default="pending", max_length=50)
    error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)


class ResourceMedia(SQLModel, table=True):
    """多模态资源子表（PPT/图片/视频）"""
    __tablename__ = "resource_media"

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    media_type: str = Field(max_length=20, index=True)  # ppt/image/video
    file_path: str | None = Field(default=None, max_length=500)  # 文件路径
    status: str = Field(default="pending", max_length=50)
    error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Evaluation — 学习行为与效果评估
# ---------------------------------------------------------------------------

class LearningEvent(SQLModel, table=True):
    """学习行为事件表 — 记录资源使用、练习结果、路径反馈等评估信号。"""
    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_learning_events_user_session_created_at", "user_id", "session_id", "created_at"),
        Index("ix_learning_events_user_type_created_at", "user_id", "event_type", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str | None = Field(default=None, max_length=100, index=True)
    resource_id: int | None = Field(default=None, index=True)
    event_type: str = Field(max_length=50, index=True)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    score: float | None = Field(default=None)
    duration_seconds: int | None = Field(default=None)
    feedback: str | None = Field(default=None, sa_column=Column(Text))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------------------------------------------------------------------
# Model registration — init_db() 通过此元组获取所有需要建表的模型类
# ---------------------------------------------------------------------------

REGISTERED_MODELS = (
    ActiveToken,
    ChatSession,
    ChatMessage,
    UserMemory,
    UserProfile,
    UserProfileHistory,
    GeneratedResource,
    ResourceMindmap,
    ResourceContent,
    ResourceQuiz,
    ResourceReading,
    ResourceCode,
    ResourceMedia,
    LearningEvent,
    User,
)


def import_all_models() -> tuple[type, ...]:
    """返回已注册的模型类元组，同时确保所有模型类被导入以触发 SQLModel 元数据注册。
    init_db() 调用此函数后再执行 create_all，才能正确建表。"""
    logger.debug("[Models] 已注册 %d 个模型: %s",
                 len(REGISTERED_MODELS),
                 [m.__name__ for m in REGISTERED_MODELS])
    return REGISTERED_MODELS
