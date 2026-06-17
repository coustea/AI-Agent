"""证据与上传 Schema — 各流水线阶段产出的信息载体。"""

from __future__ import annotations

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
    storage_key: str | None = Field(default=None, description="存储键")
    mime_type: str | None = Field(default=None, description="MIME 类型")
    extension: str | None = Field(default=None, description="文件扩展名")
