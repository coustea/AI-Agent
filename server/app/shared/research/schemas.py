"""ResearchAgent 数据模型定义。"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# 搜索任务定义
# ============================================================================

ResearchSource = Literal["web"]
ResearchDepth = Literal["quick", "standard", "deep"]


class ResearchTask(BaseModel):
    """搜索任务定义。"""

    query: str = Field(min_length=1, description="搜索查询")
    objective: str = Field(default="", description="搜索目标")
    sources: set[ResearchSource] = Field(
        default_factory=lambda: {"web"},
        description="搜索来源"
    )
    depth: ResearchDepth = Field(default="standard", description="搜索深度")
    context: str = Field(default="", description="额外上下文")

    @model_validator(mode="after")
    def validate_query(self) -> "ResearchTask":
        self.query = self.query.strip()
        if not self.query:
            raise ValueError("ResearchTask.query cannot be blank")
        return self


# ============================================================================
# 搜索结果定义
# ============================================================================

class ResearchSourceItem(BaseModel):
    """搜索来源项。"""

    source: str = Field(default="", description="来源名称")
    title: str = Field(default="", description="标题")
    url: str = Field(default="", description="链接")
    summary: str = Field(default="", description="摘要")
    published_at: str | None = Field(default=None, description="发布时间")


class ResearchError(BaseModel):
    """错误记录。"""

    stage: str = Field(description="错误阶段")
    code: str = Field(description="错误代码")
    message: str = Field(description="错误消息")
    recoverable: bool = Field(default=True, description="是否可恢复")


class ResearchReport(BaseModel):
    """搜索结果报告。"""

    query: str = Field(description="原始查询")
    sources: list[ResearchSourceItem] = Field(default_factory=list, description="搜索结果列表")
    errors: list[ResearchError] = Field(default_factory=list, description="错误记录")

    @property
    def has_results(self) -> bool:
        """是否有有效搜索结果。"""
        return len(self.sources) > 0


# ============================================================================
# 事件定义
# ============================================================================

class ResearchEvent(TypedDict):
    """搜索事件。"""

    activity_id: str
    status: Literal["running", "done", "failed"]
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    error: str | None
    duration_ms: int | None
    action: NotRequired[str]


ResearchEventHandler = Callable[[ResearchEvent], Awaitable[None]]
