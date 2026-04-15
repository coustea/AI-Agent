from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MentorChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    image_urls: Optional[list[str]] = None
    file_urls: Optional[list[str]] = None


class AttachmentInfo(BaseModel):
    url: str
    type: str
    name: str


class ToolCallRecord(BaseModel):
    tool: str
    args: dict | str
    result: str
    status: str


class ResourceCard(BaseModel):
    type: str
    title: str
    summary: str
    asset_urls: list[str]
    file_path: Optional[str] = None
    preview_text: str = ""


class ChatMessageItem(BaseModel):
    role: str
    content: str
    attachments: Optional[list[AttachmentInfo]] = None
    tool_calls: Optional[list[ToolCallRecord]] = None
    resource_cards: Optional[list[ResourceCard]] = None
    created_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    url: str
    file_type: str
    original_name: str
    size_bytes: int
