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

from sqlalchemy import ARRAY, Integer, Text, Column, Index, UniqueConstraint
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
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
    created_at: datetime = Field(default_factory=datetime.now)

# ---------------------------------------------------------------------------
# Chat — 会话与消息
# ---------------------------------------------------------------------------

class ChatSession(SQLModel, table=True):
    """会话表 — 管理多会话隔离，每个用户可以有多个独立会话"""
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)  # UUID 字符串主键
    user_id: int = Field(index=True)
    module: str = Field(index=True)  # 所属功能模块（如 "mentor"）
    title: str = Field(default="新对话", max_length=100)  # 会话标题（取首条消息前 20 字符）
    is_archived: bool = Field(default=False)  # 软删除标记

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    # 会话概要触发计数器
    summary_token_count: int = Field(default=0)  # 累计 token 数，达到阈值触发会话概要生成


class ChatMessage(SQLModel, table=True):
    """聊天消息表 — 保存用户与助手的原始聊天记录"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_session_module_created_at", "user_id", "session_id", "module", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)  # 关联 ChatSession
    module: str = Field(default="mentor", index=True)
    role: str  # 消息角色："user" | "assistant" | "system" | "tool"
    content: str = Field(sa_column=Column(Text))  # 消息正文，使用 Text 类型支持长文本
    attachments: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 附件信息
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))  # 工具调用记录
    diagram: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 图解数据（Mermaid 源码等）
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
    session_id: str = Field(index=True)  # 关联 ChatSession
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    summary_markdown: str = Field(sa_column=Column(Text))  # 概要主体 Markdown
    summary_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 结构化概要

    summary_type: str = Field(default="incremental", max_length=50)  # 概要类型：incremental | full
    version: int = Field(default=1)  # 概要版本号

    start_message_id: int | None = Field(default=None)  # 起始消息 ID
    end_message_id: int | None = Field(default=None)  # 结束消息 ID
    summarized_message_count: int = Field(default=0)  # 已压缩消息数量

    current_topic: str | None = Field(default=None, max_length=200)  # 当前话题
    current_goal: str | None = Field(default=None, max_length=200)  # 当前目标
    current_status: str | None = Field(default=None, sa_column=Column(Text))  # 当前状态
    next_action: str | None = Field(default=None, sa_column=Column(Text))  # 下一步行动

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


# ---------------------------------------------------------------------------
# Memory — 长期记忆（用户级单条）
# ---------------------------------------------------------------------------

class UserLongTermMemory(SQLModel, table=True):
    """用户长期记忆表 — 一个用户在一个 module 下只有一条长期记忆
    
    设计原则：
    - 只保存长期稳定、未来可复用的信息
    - 不保存当前会话临时状态、一次性作业中间状态
    - 同时保存 Markdown 和 JSONB 格式
    """
    __tablename__ = "user_long_term_memories"
    __table_args__ = (
        UniqueConstraint("user_id", "module", name="uq_user_long_term_memory_user_module"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    memory_markdown: str = Field(sa_column=Column(Text))  # 记忆主体 Markdown
    memory_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 结构化记忆

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
        sa_column=Column(TIMESTAMP(timezone=True))
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
    )

    id: int | None = Field(default=None, primary_key=True)  # 改为 id 主键
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    profile_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 文字画像 JSON
    profile_score_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 分数画像 JSON

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
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class UserProfileHistory(SQLModel, table=True):
    """用户画像历史表 — 保存每次画像变更的快照"""
    __tablename__ = "user_profile_history"
    __table_args__ = (
        Index("ix_user_profile_history_user_module_version", "user_id", "module", "version"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)  # 所属功能模块

    version: int = Field(index=True)  # 版本号，每次更新递增

    profile_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 文字画像快照 JSON
    profile_score_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))  # 分数画像快照 JSON

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
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class GeneratedResourceItem(SQLModel, table=True):
    """资源项明细表 — 每个 agent 生成一个资源项。"""
    __tablename__ = "generated_resource_items"
    __table_args__ = (
        Index("ix_generated_resource_items_resource_agent", "resource_id", "agent_type"),
        Index("ix_generated_resource_items_user_created_at", "user_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    resource_id: int = Field(index=True, foreign_key="generated_resources.id")
    user_id: int = Field(index=True)

    # Agent 类型（content/mindmap/diagram/quiz/code/reading）
    agent_type: str = Field(max_length=50, index=True)

    # 内容格式（markdown/json/mermaid）
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
        sa_column=Column(TIMESTAMP(timezone=True))
    )


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
    resource_item_id: int | None = Field(default=None, index=True)
    path_id: int | None = Field(default=None, index=True)
    path_node_id: int | None = Field(default=None, index=True)
    node_id: str | None = Field(default=None, max_length=50, index=True)
    event_type: str = Field(max_length=50, index=True)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    score: float | None = Field(default=None)
    duration_seconds: int | None = Field(default=None)
    feedback: str | None = Field(default=None, sa_column=Column(Text))
    metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), index=True)
    )


# ---------------------------------------------------------------------------
# Path — 学习路径规划
# ---------------------------------------------------------------------------

class LearningPath(SQLModel, table=True):
    """学习路径表 — 保存用户的个性化学习路径规划。

    一个用户在一个 module 下可以拥有多条学习路径。
    """
    __tablename__ = "learning_paths"
    __table_args__ = (
        Index("ix_learning_paths_user_module_active", "user_id", "module", "is_active"),
        Index("ix_learning_paths_user_source_resource", "user_id", "source_resource_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    module: str = Field(default="mentor", index=True)

    # 路径配置
    path_key: str | None = Field(default=None, max_length=100, index=True)
    title: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200, index=True)
    source_resource_id: int | None = Field(default=None, index=True)
    learning_goal: str | None = Field(default=None, sa_column=Column(Text))
    knowledge_level: str | None = Field(default=None, max_length=100)

    # 进度信息
    overall_progress: int = Field(default=0, ge=0, le=100)
    current_stage_id: str | None = Field(default=None, max_length=50)
    current_node_id: str | None = Field(default=None, max_length=50)

    # 预估信息
    eta_days: int = Field(default=14, ge=1)
    confidence: int = Field(default=60, ge=0, le=100)

    # 画像快照（生成路径时的画像状态）
    profile_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # 版本与状态
    version: int = Field(default=1)
    status: str = Field(default="active", max_length=30, index=True)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class LearningPathNode(SQLModel, table=True):
    """学习路径节点表 — 保存路径中每个节点的状态。

    记录节点的进度、优先级、完成时间等信息。
    """
    __tablename__ = "learning_path_nodes"
    __table_args__ = (
        Index("ix_learning_path_nodes_path_stage", "path_id", "stage_id"),
        Index("ix_learning_path_nodes_user_status", "user_id", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(index=True, foreign_key="learning_paths.id")
    user_id: int = Field(index=True)

    # 节点标识
    node_id: str = Field(max_length=50, index=True)  # content, mindmap, quiz, etc.
    stage_id: str = Field(max_length=50)  # foundation, enhancement, application
    title: str = Field(max_length=200)

    # 节点状态
    status: str = Field(default="wait", max_length=20)  # wait, processing, success
    progress: int = Field(default=0, ge=0, le=100)
    priority: int = Field(default=50, ge=0, le=100)

    # 推荐原因（基于画像维度的推荐理由）
    recommendation_reason: str | None = Field(default=None, sa_column=Column(Text))

    # 完成信息
    started_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))

    # 关联资源
    resource_id: int | None = Field(default=None, index=True)
    resource_item_id: int | None = Field(default=None, index=True)
    knowledge_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    weak_points: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
    )


class LearningPathAdjustment(SQLModel, table=True):
    """学习路径调整记录表 — 记录路径的每次调整。

    用于追踪路径变化历史和分析调整效果。
    """
    __tablename__ = "learning_path_adjustments"
    __table_args__ = (
        Index("ix_learning_path_adjustments_path_created", "path_id", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    path_id: int = Field(index=True, foreign_key="learning_paths.id")
    user_id: int = Field(index=True)

    # 调整信息
    adjustment_type: str = Field(max_length=50)  # feedback, progress, profile_update, manual
    reason: str = Field(sa_column=Column(Text))

    # 影响的节点
    impacted_node_ids: list[str] | None = Field(default=None, sa_column=Column(JSONB))

    # 调整前的状态快照
    before_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # 调整后的状态快照
    after_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True))
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
    LearningEvent,
    LearningPath,
    LearningPathNode,
    LearningPathAdjustment,
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
