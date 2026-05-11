"""会话领域类型定义。

模块职责：
- 定义会话相关常量
- 定义会话状态枚举
"""

from __future__ import annotations

from typing import Final


# 默认会话标题
DEFAULT_SESSION_TITLE: Final[str] = "新对话"

# 标题最大长度
TITLE_MAX_LENGTH: Final[int] = 100
