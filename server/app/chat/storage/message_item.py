"""对话消息数据模型，用于历史记录查询和前端渲染。

与 OpenAI messages 格式对齐。
"""

from __future__ import annotations

from typing import Any


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
        role: str,
        content: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        created_at: Any = None,
    ) -> Any:
        self.id = id
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        """序列化为字典，用于 JSON API 响应。"""
        data: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data