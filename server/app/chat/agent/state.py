"""LangGraph 图状态定义。

各节点通过返回 dict 更新部分字段。列表字段使用 Annotated[T, operator.add] 约简器：
节点只需返回新追加项，LangGraph 自动与已有值合并。
event_queue 使用 UntrackedValue：运行时可读写但不参与序列化。
"""

from __future__ import annotations

import asyncio
import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.channels.untracked_value import UntrackedValue

from app.chat.schemas import ChatStreamEvent, ClassificationResult


class TutorAgentState(TypedDict, total=False):
    # 请求（无约简器 — 后写覆盖）
    user_id: int
    session_id: str
    turn_id: int
    user_message_id: int | None
    question: str
    attachments: list[str]
    enable_web_search: bool
    need_teaching_diagram: bool

    # 上下文
    history_messages: list[AnyMessage]
    session_summary: str

    # 分类
    classification: ClassificationResult

    # 附件
    attachment_context: str
    attachment_analyses: Annotated[list[dict[str, Any]], operator.add]

    # 证据（约简器：自动追加）
    evidence: Annotated[list[dict[str, Any]], operator.add]
    sources: Annotated[list[dict[str, Any]], operator.add]

    # 运行时（列表字段用约简器，Queue 用 UntrackedValue）
    tool_invocations: Annotated[list[dict[str, Any]], operator.add]
    stream_events: Annotated[list[ChatStreamEvent], operator.add]
    event_queue: Annotated[asyncio.Queue, UntrackedValue]
    errors: Annotated[list[str], operator.add]

    # 输出
    final_answer: str
    diagram_result: dict[str, Any] | None

    # 重试控制（无约简器 — 布尔覆盖）
    _search_attempted: bool