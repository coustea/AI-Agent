"""
统一 SQLModel 表定义。

所有数据库表集中在此文件中定义，按功能域分组：
  - User       用户基础信息
  - Auth       JWT Token 白名单
  - Chat       会话与消息
  - Memory     长期记忆（用户级单条）
  - Summary    会话概要（上下文压缩）
  - Profile    用户画像及历史快照
  - Resource   生成资源记录
  - Event      学习行为事件

新表应添加到 REGISTERED_MODELS 元组中，以便 init_db() 自动创建。

重构说明（v3）：
- Chat 会话压缩使用 ChatSessionSummaryBlock
- Chat 长期记忆使用 ChatLongTermMemory
- Profile 独立为共享模块，但仍复用 global_profiles / course_profiles
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ForeignKey, Integer, Text, Column, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlmodel import SQLModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# User — 用户基础信息
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    """用户基础信息表"""
    __tablename__ = "users"

    # 自增主键
    id: int | None = Field(default=None, primary_key=True)
    # 用户名，唯一索引
    username: str = Field(max_length=50, index=True, unique=True)
    # bcrypt 哈希密码，exclude=True 防止序列化泄露
    password: str = Field(max_length=255, exclude=True)
    email: str | None = Field(default=None, max_length=100)
    # 头像 URL
    avatar: str | None = Field(default=None, max_length=500)
    # onboarding 是否已完成，True=已完成，False=未完成（需弹窗）
    is_first_login: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Auth — JWT Token 白名单（登出时从白名单移除）
# ---------------------------------------------------------------------------

class ActiveToken(SQLModel, table=True):
    """活跃 Token 白名单表 — 用于支持登出失效和强制下线"""
    __tablename__ = "active_tokens"

    id: int | None = Field(default=None, primary_key=True)
    # 关联用户，支持按用户批量清理 token
    user_id: int = Field(index=True)
    # JWT 字符串，唯一索引用于快速查找
    token: str = Field(unique=True, index=True)
    # token 过期时间，用于清理过期记录
    expires_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )

class School(SQLModel, table=True):
    """学校存储"""
    __tablename__ = "schools"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    # 办学层次：本科/专科
    level: str | None = Field(default=None, max_length=50)
    # 院校层次：985/211/双一流/普通本科/专科
    tier: str | None = Field(default=None, max_length=20)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )

# ---------------------------------------------------------------------------
# Chat — 会话与消息
# ---------------------------------------------------------------------------

class ChatSession(SQLModel, table=True):
    """会话表 — 管理多会话隔离，每个用户可以有多个独立会话"""
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index(
            "ix_chat_sessions_user_module_archived_updated",
            "user_id",
            "module",
            "is_archived",
            text("updated_at DESC"),
        ),
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    # UUID 原生类型主键
    user_id: int = Field(index=True)
    # 所属功能模块（如 "mentor"）
    module: str = Field(default="mentor", index=True)
    # 会话标题（取首条消息前 20 字符）
    title: str = Field(default="新对话", max_length=100)
    # 软删除标记
    is_archived: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )
    summary_token_count: int = Field(default=0)
    profile_token_count: int = Field(default=0)
    profile_message_count: int = Field(default=0)
    ltm_token_count: int = Field(default=0)
    ltm_message_count: int = Field(default=0)
    last_profile_message_id: int | None = Field(default=None)
    last_ltm_message_id: int | None = Field(default=None)
    last_profile_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )
    last_ltm_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )


class ChatTurn(SQLModel, table=True):
    """聊天轮次表 — 记录一次用户输入到助手完成响应的完整执行。"""
    __tablename__ = "chat_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_chat_turns_session_turn_index"),
        Index("ix_chat_turns_user_session_created_at", "user_id", "session_id", "created_at"),
        Index("ix_chat_turns_user_session_status", "user_id", "session_id", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    module: str = Field(default="mentor", index=True)
    turn_index: int = Field(default=1, index=True)
    status: str = Field(default="running", max_length=32, index=True)
    route: str = Field(default="default", max_length=50, index=True)
    execution_mode: str = Field(default="default", max_length=50, index=True)
    has_attachments: bool = Field(default=False)
    used_web_search: bool = Field(default=False)
    used_teaching_diagram: bool = Field(default=False)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True), index=True))


class ChatMessage(SQLModel, table=True):
    """聊天消息表 — 保存用户与助手的原始聊天记录"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_session_module_created_at", "user_id", "session_id", "module", "created_at"),
        Index("ix_chat_messages_session_turn_created_at", "session_id", "turn_id", "created_at"),
        Index("ix_chat_messages_attachments", "attachments", postgresql_using="gin"),
        Index("ix_chat_messages_knowledge_sources", "knowledge_sources", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    # 关联 ChatSession（UUID 类型，与 ChatSession.id 一致）
    turn_id: int | None = Field(default=None, index=True)
    module: str = Field(default="mentor", index=True)
    # 消息角色："user" | "assistant" | "system" | "tool"
    role: str
    message_kind: str | None = Field(default=None, max_length=50, index=True)
    # 消息正文，使用 Text 类型支持长文本
    content: str = Field(sa_column=Column(Text))
    # 附件信息
    attachments: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))
    # 工具调用记录
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))
    tool_call_id: str | None = Field(default=None, max_length=120, index=True)
    knowledge_sources: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))
    # 教学图解数据
    teaching_diagram: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    # 记录该条消息消耗的精准 Token
    usage_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


