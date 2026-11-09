"""
统一 SQLModel 表定义。

所有数据库表集中在此文件中定义，按功能域分组：
  - User       用户基础信息、长期记忆与自适应策略
  - Auth/School 学校库
  - Chat       会话与消息（会话内置滚动摘要）
  - Resource   生成资源记录（单表内联步骤与产物）
  - Path       学习路径（节点内联主教程与测验题目、辅助资源）
  - Quiz       题库、答题流水与错题本
  - Evaluation 学习行为事件、停留会话与周期评估报告

所有表统一使用 UtcDateTime 存储 UTC 时间，适配 MySQL/aiomysql。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlmodel import SQLModel, Field

from app.infra.types import UtcDateTime
from app.infra.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# User — 用户基础信息、画像策略与长期记忆（合并 UserProfile 与 ChatLongTermMemory）
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    """用户核心表，承载基础资料、学情画像偏好、长期记忆与自适应导学策略。"""
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
    # onboarding 是否已完成（True=已完成，False=未完成需引导）
    onboarding_completed: bool = Field(default=False)

    # ── 基础信息（由 onboarding 与个人中心维护）──
    school: str | None = Field(default=None, max_length=200)
    school_level: str | None = Field(default=None, max_length=50)
    major: str | None = Field(default=None, max_length=200)
    grade: str | None = Field(default=None, max_length=50)
    daily_study_time: str | None = Field(default=None, max_length=50)
    global_learning_goal: str | None = Field(default=None, sa_column=Column(Text))
    programming_languages: list[str] | None = Field(default=None, sa_column=Column(JSON))
    courses: list[str] | None = Field(default=None, sa_column=Column(JSON))

    # ── 学习偏好与基线字段 ──
    # 基础水平：beginner/entry/proficient/master
    foundational_level: str | None = Field(default=None, max_length=20)
    # 学习风格：theory_first/practice_first/case_driven
    learning_style: str | None = Field(default=None, max_length=20)
    # 内容深度：quick_overview/systematic_deep
    content_depth: str | None = Field(default=None, max_length=20)
    # 薄弱知识点列表
    weak_points: list[str] | None = Field(default=None, sa_column=Column(JSON))

    # ── 跨会话长期记忆（权威单文本来源）──
    long_term_memory: str = Field(default="", sa_column=Column(Text, server_default=""))

    # ── 自适应导学策略与评估触发水位 ──
    guidance_strategy: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    guidance_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(UtcDateTime(), nullable=True),
    )
    profile_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(UtcDateTime(), nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


class School(SQLModel, table=True):
    """学校基础数据表。"""
    __tablename__ = "schools"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    level: str | None = Field(default=None, max_length=50)
    tier: str | None = Field(default=None, max_length=20)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )


# ---------------------------------------------------------------------------
# Chat — 会话与消息（会话内置滚动压缩摘要）
# ---------------------------------------------------------------------------

class ChatSession(SQLModel, table=True):
    """会话表，持有滚动压缩摘要、Token 计数与长期记忆水位。"""
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index(
            "ix_chat_sessions_user_archived_updated",
            "user_id",
            "is_archived",
            "updated_at",
        ),
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    user_id: int = Field(index=True)
    title: str = Field(default="新对话", max_length=100)
    is_archived: bool = Field(default=False)

    # 滚动压缩摘要及水位
    summary_markdown: str = Field(default="", sa_column=Column(Text, server_default=""))
    last_summarized_message_id: int = Field(default=0)
    summary_token_count: int = Field(default=0)

    # 长期记忆触发水位
    ltm_token_count: int = Field(default=0)
    ltm_message_count: int = Field(default=0)
    last_ltm_message_id: int | None = Field(default=None)
    last_ltm_updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(UtcDateTime(), nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


class ChatMessage(SQLModel, table=True):
    """模型可见消息链，assistant/tool 消息通过 run_id 归属同一次运行。"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_id_id", "session_id", "id"),
        Index("ix_chat_messages_run_id_id", "run_id", "id"),
        CheckConstraint(
            "role IN ('user', 'assistant', 'tool', 'system')",
            name="ck_chat_messages_role",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            index=True,
        ),
    )
    run_id: str | None = Field(
        default=None,
        sa_column=Column(
            String(36),
            ForeignKey("chat_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    role: str  # "user" | "assistant" | "tool" | "system"
    content: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    tool_call_id: str | None = Field(default=None, max_length=120, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), index=True),
    )


class ChatRun(SQLModel, table=True):
    """一次对话运行快照（阶段、时间线步骤、产物与引用来源）。"""
    __tablename__ = "chat_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')",
            name="ck_chat_runs_status",
        ),
    )

    id: str = Field(sa_column=Column(String(36), primary_key=True))
    session_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            index=True,
        ),
    )
    user_id: int = Field(index=True)
    user_message_id: int = Field(index=True)
    status: str = Field(default="queued", max_length=16)
    phase: str = Field(default="queued", max_length=32)
    phase_label: str = Field(default="等待处理", max_length=200)
    content: str = Field(default="", sa_column=Column(Text))
    error: str = Field(default="", sa_column=Column(Text))
    total_elapsed_ms: int = Field(default=0)
    steps: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    artifacts: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    sources: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(UtcDateTime(), nullable=True),
    )


