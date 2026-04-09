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


class ChatMessageItem(BaseModel):
    """单条聊天消息"""
    role: str
    content: str
    created_at: Optional[datetime] = None
