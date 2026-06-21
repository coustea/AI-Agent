"""对话消息数据模型，用于历史记录查询和前端渲染。"""

from __future__ import annotations

from typing import Any


class ChatMessageItem:
    """对话消息数据模型。

    字段说明：
    - id: 消息数据库主键
    - role: user / assistant / tool
    - content: 消息正文
    - attachments: 附件列表（图片/文件）
    - tool_calls: 工具调用记录
    - tool_call_id: 关联的工具调用 ID
    - knowledge_sources: 知识来源
    - attachment_analyses: 附件分析结果
    - agent_activities: 本轮工具调用与附件分析的可展示记录
    - teaching_diagram: 教学图解数据
    - turn_id: 所属 turn 的 ID
    - message_kind: 消息分类
    - created_at: 创建时间
    """

    def __init__(
        self,
        *,
        id: int,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        agent_activities: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
        created_at: Any = None,
    ) -> Any:
        self.id = id
        self.role = role
        self.content = content
        self.attachments = attachments
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.knowledge_sources = knowledge_sources
        self.attachment_analyses = attachment_analyses
        self.agent_activities = agent_activities
        self.teaching_diagram = teaching_diagram
        self.turn_id = turn_id
        self.message_kind = message_kind
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        """序列化为字典，用于 JSON API 响应。"""
        data: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }
        if self.attachments:
            data["attachments"] = self.attachments
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.knowledge_sources:
            data["knowledge_sources"] = self.knowledge_sources
        if self.attachment_analyses:
            data["attachment_analyses"] = self.attachment_analyses
        if self.agent_activities:
            data["agent_activities"] = self.agent_activities
        if self.teaching_diagram:
            data["teaching_diagram"] = self.teaching_diagram
        if self.turn_id is not None:
            data["turn_id"] = self.turn_id
        if self.message_kind:
            data["message_kind"] = self.message_kind
        return data