# ---------------------------------------------------------------------------
# Resource — 生成资源记录（单表内联步骤与全部产物，对齐 ChatRun）
# ---------------------------------------------------------------------------

class GeneratedResource(SQLModel, table=True):
    """生成资源主表，包含运行状态、思考步骤与全部产物明细。"""
    __tablename__ = "generated_resources"
    __table_args__ = (
        Index("ix_generated_resources_user_created", "user_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(max_length=64, index=True)
    user_id: int = Field(index=True)
    topic: str = Field(sa_column=Column(String(255), nullable=False))
    status: str = Field(default="pending", max_length=50)
    summary: str = Field(default="", sa_column=Column(Text, server_default=""))

    request_snapshot_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    steps: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    artifacts: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


# ---------------------------------------------------------------------------
# Learning Path — 学习路径与节点（节点内联主教程）
# ---------------------------------------------------------------------------

class LearningPath(SQLModel, table=True):
    """学习路径主表。"""
    __tablename__ = "learning_paths"
    __table_args__ = (
        Index("ix_learning_paths_user_module_status", "user_id", "module", "status"),
        Index("ix_learning_paths_user_module_updated", "user_id", "module", "updated_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)
    title: str = Field(max_length=200)
    goal: str = Field(sa_column=Column(Text))
    topic: str | None = Field(default=None, sa_column=Column(Text))
    current_knowledge: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    preferences: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    overall_progress: int = Field(default=0, ge=0, le=100)
    current_node_key: str | None = Field(default=None, max_length=80, index=True)
    status: str = Field(default="active", max_length=30, index=True)

    stages_json: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


class PathNode(SQLModel, table=True):
    """学习路径节点表，直接内联节点主教程。"""
    __tablename__ = "path_nodes"
    __table_args__ = (
        Index("ix_path_nodes_path_stage", "path_id", "stage_id"),
        Index("ix_path_nodes_user_status", "user_id", "status"),
        Index("ix_path_nodes_path_priority", "path_id", "priority"),
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

    prerequisites: list[str] | None = Field(default=None, sa_column=Column(JSON))
    difficulty: str | None = Field(default=None, max_length=30)

    # ── 节点内联主教程 ──
    tutorial_title: str | None = Field(default=None, max_length=200)
    tutorial_summary: str | None = Field(default=None, sa_column=Column(Text))
    tutorial_markdown: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSON))
    weak_knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSON))
    tutorial_generated_at: datetime | None = Field(
        default=None,
        sa_column=Column(UtcDateTime(), nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )
    started_at: datetime | None = Field(default=None, sa_column=Column(UtcDateTime(), nullable=True))
    completed_at: datetime | None = Field(default=None, sa_column=Column(UtcDateTime(), nullable=True))


class PathNodeQuestion(SQLModel, table=True):
    """节点测验题目与用户作答快照表。"""
    __tablename__ = "path_node_questions"
    __table_args__ = (
        Index("ix_path_node_questions_node_round", "node_id", "round_no"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True))
    node_id: int = Field(sa_column=Column(Integer, ForeignKey("path_nodes.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)

    round_no: int = Field(default=1, ge=1)
    question_no: int = Field(default=1, ge=1, le=5)
    mode: str = Field(default="quiz", max_length=32)
    type: str = Field(default="single_choice", max_length=32)

    question: str = Field(sa_column=Column(Text))
    choice: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    answer: str = Field(sa_column=Column(Text))
    response: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSON))
    is_correct: bool | None = Field(default=None, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )
    submitted_at: datetime | None = Field(default=None, sa_column=Column(UtcDateTime(), nullable=True))


class PathNodeResource(SQLModel, table=True):
    """节点辅助资源表（思维导图、示例代码、拓展阅读、课件 PPT、动画视频等）。"""
    __tablename__ = "path_node_resources"
    __table_args__ = (
        Index("ix_path_node_resources_node_type", "node_id", "resource_type"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(sa_column=Column(Integer, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True))
    node_id: int = Field(sa_column=Column(Integer, ForeignKey("path_nodes.id", ondelete="CASCADE"), index=True))
    user_id: int = Field(index=True)

    resource_type: str = Field(max_length=32, index=True)
    version_no: int = Field(default=1, ge=1)
    title: str = Field(max_length=200)
    content_format: str = Field(default="markdown", max_length=32)
    content_text: str | None = Field(default=None, sa_column=Column(Text))
    content_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="completed", max_length=32)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    input_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


# ---------------------------------------------------------------------------
# Quiz Bank & Wrong Question — 题库题目、答题流水与错题本
# ---------------------------------------------------------------------------

class QuizQuestion(SQLModel, table=True):
    """题库题目表，存储标准 408 及学科题库记录。"""
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("question_id", name="uq_quiz_questions_question_id"),
        Index("ix_quiz_questions_subject_type", "subject", "question_type"),
        Index("ix_quiz_questions_difficulty", "difficulty"),
    )

    id: int | None = Field(default=None, primary_key=True)
    question_id: str = Field(max_length=255, index=True)
    source: str | None = Field(default=None, max_length=255, index=True)
    subject: str = Field(max_length=255, index=True)
    question_type: str = Field(max_length=100, index=True)
    difficulty: str | None = Field(default=None, max_length=100, index=True)
    content: str = Field(sa_column=Column(Text))
    options_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    answer: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSON))
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    language: str | None = Field(default=None, max_length=32, index=True)
    split: str | None = Field(default=None, max_length=64, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


class QuizAnswerHistory(SQLModel, table=True):
    """答题流水表，记录每次答题提交结果。"""
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
        sa_column=Column(UtcDateTime()),
    )


class WrongQuestion(SQLModel, table=True):
    """错题本表，按用户与题目去重记录错题快照。"""
    __tablename__ = "wrong_questions"
    __table_args__ = (
        Index("ix_wrong_questions_user_question", "user_id", "question_id", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    question_id: str = Field(max_length=255, index=True)

    subject: str = Field(max_length=255)
    question_type: str = Field(max_length=100)
    content: str = Field(sa_column=Column(Text))
    options_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    standard_answer: str | None = Field(default=None, sa_column=Column(Text))
    analysis: str | None = Field(default=None, sa_column=Column(Text))

    user_answer: str | None = Field(default=None, sa_column=Column(Text))
    wrong_count: int = Field(default=1)

    note: str | None = Field(default=None, sa_column=Column(Text))
    is_archived: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


# ---------------------------------------------------------------------------
# Evaluation – 学习行为事件、会话时长与评估报告
# ---------------------------------------------------------------------------

class LearningEvent(SQLModel, table=True):
    """统一学习行为事件流水表，承载所有功能域行为埋点与每日登录活跃。"""
    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_learning_events_user_module", "user_id", "module"),
        Index("ix_learning_events_user_module_created", "user_id", "module", "created_at"),
        Index("ix_learning_events_module_entity", "module", "entity_id"),
        Index("ix_learning_events_user_client_event", "user_id", "client_event_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(max_length=50, description="模块: auth/chat/resource/path/quiz")
    entity_id: str | None = Field(default=None, max_length=255, description="模块内实体 ID")
    event_type: str = Field(max_length=50, description="模块内事件子类型")
    score: float | None = Field(default=None, description="得分 0–100")
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    event_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("event_metadata", JSON))
    client_event_id: str | None = Field(default=None, max_length=64)
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), index=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), index=True),
    )


