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

重构说明（v2）：
- 删除 UserMemory（多条记忆模式）
- 新增 UserLongTermMemory（用户级单条长期记忆）
- 新增 ChatSessionSummary（会话概要）
- 修改 UserProfile（增加 profile_json、profile_score_json、module 字段）
- 修改 UserProfileHistory（增加 profile_json、profile_score_json、module 字段）
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ForeignKey, Integer, Text, Column, Index, UniqueConstraint, func
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

    id: int | None = Field(default=None, primary_key=True)  # 自增主键
    username: str = Field(max_length=50, index=True, unique=True)  # 用户名，唯一索引
    password: str = Field(max_length=255, exclude=True)  # bcrypt 哈希密码，exclude=True 防止序列化泄露
    email: str | None = Field(default=None, max_length=100)
    avatar: str | None = Field(default=None, max_length=500)  # 头像 URL
    is_first_login: bool = Field(default=True)  # 是否首次登录，完成后置 False

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
    user_id: int = Field(index=True)  # 关联用户，支持按用户批量清理 token
    token: str = Field(unique=True, index=True)  # JWT 字符串，唯一索引用于快速查找
    expires_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))  # token 过期时间，用于清理过期记录
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )

class School(SQLModel, table=True):
    """学校存储"""
    __tablename__ = "schools"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    level: str | None = Field(default=None, max_length=50)  # 办学层次：本科/专科
    tier: str | None = Field(default=None, max_length=20)  # 院校层次：985/211/双一流/普通本科/专科
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
        Index("ix_chat_sessions_attachment_analyses", "attachment_analyses", postgresql_using="gin"),
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )  # UUID 原生类型主键
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块（如 "mentor"）
    title: str = Field(default="新对话", max_length=100)  # 会话标题（取首条消息前 20 字符）
    is_archived: bool = Field(default=False)  # 软删除标记

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )
    # 会话概要触发计数器
    summary_token_count: int = Field(default=0)  # 累计 token 数，达到阈值触发会话概要生成
    # 附件预分析结果持久化（按消息ID索引）
    attachment_analyses: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))


