"""响应模型 — 供前端使用的资源项和资源包 DTO。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from uuid import uuid4

from app.resource.schemas.request import ResourceAgentId


class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。

    content 为 None 时表示轻量摘要（不含正文），用于状态轮询等轻量场景。
    format 由 agent_type 推导，不再从数据库存储字段读取。
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceAgentId
    title: str
    format: str
    content: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ResourceStatusSnapshot(BaseModel):
    """SSE/轮询状态接口返回的轻量任务快照。"""
    resource_id: int
    learning_need: str = ""
    status: str
    selected_agents: list[str] = Field(default_factory=list)
    agent_snapshots: dict[str, dict[str, Any]] = Field(default_factory=dict)
    current_message: str = ""
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    updated_at: str | None = None


class ResourceBundle(BaseModel):
    """资源生成完成后的资源包。"""
    id: str
    title: str = "个性化学习资源包"
    learning_need: str
    selected_agents: list[str] = Field(default_factory=list)
    plan_content: str | None = None
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class SingleResourceRequest(BaseModel):
    """单智能体资源生成请求（路径规划 / 即调即用）。

    PPT/Cartoon 是聚合 Agent，在多智能体模式下依赖上游素材；
    但在单智能体模式下可直接调用，走路径规划的 generate_node 逻辑，
    只需要传入知识点和教程即可生成，保存到 paths/ 路径下。
    """
    model_config = ConfigDict(extra="forbid")

    agent_id: ResourceAgentId
    learning_need: str

    # ── PPT/Cartoon 单独调用所需字段 ──────────────────────────────────
    knowledge_points: list[str] = Field(
        default_factory=list,
        description="知识点列表 — PPT/Cartoon 单独调用时必填",
    )
    tutorial_markdown: str = Field(
        default="",
        description="教程 Markdown 内容 — PPT/Cartoon 单独调用时必填",
    )
    tutorial_title: str = Field(
        default="",
        description="教程标题 — PPT/Cartoon 单独调用时选填，默认取 learning_need",
    )

    @field_validator("learning_need")
    @classmethod
    def validate_learning_need(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("学习需求不能为空")
        return value

    @field_validator("agent_id")
    @classmethod
    def validate_aggregation_agent(cls, value: ResourceAgentId) -> ResourceAgentId:
        """PPT/Cartoon 单独调用时必须提供知识点和教程；Video 仍不支持单独调用。"""
        # 视频 Agent 不允许单独调用
        if value == ResourceAgentId.VIDEO:
            raise ValueError("Video Agent 不支持单独调用")
        return value

    @model_validator(mode="after")
    def validate_path_node_fields(self) -> "SingleResourceRequest":
        """PPT/Cartoon 单独调用时，knowledge_points 和 tutorial_markdown 必填。"""
        # 聚合 Agent 单独调用必须携带知识点与教程内容
        if self.agent_id in {ResourceAgentId.PPT, ResourceAgentId.CARTOON}:
            if not self.knowledge_points:
                raise ValueError("PPT/Cartoon 单独调用时必须提供 knowledge_points")
            if not self.tutorial_markdown.strip():
                raise ValueError("PPT/Cartoon 单独调用时必须提供 tutorial_markdown")
        return self
