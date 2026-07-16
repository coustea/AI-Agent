"""Agent 运行时输入/输出模型。

- AgentResult     — 统一的 Agent 输出结果（成功/失败、内容、元数据）
- ResourceInput   — 多智能体资源生成输入
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.resource.schemas.plan import DownstreamContext, ResourcePlan
from app.resource.schemas.request import LearningScenario


class AgentResult(BaseModel):
    """统一 Agent 输出结果，用于多智能体资源和路径规划节点资源。"""
    # 禁止额外字段，确保结果结构可控
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    content: str = ""
    file_type: str = "markdown"
    title: str = ""
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ResourceInput(BaseModel):
    """多智能体资源生成输入。"""
    model_config = ConfigDict(extra="forbid")

    resource_id: int | None = None
    user_id: int | None = None
    username: str = ""  # 用户名，用于文件路径构建
    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    teaching_plan: ResourcePlan | None = None
    profile: dict[str, Any] = Field(default_factory=dict)  # 学习者画像
    upstream_handoffs: dict[str, DownstreamContext] = Field(default_factory=dict)
