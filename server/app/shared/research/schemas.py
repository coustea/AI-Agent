"""ResearchAgent 数据模型定义。"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# 搜索任务定义
# ============================================================================

ResearchSource = Literal["web", "knowledge_base"]
ResearchDepth = Literal["quick", "standard", "deep"]


class ResearchTask(BaseModel):
    """搜索任务定义。"""

    query: str = Field(min_length=1, description="搜索查询")
    objective: str = Field(default="", description="搜索目标")
    sources: set[ResearchSource] = Field(
        default_factory=lambda: {"web", "knowledge_base"},
        description="搜索来源: 'web' 联网搜索, 'knowledge_base' 本地知识库"
    )
    depth: ResearchDepth = Field(default="standard", description="搜索深度")
    context: str = Field(
        default="",
        description="额外上下文，如课程名称提示（用于知识库检索聚焦）"
    )

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
    """搜索来源项（同时支持联网搜索和知识库检索）。"""

    source: str = Field(default="", description="来源名称（web 工具名 / 'knowledge_base'）")
    title: str = Field(default="", description="标题")
    url: str = Field(default="", description="链接")
    summary: str = Field(default="", description="摘要")
    published_at: str | None = Field(default=None, description="发布时间")

    # 知识库专有字段（web 来源时为空）
    chunk_id: str = Field(default="", description="知识库片段 ID")
    section: str = Field(default="", description="章节")
    course: str = Field(default="", description="课程名称")
    heading_path: str = Field(default="", description="章节路径")
    page: int | None = Field(default=None, description="页码")
    score: float | None = Field(default=None, description="相关性分数")
    retrieval_type: str = Field(default="", description="检索类型: vector/bm25/hybrid")


class ResearchError(BaseModel):
    """错误记录。"""

    stage: str = Field(description="错误阶段")
    code: str = Field(description="错误代码")
    message: str = Field(description="错误消息")
    recoverable: bool = Field(default=True, description="是否可恢复")


class ResearchReport(BaseModel):
    """搜索结果报告。"""

    query: str = Field(description="原始查询")
    sources: list[ResearchSourceItem] = Field(default_factory=list, description="联网搜索结果列表")
    knowledge_chunks: list[Any] = Field(
        default_factory=list,
        description="知识库检索结果（RetrievedChunk 列表，延迟导入避免循环引用）",
    )
    errors: list[ResearchError] = Field(default_factory=list, description="错误记录")

    @property
    def has_results(self) -> bool:
        """是否有有效搜索结果（联网或知识库）。"""
        return len(self.sources) > 0 or len(self.knowledge_chunks) > 0


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
