"""Chat 模块统一数据契约 —— 涵盖运行状态、步骤时间线、SSE 事件与历史消息 DTO。"""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field

DiagramMode = Literal["auto", "required"]

RunStatus = Literal["queued", "running", "completed", "failed", "cancelled", "interrupted"]

RunPhase = Literal[
    "queued",
    "preparing",
    "thinking",
    "tool_calling",
    "streaming",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
]

StepKind = Literal[
    "thinking",
    "knowledge",
    "memory",
    "vision",
    "document",
    "code",
    "subagent",
    "tool",
]

StepStatus = Literal["running", "completed", "failed", "cancelled"]

RunEventName = Literal[
    "run.snapshot",
    "phase.changed",
    "step.upsert",
    "text.delta",
    "artifact.created",
    "run.finished",
]

TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled", "interrupted"})


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
    status: StepStatus = "running"
    timestamp: float = Field(default_factory=time.time)


class RunStep(BaseModel):
    """Agent 运行过程中的单个透明可观测步骤（推理、工具调用、子智能体执行）。"""

    step_id: str
    kind: StepKind = "tool"
    title: str
    subtitle: str = ""
    status: StepStatus = "running"
    tool_name: str = ""
    input_preview: str = ""
    output_preview: str = ""
    error: str = ""
    started_at: float = Field(default_factory=time.time)
    elapsed_ms: int = 0
    progress: int | None = None
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
    sequence: int = 0
    status: RunStatus = "queued"
    phase: RunPhase = "queued"
    phase_label: str = "等待处理"
    content: str = ""
    error: str = ""
    total_elapsed_ms: int = 0
    steps: list[RunStep] = Field(default_factory=list)
    artifacts: list[RunArtifact] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)


class RunEvent(BaseModel):
    """通过 SSE 推送给前端的单条事件帧。"""

    run_id: str
    sequence: int
    event: RunEventName
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


def encode_chat_sse(event: RunEvent) -> str:
    """将 RunEvent 编码为标准 SSE 帧文本（事件名固定为 chat.event）。"""
    return f"id: {event.sequence}\nevent: chat.event\ndata: {event.model_dump_json()}\n\n"


class UploadResponse(BaseModel):
    """文件上传成功后的元数据响应。"""

    url: str = Field(..., description="文件静态访问 URL")
    file_type: str = Field(default="document", description="image / document")
    original_name: str = Field(default="", description="原始文件名")
    size_bytes: int = Field(default=0, ge=0, description="文件字节大小")
    mime_type: str | None = Field(default=None, description="MIME 类型")


class ChatMessageItem(BaseModel):
    """会话历史消息 DTO，仅面向前端展示 user 与最终 assistant 对话轮次。"""

    id: int
    role: Literal["user", "assistant"]
    content: list[dict[str, Any]] = Field(default_factory=list)
    run_id: str | None = None
    run: dict[str, Any] | None = None
    created_at: Any = None


__all__ = [
    "ChatMessageItem",
    "DiagramMode",
    "RunArtifact",
    "RunEvent",
    "RunEventName",
    "RunPhase",
    "RunState",
    "RunStatus",
    "RunStep",
    "SourceItem",
    "StepKind",
    "StepStatus",
    "SubStep",
    "TERMINAL_STATUSES",
    "UploadResponse",
    "encode_chat_sse",
]
