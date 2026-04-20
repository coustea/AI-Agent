from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TypedDict, Annotated

from pydantic import BaseModel
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# ===================================================================
# API 层数据模型（Pydantic BaseModel）
# ===================================================================

class MentorChatRequest(BaseModel):
    """聊天请求。"""
    message: str
    session_id: Optional[str] = None
    image_urls: Optional[list[str]] = None
    file_urls: Optional[list[str]] = None
    generate_image: Optional[bool] = False
    generate_video: Optional[bool] = False


class AttachmentInfo(BaseModel):
    """单条附件信息。"""
    url: str
    type: str       # "image" | "document"
    name: str


class ToolCallRecord(BaseModel):
    """一次工具调用的完整记录（API 层）。"""
    tool: str
    args: dict | str
    result: str | dict
    status: str      # "success" | "error"


class ChatMessageItem(BaseModel):
    """返回给前端的消息条目。"""
    role: str  # "user" | "assistant" | "tool"
    content: str
    attachments: Optional[list[AttachmentInfo]] = None
    tool_calls: Optional[list[ToolCallRecord]] = None
    created_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    """文件上传成功响应。"""
    url: str
    file_type: str      # "image" | "document"
    original_name: str
    size_bytes: int


# ===================================================================
# Agent 内部状态类型（TypedDict，total=False 兼容 LangGraph 增量更新）
# ===================================================================

class ToolCallDetail(TypedDict, total=False):
    """工具调用记录（Agent 内部状态）。"""
    tool: str
    args: dict[str, Any] | str
    result: str
    status: str
    error: str


class TutorState(TypedDict, total=False):
    """LangGraph 运行状态 — 精简版。

    移除了 planner/compile_plan/execute_step/replan 相关的复杂状态字段。
    """

    # ---- 用户身份与附件 ----
    user_id: int
    session_id: str
    image_urls: Optional[list[str]]
    file_urls: Optional[list[str]]
    generate_image: bool
    generate_video: bool
    request_generate_image: bool
    request_generate_video: bool

    # ---- 路由与执行模式 ----
    route: str                               # "direct" | "attachment_needed" | "search_needed"
    execution_mode: str                      # "direct" | "attachment" | "search"

    # ---- 上下文信息 ----
    profile_context: str
    fact_context: str
    recent_chat_context: str
    file_context: str
    attachment_analysis_context: str
    attachment_analysis: dict[str, Any]

    # ---- Prompt 模板 ----
    system_prompt: str

    # ---- 对话消息 ----
    messages: Annotated[list[AnyMessage], add_messages]

    # ---- 终止与调试信息 ----
    last_guard_decision: str                 # "generate_image" | "generate_video" | "end"
    guard_reason: str
    termination_reason: str
    image_generation_status: str
    video_generation_status: str
    image_generation_prompt: str
    video_generation_prompt: str
    image_generation_plan: dict[str, Any]
    video_generation_plan: dict[str, Any]
