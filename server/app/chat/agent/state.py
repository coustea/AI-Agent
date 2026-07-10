"""LangGraph 图状态定义 — 统一 Agent 架构。

状态字段分为三类：
1. 请求输入：user_id, session_id, question, attachments, enable_web_search, need_teaching_diagram
2. 上下文：history_messages, session_summary, attachment_context
3. Agent 循环：messages（LangGraph 标准 reducer）
4. 运行时：event_queue, stream_events, tool_invocations, sources, errors
5. 输出：final_answer, diagram_result
"""

from __future__ import annotations

import asyncio
import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.channels.untracked_value import UntrackedValue
from langgraph.graph.message import add_messages

from app.chat.schemas import TutorRuntimeEvent


# LangGraph 图状态：贯穿预处理节点与 ReAct 节点的共享数据流（输入/上下文/循环/运行时/输出）
class TutorAgentState(TypedDict, total=False):
    """LangGraph 图状态定义 — 统一 Agent 架构。"""

    # ── 请求输入（无 reducer — 后写覆盖）──
    user_id: int
    username: str  # 用户名，用于文件路径构建
    session_id: str
    user_message_id: int
    question: str
    attachments: list[str]
    enable_web_search: bool
    need_teaching_diagram: bool

    # ── 上下文（无 reducer）──
    history_messages: list[AnyMessage]
    session_summary: str

    # ── 附件预处理结果（由 preprocess 节点填充）──
    attachment_context: str

    # ── Agent 循环（LangGraph 标准 messages reducer）──
    messages: Annotated[list[AnyMessage], add_messages]

    # ── 运行时（列表字段用 reducer，Queue 用 UntrackedValue）──
    tool_invocations: Annotated[list[dict[str, Any]], operator.add]
    stream_events: Annotated[list[TutorRuntimeEvent], operator.add]
    event_queue: Annotated[asyncio.Queue, UntrackedValue]
    sources: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]

    # ── 输出 ──
    final_answer: str
    diagram_result: dict[str, Any] | None
