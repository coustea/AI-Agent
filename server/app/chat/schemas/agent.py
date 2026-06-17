"""Agent 合约 Schema — TutorAgent 输入、工具上下文、流式事件。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TutorToolCall(BaseModel):
    """TutorAgent 节点选择出的工具调用。"""
    tool_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TutorTurnContext(BaseModel):
    """单轮辅导上下文。"""
    user_id: int
    session_id: str
    user_input: str = ""
    attachments: list[str] = Field(default_factory=list)
    enable_web_search: bool = False
    need_teaching_diagram: bool = False


class TutorAgentInput(BaseModel):
    """TutorAgent 的输入 — ChatService 构建，传入 TutorAgent.chat()。"""
    user_id: int
    session_id: str
    turn_id: int
    user_message_id: int | None = None
    question: str
    attachments: list[str] = Field(default_factory=list)
    history_messages: list[Any] = Field(default_factory=list)
    session_summary: str = ""
    enable_web_search: bool = False
    need_teaching_diagram: bool = False


class ClassificationResult(BaseModel):
    """classify 节点的输出 — 意图分类和路由决策。"""
    intent: str = "general_qa"
    subject: str = ""
    difficulty: str = "intermediate"
    needs_file_analysis: bool = False
    needs_knowledge_search: bool = False
    needs_web_search: bool = False
    needs_profile: bool = False
    needs_long_term_memory: bool = False
    needs_recent_evaluation: bool = False
    needs_diagram: bool = False
    safety_risk: str = "none"
    answer_style: str = "explain"


ChatStreamEventType = Literal[
    "message_start", "classify_done",
    "file_analysis_start", "file_analysis_done",
    "tool_start", "tool_done",
    "answer_token", "answer_done",
    "diagram_start", "diagram_done",
    "memory_update_start", "memory_update_done",
    "final", "error",
]


class ChatStreamEvent(BaseModel):
    """TutorAgent 流式事件。"""
    type: ChatStreamEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    sequence: int = 0
    timestamp: float = 0.0