class ChatMessage(SQLModel, table=True):
    """聊天消息表 — 保存用户与助手的原始聊天记录"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_session_module_created_at", "user_id", "session_id", "module", "created_at"),
        Index("ix_chat_messages_attachments", "attachments", postgresql_using="gin"),
        Index("ix_chat_messages_tool_calls", "tool_calls", postgresql_using="gin"),
        Index("ix_chat_messages_teaching_diagram", "teaching_diagram", postgresql_using="gin"),
        Index("ix_chat_messages_usage_metadata", "usage_metadata", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )  # 关联 ChatSession（UUID 类型，与 ChatSession.id 一致）
    module: str = Field(default="mentor", index=True)
    role: str  # 消息角色："user" | "assistant" | "system" | "tool"
    content: str = Field(sa_column=Column(Text))  # 消息正文，使用 Text 类型支持长文本
    attachments: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 附件信息
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 工具调用记录
    teaching_diagram: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 教学图解数据
    usage_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 记录该条消息消耗的精准 Token
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


# ---------------------------------------------------------------------------
# Summary — 会话概要（上下文压缩）
# ---------------------------------------------------------------------------

class ChatSessionSummary(SQLModel, table=True):
    """会话概要表 — 保存上下文压缩结果，一个会话可以有多个概要"""
    __tablename__ = "chat_session_summaries"
    __table_args__ = (
        Index("ix_chat_session_summaries_user_session_created_at", "user_id", "session_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), index=True),
    )  # 关联 ChatSession（UUID 类型，与 ChatSession.id 一致）
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    summary_markdown: str = Field(sa_column=Column(Text))  # 概要主体 Markdown（唯一权威来源）

    summary_type: str = Field(default="incremental", max_length=50)  # 概要类型：incremental | full
    version: int = Field(default=1)  # 概要版本号

    start_message_id: int | None = Field(default=None)  # 起始消息 ID
    end_message_id: int | None = Field(default=None)  # 结束消息 ID
    summarized_message_count: int = Field(default=0)  # 已压缩消息数量

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

class UserLongTermMemory(SQLModel, table=True):
    """用户长期记忆表 — 一个用户在一个 module 下只有一条长期记忆

    设计原则：
    - 只保存长期稳定、未来可复用的信息
    - 不保存当前会话临时状态、一次性作业中间状态
    - memory_markdown 是唯一权威来源（给 LLM 上下文用）
    """
    __tablename__ = "user_long_term_memories"
    __table_args__ = (
        UniqueConstraint("user_id", "module", name="uq_user_long_term_memory_user_module"),
        Index("ix_user_long_term_memories_source_session_ids", "source_session_ids", postgresql_using="gin"),
        Index("ix_user_long_term_memories_source_message_ids", "source_message_ids", postgresql_using="gin"),
        Index("ix_user_long_term_memories_source_summary_ids", "source_summary_ids", postgresql_using="gin"),
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
    source_summary_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))  # 来源概要 ID 列表
    updated_reason: str | None = Field(default=None, sa_column=Column(Text))  # 更新原因

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


# ---------------------------------------------------------------------------
# Profile — 用户画像及历史快照
# ---------------------------------------------------------------------------

class UserProfile(SQLModel, table=True):
    """用户画像表 — 一个用户在一个 module 下只有一条当前画像
    
    设计原则：
    - profile_json 是文字画像权威来源
    - profile_score_json 是评分画像权威来源
    """
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "module", name="uq_user_profile_user_module"),
        Index("ix_user_profiles_profile_json", "profile_json", postgresql_using="gin"),
        Index("ix_user_profiles_profile_score_json", "profile_score_json", postgresql_using="gin"),
        Index("ix_user_profiles_source_session_ids", "source_session_ids", postgresql_using="gin"),
        Index("ix_user_profiles_source_summary_ids", "source_summary_ids", postgresql_using="gin"),
        Index("ix_user_profiles_source_event_ids", "source_event_ids", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)  # 改为 id 主键
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    profile_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 文字画像 JSON
    profile_score_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 分数画像 JSON
    profile_markdown: str | None = Field(default=None, sa_column=Column(Text))  # 画像 Markdown 渲染缓存

    version: int = Field(default=1)  # 画像版本号
    confidence: float = Field(default=0.7)  # 画像整体置信度

    source_memory_version: int | None = Field(default=None)  # 来源长期记忆版本
    source_session_ids: list[str] | None = Field(default=None, sa_column=Column(JSONB))  # 来源会话 ID 列表
    source_summary_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))  # 来源概要 ID 列表
    source_event_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))  # 来源学习事件 ID 列表
    updated_reason: str | None = Field(default=None, sa_column=Column(Text))  # 更新原因

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class UserProfileHistory(SQLModel, table=True):
    """用户画像历史表 — 保存每次画像变更的快照"""
    __tablename__ = "user_profile_history"
    __table_args__ = (
        Index("ix_user_profile_history_profile_json", "profile_json", postgresql_using="gin"),
        Index("ix_user_profile_history_profile_score_json", "profile_score_json", postgresql_using="gin"),
        Index("ix_user_profile_history_user_module_version", "user_id", "module", "version"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    version: int = Field(index=True)  # 版本号，每次更新递增

    profile_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 文字画像快照 JSON
    profile_score_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 分数画像快照 JSON
    profile_markdown: str | None = Field(default=None, sa_column=Column(Text))  # 画像 Markdown 快照缓存

    change_reason: str | None = Field(default=None, sa_column=Column(Text))  # 变更原因

    source_memory_version: int | None = Field(default=None)  # 来源长期记忆版本
    source_session_ids: list[str] | None = Field(default=None, sa_column=Column(JSONB))  # 来源会话 ID 列表
    source_summary_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))  # 来源概要 ID 列表
    source_event_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))  # 来源学习事件 ID 列表

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
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
    personalization: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    selected_agents: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    agent_configs: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

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

    # Agent 协作与路径规划检索字段
    depends_on_agents: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    source_resource_item_ids: list[int] | None = Field(default=None, sa_column=Column(JSONB))
    covered_knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    weak_points_covered: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    recommended_next_resource_types: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    # Agent 执行报告
    execution_report: str | None = Field(default=None, sa_column=Column(Text))

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
        Index("ix_quiz_questions_options_json", "options_json", postgresql_using="gin"),
        Index("ix_quiz_questions_knowledge_points", "knowledge_points", postgresql_using="gin"),
        Index("ix_quiz_questions_tags", "tags", postgresql_using="gin"),
        Index("ix_quiz_questions_raw_record", "raw_record", postgresql_using="gin"),
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
# Path — 课程级学习路径规划 (Course Path)
# ---------------------------------------------------------------------------

class CoursePathGenerationTask(SQLModel, table=True):
    """路径规划任务表 — 保存慢速规划过程的真实进度快照。"""
    __tablename__ = "course_path_generation_tasks"
    __table_args__ = (
        Index("ix_path_generation_tasks_user_module_status", "user_id", "module", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)
    goal: str = Field(sa_column=Column(Text))
    topic: str = Field(default="", sa_column=Column(Text))
    current_knowledge: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    preferences: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    status: str = Field(default="pending", max_length=30, index=True)
    progress: int = Field(default=0, ge=0, le=100)
    latest_message: str = Field(default="规划任务已创建，等待开始", sa_column=Column(Text))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    generated_path_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("course_paths.id", ondelete="SET NULL"), index=True))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    started_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class CoursePath(SQLModel, table=True):
    """课程级学习路径表 — 记录用户在特定目标下的学习路线图。"""
    __tablename__ = "course_paths"
    __table_args__ = (
        Index("ix_course_paths_user_module_status", "user_id", "module", "status"),
        Index("ix_course_paths_stages_json", "stages_json", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)

    # 路径配置
    title: str = Field(max_length=200)
    goal: str = Field(sa_column=Column(Text))
    
    # 进度信息
    overall_progress: int = Field(default=0, ge=0, le=100)
    current_stage_id: str | None = Field(default=None, max_length=50)
    current_node_id: str | None = Field(default=None, max_length=50)

    # 预估信息
    eta_days: int = Field(default=14, ge=1)
    confidence: int = Field(default=60, ge=0, le=100)

    # 版本与状态
    version: int = Field(default=1)
    status: str = Field(default="active", max_length=30, index=True)  # active, completed, archived

    # 宏观阶段框架 (来自大模型生成的 Stages)
    stages_json: list[dict] | None = Field(default=None, sa_column=Column(JSONB))

    # 规划原因/依据 (来自大模型)
    adjustment_rationale: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    # 个性化诊断与裁剪策略报告 (来自多智能体规划第一棒)
    strategy_report: str | None = Field(default=None, sa_column=Column(Text))

    # 搜索证据与学习效果摘要
    search_evidence: list[dict] | None = Field(default=None, sa_column=Column(JSONB), description="搜索证据摘要")
    learning_signal_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB), description="学习效果摘要")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class CoursePathNode(SQLModel, table=True):
    """课程路径节点表 — 记录地图上的每一个学习节点（能力点/知识点）。"""
    __tablename__ = "course_path_nodes"
    __table_args__ = (
        Index("ix_course_path_nodes_path_stage", "path_id", "stage_id"),
        Index("ix_course_path_nodes_user_status", "user_id", "status"),
        Index("ix_course_path_nodes_prerequisites", "prerequisites", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("course_paths.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)

    # 节点标识
    node_id: str = Field(max_length=50, index=True)  # 节点唯一标识
    stage_id: str = Field(max_length=50)  # 所属阶段 (如 foundation, core, extension)
    title: str = Field(max_length=200)

    # 节点状态
    status: str = Field(default="locked", max_length=20)  # locked, available, in_progress, completed
    resource_status: str = Field(default="not_started", max_length=20)  # not_started, generating, ready, failed
    progress: int = Field(default=0, ge=0, le=100)
    priority: int = Field(default=50, ge=0, le=100)

    # 节点元数据
    prerequisites: list[str] | None = Field(default=None, sa_column=Column(JSONB))  # 前置节点 ID 列表
    mastery_target: str | None = Field(default=None, sa_column=Column(Text))  # 掌握目标
    estimated_minutes: int | None = Field(default=None)  # 预计花费时间
    difficulty: str | None = Field(default=None, max_length=30)  # beginner, intermediate, advanced

    # 推荐原因（基于画像维度的推荐理由）
    recommendation_reason: str | None = Field(default=None, sa_column=Column(Text))

    # 资源推送策略
    resource_policy: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB), description="资源推送策略")

    # 完成信息
    started_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class CoursePathResourceBinding(SQLModel, table=True):
    """课程路径节点与实际生成资源的绑定关系。"""
    __tablename__ = "course_path_resource_bindings"
    __table_args__ = (
        Index("ix_course_path_resource_bindings_node", "node_id"),
        Index("ix_course_path_resource_bindings_resource", "resource_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    
    node_id: int = Field(sa_column=Column(Integer, ForeignKey("course_path_nodes.id", ondelete="CASCADE"), index=True))
    resource_id: int = Field(sa_column=Column(Integer, ForeignKey("generated_resources.id", ondelete="CASCADE"), index=True))
    resource_item_id: int | None = Field(default=None, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class CoursePathSummary(SQLModel, table=True):
    """路径学习总结表 — 记录路径完成后的掌握度分析、薄弱点回顾和后续建议。"""
    __tablename__ = "course_path_summaries"
    __table_args__ = (
        Index("ix_course_path_summaries_user_path", "user_id", "path_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(index=True, foreign_key="course_paths.id")
    user_id: int = Field(index=True)

    summary_markdown: str | None = Field(default=None, sa_column=Column(Text))
    mastery_scores: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    weak_points: list[dict] | None = Field(default=None, sa_column=Column(JSONB))
    next_suggestions: list[dict] | None = Field(default=None, sa_column=Column(JSONB))

    status: str = Field(default="pending", max_length=20, index=True)  # pending, generating, completed, failed
    error_message: str | None = Field(default=None, sa_column=Column(Text))

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
    ChatMessage,
    ChatSessionSummary,
    UserLongTermMemory,
    UserProfile,
    UserProfileHistory,
    GeneratedResource,
    GeneratedResourceItem,
    QuizQuestion,
    LearningEvent,
    LearningSession,
    CoursePathGenerationTask,
    CoursePath,
    CoursePathNode,
    CoursePathResourceBinding,
    CoursePathSummary,
    User,
    School,
)


def import_all_models() -> tuple[type, ...]:
    """返回已注册的模型类元组，同时确保所有模型类被导入以触发 SQLModel 元数据注册。
    init_db() 调用此函数后再执行 create_all，才能正确建表。"""
    logger.debug("[Models] 已注册 %d 个模型: %s",
                 len(REGISTERED_MODELS),
                 [m.__name__ for m in REGISTERED_MODELS])
    return REGISTERED_MODELS
