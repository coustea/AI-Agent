"""Response and resource-item models served to the frontend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import uuid4

from app.resource.schemas.plan import DownstreamContext
from app.resource.schemas.request import ResourceAgentId
from app.resource.schemas.result import AgentResult


class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceAgentId
    title: str
    format: str
    content: Any
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_context: DownstreamContext | None = None
    execution_report: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ResourceBundle(BaseModel):
    """资源生成完成后的资源包。"""
    id: str
    task_id: str
    topic: str | None = None
    title: str = "个性化学习资源包"
    learning_need: str
    selected_agents: list[str] = Field(default_factory=list)
    resources: list[GeneratedResourceItem] = Field(default_factory=list)
    status: str = "completed"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class SingleResourceRequest(BaseModel):
    """单智能体资源生成请求（路径规划 / 即调即用）。"""
    model_config = ConfigDict(extra="forbid")

    agent_id: ResourceAgentId
    learning_need: str

    @field_validator("learning_need")
    @classmethod
    def validate_learning_need(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("学习需求不能为空")
        return value
