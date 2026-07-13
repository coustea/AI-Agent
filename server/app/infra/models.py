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
- Profile 独立为共享模块
"""

# 本文件集中定义所有 SQLModel 数据库表，新表需加入底部 REGISTERED_MODELS 元组以便自动建表
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ForeignKey, Integer, Text, Column, Index, UniqueConstraint, CheckConstraint, func, text
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

    # ── 基础信息（原 profile_json.base_info，由 onboarding 填写）──
    school: str | None = Field(default=None, max_length=200)
    school_level: str | None = Field(default=None, max_length=50)
    major: str | None = Field(default=None, max_length=200)
    grade: str | None = Field(default=None, max_length=50)
    daily_study_time: str | None = Field(default=None, max_length=50)
    global_learning_goal: str | None = Field(default=None, sa_column=Column(Text))
    programming_languages: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    courses: list[str] | None = Field(default=None, sa_column=Column(JSONB))

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
            "ix_chat_sessions_user_archived_updated",
            "user_id",
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
    ltm_token_count: int = Field(default=0)
    ltm_message_count: int = Field(default=0)
    last_ltm_message_id: int | None = Field(default=None)
    last_ltm_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )


class ChatMessage(SQLModel, table=True):
    """模型可见消息；本轮派生消息直接关联发起请求的 UserMessage。"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created_at", "session_id", "created_at"),
        Index("ix_chat_messages_session_user_message", "session_id", "user_message_id"),
        CheckConstraint(
            "role IN ('user', 'assistant', 'tool', 'system')",
            name="ck_chat_messages_role",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            index=True,
        ),
    )
    user_message_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )

    role: str  # "user" | "assistant" | "tool" | "system"
    content: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB))
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))
    tool_call_id: str | None = Field(default=None, max_length=120, index=True)
    usage_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(TIMESTAMP(timezone=True), index=True))


class ChatAttachmentAnalysis(SQLModel, table=True):
    """附件分析派生产物，不改写用户原始消息。"""
    __tablename__ = "chat_attachment_analyses"
    __table_args__ = (
        Index("ix_chat_attachment_analyses_user_message_created_at", "user_message_id", "created_at"),
        CheckConstraint(
            "analysis_type IN ('image', 'document')",
            name="ck_chat_attachment_analyses_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_chat_attachment_analyses_status",
        ),
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    user_message_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("chat_messages.id", ondelete="CASCADE"),
            index=True,
        ),
    )
    analysis_type: str = Field(max_length=20)
    status: str = Field(default="running", max_length=20)
    content: str = Field(default="", sa_column=Column(Text))
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True)),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )


class ChatActivity(SQLModel, table=True):
    """可公开、可回放的 Agent 生命周期摘要。"""
    __tablename__ = "chat_activities"
    __table_args__ = (
        UniqueConstraint(
            "user_message_id",
            "activity_id",
            name="uq_chat_activities_user_message_activity",
        ),
        Index("ix_chat_activities_user_message_started_at", "user_message_id", "started_at"),
        CheckConstraint(
            "status IN ('running', 'done', 'failed')",
            name="ck_chat_activities_status",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_message_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("chat_messages.id", ondelete="CASCADE"),
            index=True,
        ),
    )
    activity_id: str = Field(max_length=160)
    kind: str = Field(default="workflow", max_length=30)
    stage: str | None = Field(default=None, max_length=80)
    status: str = Field(default="running", max_length=20)
    title: str = Field(default="", max_length=255)
    summary: str = Field(default="", sa_column=Column(Text))
    message: str = Field(default="", sa_column=Column(Text))
    detail: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True)),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
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
            "block_index",
            name="uq_chat_session_summary_blocks_session_block",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            index=True,
        ),
    )

    block_index: int = Field(default=1, index=True)
    summary_markdown: str = Field(sa_column=Column(Text))
    start_message_id: int | None = Field(default=None)
    end_message_id: int | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


# ---------------------------------------------------------------------------
# Memory — 长期记忆（用户级单条）
# ---------------------------------------------------------------------------

