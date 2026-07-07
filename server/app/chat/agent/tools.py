"""TutorAgent 工具构建 — 收集各工具模块的 Tool 对象。

职责：
  - 导入各工具模块的 as_tool() 函数
  - 组装为统一的 Tool 列表
  - 定义工具名称到证据类型的映射
  - 新增 generate_teaching_diagram 工具（图解生成）
  - 新增 research 工具（调用 ResearchAgent 子 Agent 进行网页研究）

Chat 保留本地课程知识库工具；普通网页搜索与抓取统一委托给
app/shared/research/ResearchAgent。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from app.rag.tools import build_knowledge_tool
from app.chat.tools.user_context import as_tool as _user_context_tools
from app.chat.schemas import EvidenceSet, TutorRequestContext
from app.chat.schemas.diagram import TeachingDiagramGenerator
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


class GenerateDiagramArgs(BaseModel):
    """教学图解生成参数。"""
    question: str = Field(description="学生原始问题（必须完整复述，用于确定图解主题）")
    answer_summary: str = Field(description="回答中与图解主题直接相关的核心内容摘要，用于提取图解核心内容")


def _result_handler(handler, tool_name: str):
    """包装工具处理器，保留原始结果结构。"""
    async def _wrapped(**kwargs: Any) -> Any:
        try:
            return await handler(**kwargs)
        except Exception as exc:
            logger.warning("[%s] failed: error=%s", tool_name, exc)
            raise
    return _wrapped


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
        # 教学图解生成
        Tool(
            "generate_teaching_diagram",
            "Generate a teaching diagram (JSON format) for complex processes, architectures, or protocols. "
            "Use when the question involves visualizable concepts that benefit from a diagram. "
            "The diagram MUST be strictly about the student's question topic — never generate diagrams on unrelated subjects.",
            GenerateDiagramArgs,
            _result_handler(_generate_diagram_handler(request), "generate_teaching_diagram"),
        ),
    ]


def _generate_diagram_handler(request: TutorRequestContext) -> Any:
    """创建图解生成处理器（闭包捕获 request 上下文）。"""
    async def _handler(question: str, answer_summary: str) -> dict[str, Any]:
        try:
            generator = TeachingDiagramGenerator()
            # 构造空的 EvidenceSet（图解生成器需要）
            evidence_set = EvidenceSet(items=[])
            result = await generator.generate(request, answer_summary, evidence_set)
            return result or {"error": "图解生成失败"}
        except Exception as exc:
            logger.warning("[generate_teaching_diagram] failed: %s", exc)
            return {"error": str(exc)}
    return _handler