class LearningSession(SQLModel, table=True):
    """学习会话表，记录用户在各页面的实际活跃学习时长。"""
    __tablename__ = "learning_sessions"
    __table_args__ = (
        Index("ix_learning_sessions_user_started_at", "user_id", "started_at"),
        Index("ix_learning_sessions_user_source_page", "user_id", "source_page"),
        Index("ix_learning_sessions_user_client_session", "user_id", "client_session_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    source_page: str = Field(max_length=50, index=True, description="来源页面标识")
    module: str | None = Field(default=None, max_length=50, description="所属模块")
    entity_id: str | None = Field(default=None, max_length=100, description="多态业务主实体 ID")
    sub_entity_id: str | None = Field(default=None, max_length=100, description="多态业务子实体 ID")
    started_at: datetime = Field(sa_column=Column(UtcDateTime(), index=True))
    ended_at: datetime = Field(sa_column=Column(UtcDateTime()))
    duration_seconds: int = Field(ge=1, le=14400, description="实际活跃时长(秒)")
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    client_session_id: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )


class LearningAssessment(SQLModel, table=True):
    """周期性学情评估报告表。"""
    __tablename__ = "learning_assessments"
    __table_args__ = (
        Index("ix_assessments_user_created", "user_id", "created_at"),
        Index("ix_assessments_user_status", "user_id", "status"),
        CheckConstraint("status IN ('generating', 'ready', 'failed')", name="chk_assessments_status"),
        CheckConstraint("window_end > window_start", name="chk_assessments_window_order"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    trigger_source: str = Field(max_length=20, description="触发来源: profile_update / manual")
    range_days: int = Field()
    window_start: datetime = Field(sa_column=Column(UtcDateTime()))
    window_end: datetime = Field(sa_column=Column(UtcDateTime()))
    status: str = Field(max_length=16, default="generating")
    assessment: str | None = Field(default=None, sa_column=Column(Text, nullable=True), description="LLM 生成的学习评估文案")
    generated_at: datetime | None = Field(
        default=None,
        sa_column=Column(UtcDateTime(), nullable=True),
    )
    failure_code: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(UtcDateTime(), onupdate=func.now()),
    )


# ---------------------------------------------------------------------------
# Model registration — init_db() 注册表元组（精简为 15 张核心表）
# ---------------------------------------------------------------------------

REGISTERED_MODELS = (
    User,
    School,
    ChatSession,
    ChatMessage,
    ChatRun,
    GeneratedResource,
    LearningPath,
    PathNode,
    PathNodeQuestion,
    PathNodeResource,
    QuizQuestion,
    QuizAnswerHistory,
    WrongQuestion,
    LearningEvent,
    LearningSession,
    LearningAssessment,
)
