"""消息领域类型定义。

模块职责：
- 定义消息相关常量
"""

from __future__ import annotations

from typing import Final


# 消息角色
class MessageRole:
    """消息角色常量。"""
    USER: Final[str] = "user"
    ASSISTANT: Final[str] = "assistant"
    SYSTEM: Final[str] = "system"
    TOOL: Final[str] = "tool"


# 消息过期天数
MESSAGE_EXPIRE_DAYS: Final[int] = 7

# 消息角色列表（用于对话）
DIALOGUE_ROLES: Final[set[str]] = {MessageRole.USER, MessageRole.ASSISTANT}
