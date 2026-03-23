from typing import Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: Optional[str] = Field(default="新会话", max_length=200)


class SessionRead(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    message_id: int
    role: str
    content: str
    created_at: str
