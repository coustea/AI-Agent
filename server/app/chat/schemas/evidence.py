"""证据与上传 Schema — 各流水线阶段产出的信息载体。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field


EvidenceType = Literal[
    "attachment",
    "web_search",
    "knowledge_base",
    "learner_profile",
    "long_term_memory",
    "recent_evaluation",
]


class SourceItem(BaseModel):
    """来源条目 — 单个 URL 或知识库来源的元数据。"""
    source: str = ""
    title: str = ""
    url: str = ""
    summary: str = ""
    published_at: str | None = None


class AgentError(BaseModel):
    """归一化的 Agent 错误。"""
    stage: str = ""
    code: str = ""
    message: str = ""
    recoverable: bool = True


class ToolInvocation(BaseModel):
    """单次工具调用记录。"""
    tool_call_id: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_text: str = ""
    status: Literal["success", "ignored", "failed"] = "success"
    assistant_message_id: int | None = None
    tool_message_id: int | None = None


class AttachmentAnalysis(BaseModel):
    """附件分析结果。"""
    file_url: str = ""
    file_name: str = ""
    analysis_type: Literal["image", "document"] = "image"
    summary_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedToolResult(BaseModel):
    """统一标准化的工具执行结果。"""
    text: str = ""
    sources: list[SourceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def normalize_tool_result(raw_result: Any) -> NormalizedToolResult:
    """将任意工具返回值标准化为 NormalizedToolResult。

    规范：
    - 字符串放入 text
    - Mapping 中优先读取 text 或 message
    - Mapping 中的 sources 单独提取
    - 其他字段放入 metadata
    - Pydantic 模型先 model_dump()
    - None 返回空结果
    """
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
            for s in raw_sources:
                if isinstance(s, dict):
                    sources.append(SourceItem(**s))
                elif isinstance(s, SourceItem):
                    sources.append(s)
        metadata = {k: v for k, v in raw_result.items() if k not in ("text", "message", "sources")}
        return NormalizedToolResult(text=text, sources=sources, metadata=metadata)
    return NormalizedToolResult(text=str(raw_result).strip())


class Evidence(BaseModel):
    """统一证据模型 — 各阶段产出的信息载体。"""
    evidence_type: EvidenceType
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.7
    freshness: str = "turn"
    scope: str = "turn"
    usable_for_answer: bool = True
    usable_for_diagram: bool = True


class EvidenceSet(BaseModel):
    """证据集合 — 编排流水线中各阶段产出的证据汇总容器。"""
    items: list[Evidence] = Field(default_factory=list)

    def extend(self, items: list[Evidence]) -> None:
        self.items.extend(items)


class UploadResponse(BaseModel):
    """文件上传成功后的响应 DTO。"""
    url: str = Field(..., description="文件访问 URL")
    file_type: str = Field(default="document", description="image / document")
    original_name: str = Field(default="", description="原始文件名")
    size_bytes: int = Field(default=0, ge=0, description="文件大小")
    mime_type: str | None = Field(default=None, description="MIME 类型")


# ── 消息数据模型 ──


class ChatMessageItem:
    """对话消息数据模型（OpenAI 格式）。

    字段说明：
    - id: 消息数据库主键
    - role: user / assistant / tool
    - content: 消息正文（OpenAI 格式，支持多部分内容）
    - tool_calls: 工具调用记录（assistant 消息）
    - tool_call_id: 关联的工具调用 ID（tool 消息）
    - created_at: 创建时间
    """

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
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        """序列化为字典，用于 JSON API 响应。"""
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
        return data