# ---------------------------------------------------------------------------
# Summary — 会话概要（上下文压缩）
# ---------------------------------------------------------------------------

class ChatSessionSummaryBlock(SQLModel, table=True):
    """会话摘要块表 — 按时间顺序保存已压缩会话块。"""
    __tablename__ = "chat_session_summary_blocks"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "module",
            "block_index",
            name="uq_chat_session_summary_blocks_session_module_block",
        ),
        Index(
            "ix_chat_session_summary_blocks_user_session_module_created_at",
            "user_id",
            "session_id",
            "module",
            text("created_at DESC"),
        ),
        Index(
            "ix_chat_session_summary_blocks_user_session_module_block",
            "user_id",
            "session_id",
            "module",
            text("block_index DESC"),
        ),
        Index("ix_chat_session_summary_blocks_topics", "topics", postgresql_using="gin"),
        Index("ix_chat_session_summary_blocks_keywords", "keywords", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    # 关联 ChatSession（UUID 类型，与 ChatSession.id 一致）
    # 所属功能模块
    module: str = Field(default="mentor", index=True)

    block_index: int = Field(default=1, index=True)
    summary_markdown: str = Field(sa_column=Column(Text))
    summary_type: str = Field(default="incremental", max_length=50)
    version: int = Field(default=1)
    start_message_id: int | None = Field(default=None)
    end_message_id: int | None = Field(default=None)
    start_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    end_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    summarized_message_count: int = Field(default=0)
    topics: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    keywords: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Memory — 长期记忆（用户级单条）
# ---------------------------------------------------------------------------

class ChatLongTermMemory(SQLModel, table=True):
    """Chat 长期记忆表 — 一个用户在一个 chat module 下只有一条长期记忆

    设计原则：
    - 只保存长期稳定、未来可复用的信息
    - 不保存当前会话临时状态、一次性作业中间状态
    - memory_markdown 是唯一权威来源（给 LLM 上下文用）
    """
    __tablename__ = "chat_long_term_memories"
    __table_args__ = (
        UniqueConstraint("user_id", "module", name="uq_chat_long_term_memory_user_module"),
        Index("ix_chat_long_term_memories_source_session_ids", "source_session_ids", postgresql_using="gin"),
        Index("ix_chat_long_term_memories_source_message_ids", "source_message_ids", postgresql_using="gin"),
        Index("ix_chat_long_term_memories_source_summary_block_ids", "source_summary_block_ids", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    memory_markdown: str = Field(sa_column=Column(Text))  # 记忆主体 Markdown（唯一权威来源）
    category: str = Field(default="general", max_length=50, index=True)  # 记忆分类

    version: int = Field(default=1)  # 记忆版本号
    confidence: float = Field(default=0.7)  # 记忆置信度

    source_session_ids: list[str] | None = Field(default=None, sa_column=Column(JSONB))  # 来源会话 ID 列表
    source_message_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))  # 来源消息 ID 列表
    source_summary_block_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))
    updated_reason: str | None = Field(default=None, sa_column=Column(Text))  # 更新原因

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class ChatAttachmentAnalysis(SQLModel, table=True):
    """附件分析结果表。"""
    __tablename__ = "chat_attachment_analyses"
    __table_args__ = (
        Index("ix_chat_attachment_analyses_user_session_created_at", "user_id", "session_id", "created_at"),
        Index("ix_chat_attachment_analyses_message_id", "message_id"),
        Index("ix_chat_attachment_analyses_file_id", "file_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    message_id: int | None = Field(default=None, index=True)
    file_id: int | None = Field(default=None, index=True)
    file_name: str | None = Field(default=None, max_length=255)
    file_url: str | None = Field(default=None, max_length=1000)
    turn_id: int | None = Field(default=None, index=True)
    module: str = Field(default="mentor", index=True)
    analysis_type: str = Field(max_length=50, index=True)
    summary_text: str = Field(sa_column=Column(Text))
    extracted_text: str | None = Field(default=None, sa_column=Column(Text))
    structured_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


class ChatUploadedFile(SQLModel, table=True):
    """聊天上传文件元数据表。"""
    __tablename__ = "chat_uploaded_files"
    __table_args__ = (
        Index("ix_chat_uploaded_files_user_session_created_at", "user_id", "session_id", "created_at"),
        Index("ix_chat_uploaded_files_storage_key", "storage_key"),
        Index("ix_chat_uploaded_files_file_kind", "file_kind"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    module: str = Field(default="mentor", index=True)
    storage_url: str = Field(max_length=1000)
    storage_key: str | None = Field(default=None, max_length=500)
    original_name: str = Field(max_length=255)
    file_kind: str = Field(max_length=32, index=True)
    mime_type: str | None = Field(default=None, max_length=120)
    extension: str | None = Field(default=None, max_length=20)
    size_bytes: int = Field(default=0, ge=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


class ChatMessageAttachment(SQLModel, table=True):
    """消息与附件关联表。"""
    __tablename__ = "chat_message_attachments"
    __table_args__ = (
        Index("ix_chat_message_attachments_message_id", "message_id"),
        Index("ix_chat_message_attachments_file_id", "file_id"),
        Index("ix_chat_message_attachments_turn_id", "turn_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    message_id: int = Field(index=True)
    file_id: int = Field(index=True)
    turn_id: int | None = Field(default=None, index=True)
    module: str = Field(default="mentor", index=True)
    attachment_order: int = Field(default=0, ge=0)
    attachment_role: str = Field(default="input", max_length=32)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


class ChatToolInvocation(SQLModel, table=True):
    """工具调用记录表。"""
    __tablename__ = "chat_tool_invocations"
    __table_args__ = (
        Index("ix_chat_tool_invocations_user_session_created_at", "user_id", "session_id", "created_at"),
        Index("ix_chat_tool_invocations_assistant_message_id", "assistant_message_id"),
        Index("ix_chat_tool_invocations_tool_message_id", "tool_message_id"),
        Index("ix_chat_tool_invocations_tool_call_id", "tool_call_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )
    turn_id: int | None = Field(default=None, index=True)
    module: str = Field(default="mentor", index=True)
    assistant_message_id: int | None = Field(default=None, index=True)
    tool_message_id: int | None = Field(default=None, index=True)
    tool_call_id: str = Field(max_length=120, index=True)
    tool_name: str = Field(max_length=120, index=True)
    arguments_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    result_text: str | None = Field(default=None, sa_column=Column(Text))
    result_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    status: str = Field(default="success", max_length=32, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


class ChatTurnTranscript(SQLModel, table=True):
    """对话轮 transcript 源数据表。"""
    __tablename__ = "chat_turn_transcripts"
    __table_args__ = (
        UniqueConstraint("turn_id", name="uq_chat_turn_transcripts_turn_id"),
        Index("ix_chat_turn_transcripts_turn_id", "turn_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    turn_id: int = Field(index=True)
    transcript_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    final_answer: str = Field(default="", sa_column=Column(Text))
    constraint_report_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Profile — 用户画像及历史快照
# ---------------------------------------------------------------------------

class GlobalProfile(SQLModel, table=True):
    """全局主画像表"""
    __tablename__ = "global_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "module", name="uq_global_profile_user_module"),
        Index("ix_global_profiles_profile_json", "profile_json", postgresql_using="gin"),
        Index("ix_global_profiles_profile_score_json", "profile_score_json", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)

    profile_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    profile_score_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )

class CourseProfile(SQLModel, table=True):
    """课程子画像表"""
    __tablename__ = "course_profiles"
    __table_args__ = (
        UniqueConstraint("global_profile_id", "course_key", name="uq_course_profile_global_course_key"),
    )

    id: int | None = Field(default=None, primary_key=True)
    global_profile_id: int = Field(sa_column=Column(Integer, ForeignKey("global_profiles.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)
    course_key: str = Field(max_length=200, index=True)
    course_name: str = Field(max_length=200, index=True)
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    profile_markdown: str = Field(default="", sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Resource — 生成资源记录
# ---------------------------------------------------------------------------

class GeneratedResource(SQLModel, table=True):
    """生成资源主表 — 记录每次多智能体资源生成的输入参数。"""
    __tablename__ = "generated_resources"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    # 输入信息 — 用户自然语言描述
    learning_need: str | None = Field(default=None, sa_column=Column(Text))

    # 配置信息
    teaching_plan: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    review_result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    failed_agents: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    workflow_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    selected_agents: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    agent_configs: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    source: str | None = Field(default=None, max_length=255, index=True)

    # 状态
    status: str = Field(default="pending", max_length=50)
    error_message: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class GeneratedResourceItem(SQLModel, table=True):
    """资源项明细表 — 每个 agent 生成一个资源项。"""
    __tablename__ = "generated_resource_items"
    __table_args__ = (
        Index("ix_generated_resource_items_content_json", "content_json", postgresql_using="gin"),
        Index("ix_generated_resource_items_metadata_json", "metadata_json", postgresql_using="gin"),
        Index("ix_generated_resource_items_metrics", "metrics", postgresql_using="gin"),
        Index("ix_generated_resource_items_downstream_context", "downstream_context", postgresql_using="gin"),
        Index("ix_generated_resource_items_covered_knowledge_points", "covered_knowledge_points", postgresql_using="gin"),
        Index("ix_generated_resource_items_weak_points_covered", "weak_points_covered", postgresql_using="gin"),
        Index("ix_generated_resource_items_resource_agent", "resource_id", "agent_type"),
        Index("ix_generated_resource_items_user_created_at", "user_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(sa_column=Column(Integer, ForeignKey("generated_resources.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)

    # Agent 类型（content/mindmap/quiz/code/reading/ppt）
    agent_type: str = Field(max_length=50, index=True)

    # 内容格式（markdown/json/text/code）
    content_format: str = Field(default="json", max_length=50)

    # 展示与契约信息
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, sa_column=Column(Text))
    output_contract: str | None = Field(default=None, max_length=80)
    generated_by: str | None = Field(default=None, max_length=50, index=True)

    # 内容主体（根据 content_format 选择存储位置）
    content_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    content_text: str | None = Field(default=None, sa_column=Column(Text))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    metrics: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    downstream_context: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    status: str = Field(default="pending", max_length=50)
    error_message: str | None = Field(default=None, sa_column=Column(Text))

    # Agent 协作与路径规划检索字段
    depends_on_agents: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    source_resource_item_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))
    covered_knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    weak_points_covered: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    recommended_next_resource_types: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    # Agent 执行报告
    execution_report: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Quiz Bank - 题库题目
# ---------------------------------------------------------------------------

class QuizQuestion(SQLModel, table=True):
    """题库题目表，存储离线整理后的标准化题目记录。"""
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("question_id", name="uq_quiz_questions_question_id"),
        Index("ix_quiz_questions_subject_type", "subject", "question_type"),
        Index("ix_quiz_questions_subject_en_type", "subject_en", "question_type"),
        Index("ix_quiz_questions_difficulty", "difficulty"),
        Index("ix_quiz_questions_tags", "tags", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    question_id: str = Field(max_length=255, index=True)
    source: str | None = Field(default=None, max_length=255, index=True)
    subject: str = Field(max_length=255, index=True)
    subject_en: str | None = Field(default=None, max_length=255, index=True)
    question_type: str = Field(max_length=100, index=True)
    difficulty: str | None = Field(default=None, max_length=100, index=True)
    bloom_level: str | None = Field(default=None, max_length=100)
    content: str = Field(sa_column=Column(Text))
    options_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    answer: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    language: str | None = Field(default=None, max_length=32, index=True)
    split: str | None = Field(default=None, max_length=64, index=True)
    source_file: str | None = Field(default=None, max_length=500)
    raw_record: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Evaluation – 学习行为与效果评估
# ---------------------------------------------------------------------------

class LearningEvent(SQLModel, table=True):
    """学习行为事件表 — 记录资源使用、练习结果、路径反馈等评估信号。"""
    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_learning_events_user_session_created_at", "user_id", "session_id", "created_at"),
        Index("ix_learning_events_user_type_created_at", "user_id", "event_type", "created_at"),
        Index("ix_learning_events_metadata_json", "metadata_json", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str | None = Field(default=None, max_length=100, index=True)
    resource_id: int | None = Field(default=None, index=True)
    resource_item_id: int | None = Field(default=None, index=True)
    path_id: int | None = Field(default=None, index=True)
    path_node_id: int | None = Field(default=None, index=True)
    node_id: str | None = Field(default=None, max_length=50, index=True)
    event_type: str = Field(max_length=50, index=True)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    score: float | None = Field(default=None)
    feedback: str | None = Field(default=None, sa_column=Column(Text))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


class LearningSession(SQLModel, table=True):
    """学习会话表 — 记录用户在某个学习页面上的实际活跃时长。"""
    __tablename__ = "learning_sessions"
    __table_args__ = (
        Index("ix_learning_sessions_user_started_at", "user_id", "started_at"),
        Index("ix_learning_sessions_user_source_page", "user_id", "source_page"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    source_page: str = Field(max_length=50, description="来源页面标识")
    started_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), index=True))
    ended_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    duration_seconds: int = Field(ge=1, le=86400, description="实际活跃时长(秒)")
    resource_id: int | None = Field(default=None)
    path_id: int | None = Field(default=None)
    path_node_id: int | None = Field(default=None)
    node_id: str | None = Field(default=None, max_length=50)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


# ---------------------------------------------------------------------------
# Learning Path V2 — 新学习路径域
# ---------------------------------------------------------------------------

class LearningPath(SQLModel, table=True):
    """学习路径主表。"""
    __tablename__ = "learning_paths"
    __table_args__ = (
        Index("ix_learning_paths_user_module_status", "user_id", "module", "status"),
        Index("ix_learning_paths_user_module_updated", "user_id", "module", "updated_at"),
        Index("ix_learning_paths_stages_json", "stages_json", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)
    title: str = Field(max_length=200)
    goal: str = Field(sa_column=Column(Text))
    topic: str | None = Field(default=None, sa_column=Column(Text))

    overall_progress: int = Field(default=0, ge=0, le=100)
    current_node_key: str | None = Field(default=None, max_length=80, index=True)
    eta_days: int = Field(default=14, ge=1)
    confidence: int = Field(default=60, ge=0, le=100)
    status: str = Field(default="active", max_length=30, index=True)

    stages_json: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class PathNode(SQLModel, table=True):
    """学习路径节点表。"""
    __tablename__ = "path_nodes"
    __table_args__ = (
        Index("ix_path_nodes_path_stage", "path_id", "stage_id"),
        Index("ix_path_nodes_user_status", "user_id", "status"),
        Index("ix_path_nodes_path_priority", "path_id", "priority"),
        Index("ix_path_nodes_prerequisites", "prerequisites", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)

    node_id: str = Field(max_length=80, index=True)
    stage_id: str = Field(max_length=80, index=True)
    title: str = Field(max_length=200)

    status: str = Field(default="locked", max_length=32, index=True)
    priority: int = Field(default=0)
    attempt_count: int = Field(default=0, ge=0)
    current_tutorial_id: int | None = Field(default=None, index=True)

    prerequisites: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    resource_policy: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    mastery_target: str | None = Field(default=None, sa_column=Column(Text))
    estimated_minutes: int | None = Field(default=None)
    difficulty: str | None = Field(default=None, max_length=30)
    recommendation_reason: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )
    started_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))


class PathNodeTutorial(SQLModel, table=True):
    """节点教程版本表。"""
    __tablename__ = "path_node_tutorials"
    __table_args__ = (
        Index("ix_path_node_tutorials_node_current", "node_id", "is_current"),
        Index("ix_path_node_tutorials_node_type", "node_id", "tutorial_type"),
        Index("ix_path_node_tutorials_based_on", "based_on_tutorial_id"),
        Index("ix_path_node_tutorials_knowledge_points", "knowledge_points", postgresql_using="gin"),
        Index("ix_path_node_tutorials_weak_points", "weak_knowledge_points", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True))
    node_id: int = Field(sa_column=Column(Integer, ForeignKey("path_nodes.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)

    tutorial_type: str = Field(default="primary", max_length=32, index=True)
    version_no: int = Field(default=1, ge=1)
    based_on_tutorial_id: int | None = Field(default=None, index=True)
    is_current: bool = Field(default=True, index=True)

    title: str = Field(max_length=200)
    summary: str | None = Field(default=None, sa_column=Column(Text))
    content_markdown: str = Field(sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    weak_knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class PathNodeQuestion(SQLModel, table=True):
    """节点测验题与作答快照表。"""
    __tablename__ = "path_node_questions"
    __table_args__ = (
        Index("ix_path_node_questions_node_round", "node_id", "round_no"),
        Index("ix_path_node_questions_tutorial_round", "tutorial_id", "round_no"),
        Index("ix_path_node_questions_knowledge_points", "knowledge_points", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True))
    node_id: int = Field(sa_column=Column(Integer, ForeignKey("path_nodes.id", ondelete="CASCADE"), index=True))
    tutorial_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("path_node_tutorials.id", ondelete="SET NULL"), index=True))
    user_id: int = Field(index=True)

    round_no: int = Field(default=1, ge=1)
    question_no: int = Field(default=1, ge=1, le=5)
    mode: str = Field(default="quiz", max_length=32)
    type: str = Field(default="single_choice", max_length=32)

    question: str = Field(sa_column=Column(Text))
    choice: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    answer: str = Field(sa_column=Column(Text))
    response: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    is_correct: bool | None = Field(default=None, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )
    submitted_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))


class PathNodeResource(SQLModel, table=True):
    """节点额外资源表。"""
    __tablename__ = "path_node_resources"
    __table_args__ = (
        Index("ix_path_node_resources_node_type", "node_id", "resource_type"),
        Index("ix_path_node_resources_content_json", "content_json", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True))
    node_id: int = Field(sa_column=Column(Integer, ForeignKey("path_nodes.id", ondelete="CASCADE"), index=True))
    tutorial_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("path_node_tutorials.id", ondelete="SET NULL"), index=True))
    user_id: int = Field(index=True)

    resource_type: str = Field(max_length=32, index=True)
    version_no: int = Field(default=1, ge=1)
    title: str = Field(max_length=200)
    content_format: str = Field(default="markdown", max_length=32)
    content_text: str | None = Field(default=None, sa_column=Column(Text))
    content_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="completed", max_length=32)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    input_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Wrong Question — 错题本
# ---------------------------------------------------------------------------

class WrongQuestion(SQLModel, table=True):
    """错题本表 — 记录用户答错的题目"""
    __tablename__ = "wrong_questions"
    __table_args__ = (
        Index("ix_wrong_questions_user_id", "user_id"),
        Index("ix_wrong_questions_user_question", "user_id", "question_id", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    question_id: str = Field(max_length=255, index=True)  # 关联 QuizQuestion.question_id

    # 快照字段（避免题目被删除后无法查看）
    subject: str = Field(max_length=255)
    question_type: str = Field(max_length=100)
    content: str = Field(sa_column=Column(Text))
    options_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    standard_answer: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))

    # 错误信息
    user_answer: str | None = Field(default=None, sa_column=Column(Text))  # 用户当时答错的答案
    wrong_count: int = Field(default=1)  # 累计错误次数

    # 用户标记
    note: str | None = Field(default=None, sa_column=Column(Text))  # 用户笔记
    is_archived: bool = Field(default=False)  # 是否已归档（手动移除）

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Model registration — init_db() 通过此元组获取所有需要建表的模型类
# ---------------------------------------------------------------------------

REGISTERED_MODELS = (
    ActiveToken,
    ChatSession,
    ChatTurn,
    ChatMessage,
    ChatSessionSummaryBlock,
    ChatAttachmentAnalysis,
    ChatUploadedFile,
    ChatMessageAttachment,
    ChatToolInvocation,
    ChatTurnTranscript,
    ChatLongTermMemory,
    GlobalProfile,
    CourseProfile,
    GeneratedResource,
    GeneratedResourceItem,
    QuizQuestion,
    LearningEvent,
    LearningSession,
    LearningPath,
    PathNode,
    PathNodeTutorial,
    PathNodeQuestion,
    PathNodeResource,
    User,
    School,
    WrongQuestion,
)
