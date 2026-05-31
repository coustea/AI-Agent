"""聊天请求模式定义。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="消息角色: user / assistant / system / tool")
    content: str = Field(..., description="消息文本内容")
    tool_calls: list[dict] | None = Field(default=None, description="当 role 为 assistant 时，携带的大模型工具调用要求")
    tool_call_id: str | None = Field(default=None, description="当 role 为 tool 时，对应的工具调用 ID")
