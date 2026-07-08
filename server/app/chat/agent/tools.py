"""TutorAgent 工具构建 — 收集各工具模块的 Tool 对象。

职责：
  - 导入各工具模块的 as_tool() 函数
  - 组装为统一的 Tool 列表
  - 定义工具名称到证据类型的映射
  - 新增 research 工具（调用 ResearchAgent 子 Agent 进行网页研究）

Chat 保留本地课程知识库工具；普通网页搜索与抓取统一委托给
app/shared/research/ResearchAgent。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.rag.tools import build_knowledge_tool
from app.chat.tools.user_context import as_tool as _user_context_tools
from app.chat.schemas import TutorRequestContext
from app.infra.tool_excute import Tool
from app.infra.logging import get_logger
from app.shared.research import (
    ResearchEvent,
    build_research_tool,
)

logger = get_logger(__name__)

TOOL_EVIDENCE_TYPES: dict[str, str] = {
    "get_learner_profile": "learner_profile",
    "get_long_term_memory": "long_term_memory",
    "search_knowledge_base": "knowledge_base",
    "research": "web_search",
}

ResearchEventHandler = Callable[[ResearchEvent], Awaitable[None]]


def build_tutor_tools(
    request: TutorRequestContext,
    *,
    research_event_handler: ResearchEventHandler | None = None,
) -> list[Tool]:
    """装配当前辅导请求可用的业务工具。"""
    return [
        # 用户上下文工具（画像 + 长期记忆）
        *_user_context_tools(request),
        # 本地课程知识库仍属于 Chat。
        build_knowledge_tool(),
        # 普通网页搜索与抓取统一委托给共享 ResearchAgent。
        build_research_tool(
            event_handler=research_event_handler,
            enabled=request.enable_web_search,
        ),
    ]
