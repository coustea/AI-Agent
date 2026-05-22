"""Chat response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """文件上传结果。"""

    url: str = Field(..., description="文件访问 URL")
    file_type: str = Field(default="document", description="文件类型: image / document")
    original_name: str = Field(default="", description="原始文件名")
    size_bytes: int = Field(default=0, ge=0, description="文件大小（字节）")