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

from pydantic import BaseModel, Field

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

GENERATE_TEACHING_DIAGRAM_TOOL_NAME = "generate_teaching_diagram"


class GenerateTeachingDiagramArgs(BaseModel):
    """Arguments for generating a structured teaching diagram."""

    focus: str = Field(
        min_length=1,
        max_length=1000,
        description="The specific concept, relationship, or process the diagram should emphasize.",
    )


# 工具名称到证据类型的映射，用于构建对话证据与来源
TOOL_EVIDENCE_TYPES: dict[str, str] = {
    "get_learner_profile": "learner_profile",
    "get_long_term_memory": "long_term_memory",
    "search_knowledge_base": "knowledge_base",
    "research": "web_search",
}

# 联网搜索事件处理函数类型
ResearchEventHandler = Callable[[ResearchEvent], Awaitable[None]]


# 装配当前辅导请求可用的业务工具（用户上下文/知识库/联网搜索）
def build_tutor_tools(
    request: TutorRequestContext,
    *,
    research_event_handler: ResearchEventHandler | None = None,
    diagram_context: str = "",
    diagram_generator: Any | None = None,
) -> list[Tool]:
    """装配当前辅导请求可用的业务工具。"""

    generator = diagram_generator

    async def generate_teaching_diagram(focus: str) -> dict[str, Any]:
        nonlocal generator
        logger.info("[ChatTools] generate_teaching_diagram 开始: focus_len=%d", len(focus))
        if generator is None:
            from app.chat.diagram_generator import TeachingDiagramGenerator

            generator = TeachingDiagramGenerator()
        result = await generator.generate(
            request=request,
            focus=focus,
            context=diagram_context,
        )
        logger.info("[ChatTools] generate_teaching_diagram 完成")
        return result

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
        Tool(
            name=GENERATE_TEACHING_DIAGRAM_TOOL_NAME,
            description=(
                "学生明确要求图解，或视觉关系能显著帮助理解时调用。"
                "调用成功后不要再输出文字回答。"
            ),
            args_model=GenerateTeachingDiagramArgs,
            handler=generate_teaching_diagram,
        ),
    ]
