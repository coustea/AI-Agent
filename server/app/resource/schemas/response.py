"""响应模型 — 供前端使用的资源项和资源包 DTO。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.resource.schemas.request import ResourceAgentId
from app.resource.status import ResourceLifecycleStatus


class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。

    content 为 None 时表示轻量摘要（不含正文），用于状态轮询等轻量场景。
    format 由 agent_type 推导，不再从数据库存储字段读取。
    """
    id: str  # 总是由 _item_to_dto 显式设置，无默认值
    type: ResourceAgentId
    title: str
    format: Literal["markdown", "json", "html", "mp4"]
    content: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ResourceAgentSnapshot(BaseModel):
    """One persisted Agent state used to restore the running page."""

    agent_id: str
    status: Literal["pending", "running", "completed", "failed", "interrupted"]
    message: str
    progress: int = Field(ge=0, le=100)
    phase: str
    elapsed_ms: int | None = None
    artifact_id: str | None = None
    timestamp: int | None = None


class ResourceStatusSnapshot(BaseModel):
    """SSE/轮询状态接口返回的轻量任务快照。"""
    resource_id: int
    learning_need: str = ""
    status: ResourceLifecycleStatus
    selected_agents: list[ResourceAgentId] = Field(default_factory=list)
    agent_snapshots: dict[str, ResourceAgentSnapshot] = Field(default_factory=dict)
    current_message: str = ""
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    updated_at: str | None = None


class ResourceBundleMetadata(BaseModel):
    """Task-level facts needed by the standalone result page."""

    failed_agents: list[str] = Field(default_factory=list)


class ResourceBundle(BaseModel):
    """资源生成完成后的资源包。"""
    id: str
    title: str = "个性化学习资源包"
    learning_need: str
    selected_agents: list[ResourceAgentId] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    status: ResourceLifecycleStatus = ResourceLifecycleStatus.COMPLETED
    created_at: str  # 总是由 service 显式设置，无默认值
    updated_at: str  # 总是由 service 显式设置，无默认值
    metadata: ResourceBundleMetadata = Field(default_factory=ResourceBundleMetadata)