class ChatLongTermMemory(SQLModel, table=True):
    """Chat 长期记忆表 — 每个用户一条 Markdown 记忆。

    设计原则：
    - 只保存长期稳定、未来可复用的信息
    - 不保存当前会话临时状态、一次性作业中间状态
    - memory_markdown 是唯一权威来源（给 LLM 上下文用）
    """
    __tablename__ = "chat_long_term_memories"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_chat_long_term_memory_user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    memory_markdown: str = Field(sa_column=Column(Text))  # 记忆主体 Markdown（唯一权威来源）

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class UserProfile(SQLModel, table=True):
    """用户主画像表 — 每个用户一条主画像记录。

    维度明细见 UserProfileDimension。
    基础信息（school/major/grade 等）已移至 User 表。
    """
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    # 评分汇总（原 profile_score_json 顶层字段）
    overall_score: int = Field(default=0)
    scored_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )

    guidance_strategy: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    guidance_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    last_assessment_report_id: int | None = Field(
        default=None,
        foreign_key="learning_assessment_reports.id"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class UserProfileDimension(SQLModel, table=True):
    """用户画像维度明细表 — 原 profile_json.dimensions 与
    profile_score_json.dimension_scores / dimension_evidence 的关系化存储。

    每个 (user_id, dimension_key) 唯一，例如 dimension_key 可取
    'knowledge_level' / 'learning_style' 等画像维度。
    """
    __tablename__ = "user_profile_dimensions"
    __table_args__ = (
        UniqueConstraint("user_id", "dimension_key", name="uq_user_profile_dimensions_user_key"),
        Index("ix_user_profile_dimensions_user_id", "user_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field()
    dimension_key: str = Field(max_length=50, index=True)

    # 维度正文描述（原 dimensions[*].value）
    value: str = Field(sa_column=Column(Text))
    # 支撑证据列表（原 dimensions[*].evidence / dimension_evidence[*]）
    evidence: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    # 维度得分 0-100（原 dimension_scores[*]）
    score: int | None = Field(default=None, ge=0, le=100)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class LearningAssessmentReport(SQLModel, table=True):
    """学习效果评估报告表 — 记录用户单次评估报告。"""
    __tablename__ = "learning_assessment_reports"
    __table_args__ = (
        Index("ix_reports_user_created", "user_id", "created_at"),
        Index("ix_reports_user_status", "user_id", "status"),
        Index(
            "uq_reports_user_generating",
            "user_id",
            postgresql_where=text("status = 'generating'"),
            unique=True,
        ),
        CheckConstraint("range_days IN (7, 14, 30)", name="chk_reports_range_days"),
        CheckConstraint("status IN ('generating', 'ready', 'failed')", name="chk_reports_status"),
        CheckConstraint("window_end > window_start", name="chk_reports_window_order"),
        CheckConstraint(
            "(status = 'ready' AND facts_snapshot IS NOT NULL) OR "
            "(status = 'failed' AND failure_code IS NOT NULL) OR "
            "(status = 'generating')",
            name="chk_reports_state_consistency"
        )
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    range_days: int = Field()
    window_start: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    window_end: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    status: str = Field(max_length=16, default="generating")
    facts_snapshot: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    report_markdown: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    generated_at: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    failure_code: str | None = Field(default=None, max_length=64)
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
    """生成资源主表 — 记录每次多智能体资源生成任务。"""
    __tablename__ = "generated_resources"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    learning_need: str | None = Field(default=None, sa_column=Column(Text))
    # 请求在入队前冻结；后台工作流不得依赖 HTTP 进程内参数。
    request_snapshot_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    plan_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    status: str = Field(default="pending", max_length=50)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now())
    )


class GeneratedResourceItem(SQLModel, table=True):
    """资源项明细表 — 每个 agent 生成一个资源项。

    每个 (resource_id, agent_type) 组合只能有一条成功记录。
    失败 Agent 不创建记录，仅在工作流状态中保留失败信息。
    content_format 由 agent_type 推导，不再单独存储。
    """
    __tablename__ = "generated_resource_items"
    __table_args__ = (
        UniqueConstraint("resource_id", "agent_type", name="uq_generated_resource_items_resource_agent"),
        Index("ix_generated_resource_items_content_json", "content_json", postgresql_using="gin"),
        Index("ix_generated_resource_items_metadata_json", "metadata_json", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(sa_column=Column(Integer, ForeignKey("generated_resources.id", ondelete="CASCADE"), index=True))

    # Agent 类型（content/mindmap/quiz/code/reading/ppt/cartoon）
    agent_type: str = Field(max_length=50, index=True)

    # 展示信息
    title: str | None = Field(default=None, max_length=200)

    # 内容主体（根据 agent_type 选择存储位置）
    content_json: dict[str, Any] | list[Any] | None = Field(default=None, sa_column=Column(JSONB))
    content_text: str | None = Field(default=None, sa_column=Column(Text))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class GeneratedResourceAgentRun(SQLModel, table=True):
    """Agent 运行状态表 — 记录每个 Agent 的生命周期状态。

    每个 (resource_id, agent_id) 组合只有一条记录。
    """
    __tablename__ = "generated_resource_agent_runs"
    __table_args__ = (
        UniqueConstraint("resource_id", "agent_id", name="uq_resource_agent_run"),
        CheckConstraint(
            "status IN ('pending','running','completed','failed','interrupted')",
            name="ck_resource_agent_run_status",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(sa_column=Column(Integer, ForeignKey("generated_resources.id", ondelete="CASCADE"), index=True))
    agent_id: str = Field(max_length=32)
    status: str = Field(default="pending", max_length=16)
    phase: str = Field(default="queued", max_length=64)
    message: str = Field(default="等待调度", sa_column=Column(Text, nullable=False))
    progress: int = Field(default=0)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    elapsed_ms: int | None = Field(default=None)
    started_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    heartbeat_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now()),
    )


class GeneratedResourceRunEvent(SQLModel, table=True):
    """资源任务事件历史。

    事件 ID 是该资源 SSE 的断点序号；数据库是刷新/切页后的唯一事实源，
    进程内订阅仅用于把已提交事件立即推送给当前页面。
    """
    __tablename__ = "generated_resource_run_events"
    __table_args__ = (
        Index("ix_generated_resource_run_events_resource_id_id", "resource_id", "id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(
        sa_column=Column(Integer, ForeignKey("generated_resources.id", ondelete="CASCADE"), index=True)
    )
    agent_id: str | None = Field(default=None, max_length=32)
    event: str = Field(max_length=48)
    status: str | None = Field(default=None, max_length=16)
    phase: str | None = Field(default=None, max_length=64)
    message: str = Field(sa_column=Column(Text, nullable=False))
    progress: int | None = Field(default=None)
    data_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True)),
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
        Index("ix_quiz_questions_difficulty", "difficulty"),
        Index("ix_quiz_questions_tags", "tags", postgresql_using="gin"),
    )

    id: int | None = Field(default=None, primary_key=True)
    question_id: str = Field(max_length=255, index=True)
    source: str | None = Field(default=None, max_length=255, index=True)
    subject: str = Field(max_length=255, index=True)
    question_type: str = Field(max_length=100, index=True)
    difficulty: str | None = Field(default=None, max_length=100, index=True)
    content: str = Field(sa_column=Column(Text))
    options_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    answer: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    language: str | None = Field(default=None, max_length=32, index=True)
    split: str | None = Field(default=None, max_length=64, index=True)

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
    """学习行为事件表 — 单表 unified 结构，module + entity_id 替代 6 个可空 FK 列。"""
    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_learning_events_user_module", "user_id", "module"),
        Index("ix_learning_events_user_module_created", "user_id", "module", "created_at"),
        Index("ix_learning_events_module_entity", "module", "entity_id"),
        Index("ix_learning_events_event_metadata", "event_metadata", postgresql_using="gin"),
        Index(
            "uq_events_user_client_event",
            "user_id",
            "client_event_id",
            postgresql_where=text("client_event_id IS NOT NULL"),
            unique=True,
        )
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(max_length=50, description="模块: chat/resource/path/quiz/visualizer")
    entity_id: str | None = Field(default=None, max_length=255, description="模块内实体 ID（session_id / resource_id / path_node_id / …）")
    event_type: str = Field(max_length=50, description="模块内事件子类型")
    score: float | None = Field(default=None, description="得分 0–100")
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    event_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("event_metadata", JSONB))
    client_event_id: str | None = Field(default=None, max_length=64)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )
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
        Index(
            "uq_sessions_user_client_session",
            "user_id",
            "client_session_id",
            postgresql_where=text("client_session_id IS NOT NULL"),
            unique=True,
        )
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    source_page: str = Field(max_length=50, index=True, description="来源页面标识")
    started_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), index=True))
    ended_at: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True)))
    duration_seconds: int = Field(ge=1, le=14400, description="实际活跃时长(秒)")
    resource_id: int | None = Field(default=None)
    path_id: int | None = Field(default=None)
    path_node_id: int | None = Field(default=None)
    node_id: str | None = Field(default=None, max_length=50)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    client_session_id: str | None = Field(default=None, max_length=64)
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
    difficulty: str | None = Field(default=None, max_length=30)

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
        Index("ix_path_node_resources_input_json", "input_json", postgresql_using="gin"),
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

class QuizAnswerHistory(SQLModel, table=True):
    """答题历史表 — 记录用户每次答题的作答结果。"""
    __tablename__ = "quiz_answer_history"
    __table_args__ = (
        Index("ix_quiz_answer_history_user_question", "user_id", "question_id"),
        Index("ix_quiz_answer_history_user_created", "user_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    question_id: str = Field(max_length=255, index=True)
    subject: str | None = Field(default=None, max_length=255)
    question_type: str | None = Field(default=None, max_length=100)
    user_answer: str | None = Field(default=None, sa_column=Column(Text))
    score: int | None = Field(default=None, ge=0, le=100)
    is_correct: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True)),
    )


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

# 所有需要建表的模型类注册表，init_db() 据此创建或更新表结构
REGISTERED_MODELS = (
    ActiveToken,
    ChatSession,
    ChatMessage,
    ChatAttachmentAnalysis,
    ChatActivity,
    ChatSessionSummaryBlock,
    ChatLongTermMemory,
    UserProfile,
    UserProfileDimension,
    LearningAssessmentReport,
    GeneratedResource,
    GeneratedResourceItem,
    GeneratedResourceAgentRun,
    GeneratedResourceRunEvent,
    QuizQuestion,
    QuizAnswerHistory,
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
