"""Agent 合约 Schema — TutorAgent 输入、工具上下文、流式事件（重构后）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TutorRequestContext(BaseModel):
    """当前用户消息的辅导请求上下文。"""
    user_id: int
    username: str  # 用户名，用于文件路径构建
    session_id: str
    user_input: str = ""
    attachments: list[str] = Field(default_factory=list)
    enable_web_search: bool = False
    need_teaching_diagram: bool = False


class TutorAgentInput(BaseModel):
    """TutorAgent 的输入 — ChatService 构建，传入 TutorAgent.chat()。"""
    user_id: int
    username: str  # 用户名，用于文件路径构建
    session_id: str
    user_message_id: int
    question: str
    attachments: list[str] = Field(default_factory=list)
    history_messages: list[Any] = Field(default_factory=list)
    session_summary: str = ""
    enable_web_search: bool = False
    need_teaching_diagram: bool = False


# ── 流式事件类型（简化后）──

TutorRuntimeEventType = Literal[
    "message_start",      # 对话开始
    "agent_status",       # Agent 工具调用状态（包含附件分析、搜索、图解生成）
    "answer_token",       # 流式回答 token
    "answer_done",        # 回答完成
    "content_replace",    # 内容替换（安全过滤后校准）
    "diagram",            # 图解结果
    "final",              # 最终事件
    "error",              # 错误
]


class TutorRuntimeEvent(BaseModel):
    """TutorAgent 流式事件。"""
    type: TutorRuntimeEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    sequence: int = 0
    timestamp: float = 0.0
