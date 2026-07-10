"""把 ResearchAgent 暴露为单一、可复用的业务工具。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from app.infra.tool_excute import Tool
from app.shared.research.agent import ResearchAgent
from app.shared.research.schemas import (
    ResearchDepth,
    ResearchEvent,
    ResearchTask,
)

ResearchEventHandler = Callable[[ResearchEvent], Awaitable[None]]


# ResearchAgent 委托工具的入参模型
class ResearchToolArgs(BaseModel):
    """ResearchAgent 委托参数。"""

    query: str = Field(min_length=1, description="需要检索和核验的问题")
    objective: str = Field(default="", description="本次研究要解决的具体目标")
    depth: ResearchDepth = Field(default="standard", description="研究深度")


# 构建供上层 Agent 注册的 ResearchAgent 委托工具
def build_research_tool(
    *,
    event_handler: ResearchEventHandler | None = None,
    enabled: bool = True,
) -> Tool:
    """构建供上层 Agent 注册的 ResearchAgent 委托工具。"""

    # 委托工具的具体执行逻辑
    async def research(
        query: str,
        objective: str = "",
        depth: ResearchDepth = "standard",
    ) -> dict[str, Any]:
        # 工具未启用时直接返回提示，不再执行搜索
        if not enabled:
            return {
                "text": "当前任务未启用联网研究。",
                "sources": [],
                "query": query,
                "errors": [],
            }

        report = await ResearchAgent(
            event_handler=event_handler,
        ).run(
            ResearchTask(
                query=query,
                objective=objective,
                depth=depth,
                sources={"web"},
            )
        )

        # 将搜索结果拼接为可读文本摘要
        result_text = ""
        if report.sources:
            parts = []
            for s in report.sources:
                entry = s.title
                if s.url:
                    entry += f"\n链接: {s.url}"
                if s.summary:
                    entry += f"\n摘要: {s.summary}"
                parts.append(entry)
            result_text = "\n\n".join(parts)

        # 无有效结果时附带错误摘要，便于上层判断是否重试
        if not result_text:
            error_summary = "；".join(error.message for error in report.errors[:3])
            result_text = "联网研究未获得可用于回答的证据。"
            if error_summary:
                result_text += f" 原因：{error_summary}"

        return {
            "text": result_text,
            "sources": [source.model_dump() for source in report.sources],
            "query": report.query,
            "errors": [error.model_dump() for error in report.errors],
        }

    # 包装为统一的 Tool 对象供 Agent 注册
    return Tool(
        "research",
        "Delegate web search, page research, source verification, and time-sensitive fact checking to ResearchAgent.",
        ResearchToolArgs,
        research,
    )
