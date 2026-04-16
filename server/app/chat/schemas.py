from datetime import datetime
from typing import Optional

from pydantic import BaseModel

# 聊天请求（当前接口用 Form 接收参数，此类未直接使用）
class MentorChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    image_urls: Optional[list[str]] = None
    file_urls: Optional[list[str]] = None


class AttachmentInfo(BaseModel):
    """单条附件信息。"""
    url: str
    type: str       # "image" | "document"
    name: str


class ToolCallRecord(BaseModel):
    """一次工具调用的完整记录。"""
    tool: str        # 工具名称
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
    url: str            # 前端访问该文件的 API 路径
    file_type: str      # "image" | "document"
    original_name: str
    size_bytes: int
