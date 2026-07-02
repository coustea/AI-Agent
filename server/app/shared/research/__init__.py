"""共享研究模块 — 提供统一的搜索能力给所有 Agent 使用。

ResearchAgent 是一个独立的搜索子 Agent，可以被 chat、resource、path 等模块调用。
它只负责搜索和总结，不涉及存储或业务逻辑。
"""

from app.shared.research.agent import ResearchAgent
from app.shared.research.delegate_tool import ResearchToolArgs, build_research_tool
from app.shared.research.schemas import (
    ResearchDepth,
    ResearchError,
    ResearchEvidence,
    ResearchEvent,
    ResearchEventHandler,
    ResearchInvocation,
    ResearchReport,
    ResearchSource,
    ResearchSourceItem,
    ResearchTask,
)

__all__ = [
    "ResearchAgent",
    "ResearchToolArgs",
    "ResearchDepth",
    "ResearchError",
    "ResearchEvidence",
    "ResearchEvent",
    "ResearchEventHandler",
    "ResearchInvocation",
    "ResearchReport",
    "ResearchSource",
    "ResearchSourceItem",
    "ResearchTask",
    "build_research_tool",
]
