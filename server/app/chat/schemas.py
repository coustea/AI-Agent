"""Chat 模块统一数据契约 —— 涵盖 AgentInput、运行状态、步骤时间线、SSE 事件与历史消息 DTO。"""

from __future__ import annotations

import time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

DiagramMode = Literal["auto", "required"]

TerminalStatus = Literal["completed", "failed", "cancelled", "interrupted"]
RunStatus = Literal["queued", "running"] | TerminalStatus

RunPhase = Literal[
    "queued",
    "preparing",
    "waiting_model",
    "saving",
    "cancelling",
    "tool_calling",
    "streaming",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
]

StepStatus = Literal["running", "completed", "failed", "cancelled"]

TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled", "interrupted"})


class AttachmentInput(BaseModel):
    """用户随消息上传的单个附件描述。"""

    url: str
    file_type: str = "document"
    original_name: str = ""
    mime_type: str | None = None
    size_bytes: int = Field(default=0, ge=0)


class ChatRequest(BaseModel):
    """前端提交的单轮聊天请求，不包含身份与运行登记字段。"""

    question: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    attachments: list[AttachmentInput] = Field(default_factory=list)
    diagram_mode: DiagramMode = "auto"
    video_mode: bool = False


class AgentInput(ChatRequest):
    """单轮对话的请求与登记信息，用于服务编排和上下文准备。"""

    user_id: int
    username: str
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_message_id: int = 0
    is_first_turn: bool = False

    @property
    def effective_question(self) -> str:
        """返回非空的用户提问文本（仅传附件时自动补齐默认引导语）。"""
        text = self.question.strip()
        if text:
            return text
        return "请分析我上传的附件，并解答其中的问题。"


class SourceItem(BaseModel):
    """知识库或外部检索的引用来源条目。"""

    source: str = ""
    title: str = ""
    heading: str = ""
    url: str = ""
    summary: str = ""
    score: float | None = None


class SubStep(BaseModel):
    """子智能体（如 PPT / 视频生成）内部的实时子步骤。"""

    id: str
    title: str
    timestamp: float = Field(default_factory=time.time)


class RunStep(BaseModel):
    """Agent 运行过程中的单个透明可观测步骤（推理、工具调用、子智能体执行）。"""

    step_id: str
    title: str
    subtitle: str = ""
    status: StepStatus = "running"
    tool_name: str = ""
    input_preview: str = ""
    output_preview: str = ""
    error: str = ""
    started_at: float = Field(default_factory=time.time)
    elapsed_ms: int = 0
    sub_steps: list[SubStep] = Field(default_factory=list)


class RunArtifact(BaseModel):
    """运行产出的可下载/可预览多模态资源（教学视频 / PPT 课件）。"""

    id: str
    kind: str
    title: str = ""
    url: str = ""
    preview_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunState(BaseModel):
    """一次 Agent 运行的完整实时快照，同时服务 SSE 首帧同步与历史回放。"""

    run_id: str
    status: RunStatus = "queued"
    phase: RunPhase = "queued"
    phase_label: str = "等待处理"
    content: str = ""
    error: str = ""
    total_elapsed_ms: int = 0
    steps: list[RunStep] = Field(default_factory=list)
    artifacts: list[RunArtifact] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)


def encode_chat_sse(state: RunState) -> str:
    """将完整运行快照编码为唯一的 run.state SSE 帧。"""
    return f"event: run.state\ndata: {state.model_dump_json()}\n\n"


class ChatMessageItem(BaseModel):
    """会话历史消息 DTO，仅面向前端展示 user 与最终 assistant 对话轮次。"""

    id: int
    role: Literal["user", "assistant"]
    content: list[dict[str, Any]] = Field(default_factory=list)
    run: dict[str, Any] | None = None
    created_at: Any = None
