"""Chat 模块的数据契约。

- ``TutorInput``                           一轮辅导对话的统一输入上下文
- ``SourceItem`` / ``NormalizedToolResult`` 工具结果与引用来源
- ``UploadResponse`` / ``ChatMessageItem`` 上传与历史消息 DTO
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DiagramMode = Literal["auto", "required"]


class TutorInput(BaseModel):
    """TutorAgent 单轮运行输入上下文。"""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    username: str
    session_id: str
    user_message_id: int
    question: str
    attachments: list[str] = Field(default_factory=list)
    history_messages: list[Any] = Field(default_factory=list)
    session_summary: str = ""
    diagram_mode: DiagramMode = "auto"
    video_mode: bool = False
    voice_mode: bool = False
    attachment_context: str = ""


class SourceItem(BaseModel):
    """来源条目 —— 单个 URL 或知识库来源的元数据。"""

    source: str = ""
    title: str = ""
    url: str = ""
    summary: str = ""
    published_at: str | None = None


class NormalizedToolResult(BaseModel):
    """统一标准化后的工具执行结果。"""

    text: str = ""
    sources: list[SourceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def normalize_tool_result(raw_result: Any) -> NormalizedToolResult:
    """把任意工具返回值标准化为 ``NormalizedToolResult``。"""
    if raw_result is None:
        return NormalizedToolResult()
    if isinstance(raw_result, str):
        return NormalizedToolResult(text=raw_result)
    if isinstance(raw_result, BaseModel):
        raw_result = raw_result.model_dump()
    if isinstance(raw_result, Mapping):
        text = str(raw_result.get("text") or raw_result.get("message") or "").strip()
        raw_sources = raw_result.get("sources", [])
        sources: list[SourceItem] = []
        if isinstance(raw_sources, list):
            for item in raw_sources:
                if isinstance(item, dict):
                    sources.append(SourceItem(**item))
                elif isinstance(item, SourceItem):
                    sources.append(item)
        metadata = {k: v for k, v in raw_result.items() if k not in ("text", "message", "sources")}
        return NormalizedToolResult(text=text, sources=sources, metadata=metadata)
    return NormalizedToolResult(text=str(raw_result).strip())


class UploadResponse(BaseModel):
    """文件上传成功后的响应。"""

    url: str = Field(..., description="文件访问 URL")
    file_type: str = Field(default="document", description="image / document")
    original_name: str = Field(default="", description="原始文件名")
    size_bytes: int = Field(default=0, ge=0, description="文件大小")
    mime_type: str | None = Field(default=None, description="MIME 类型")


class ChatMessageItem:
    """历史消息 DTO，供 ``GET /chat/history`` 序列化。"""

    def __init__(
        self,
        *,
        id: int,
        user_message_id: int | None,
        role: str,
        content: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        activities: list[dict[str, Any]] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        video: dict[str, Any] | None = None,
        created_at: Any = None,
    ) -> None:
        self.id = id
        self.user_message_id = user_message_id
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.attachment_analyses = attachment_analyses or []
        self.activities = activities or []
        self.usage_metadata = usage_metadata
        self.video = video
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        """序列化为字典，仅输出非空的可选字段。"""
        data: dict[str, Any] = {
            "id": self.id,
            "user_message_id": self.user_message_id,
            "role": self.role,
            "content": self.content,
            "attachment_analyses": self.attachment_analyses,
            "activities": self.activities,
            "created_at": self.created_at,
        }
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.usage_metadata:
            data["usage_metadata"] = self.usage_metadata
        if self.video:
            data["video"] = self.video
        return data


__all__ = [
    "ChatMessageItem",
    "DiagramMode",
    "NormalizedToolResult",
    "SourceItem",
    "TutorInput",
    "UploadResponse",
    "normalize_tool_result",
]
