"""Chat module schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MentorChatRequest(BaseModel):
    """统一对话请求，支持纯文本、图片和文档。"""

    message: str
    session_id: Optional[str] = None
    image_url: Optional[str] = None
    file_urls: Optional[list[str]] = None


class AttachmentInfo(BaseModel):
    """附件信息"""
    url: str
    type: str  # "image" or "document"
    name: str


class ToolCallRecord(BaseModel):
    """工具调用记录"""
    tool: str
    args: dict | str
    result: str
    status: str  # "success" | "error"


class ChatMessageItem(BaseModel):
    """单条聊天消息"""
    role: str
    content: str
    attachments: Optional[list[AttachmentInfo]] = None
    tool_calls: Optional[list[ToolCallRecord]] = None
    created_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    """文件上传响应"""
    url: str
    file_type: str  # "image" or "document"
    original_name: str
    size_bytes: int
