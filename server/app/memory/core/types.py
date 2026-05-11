"""核心类型定义。

模块职责：
- 定义模块名称常量
- 定义公共类型别名
"""

from __future__ import annotations

from typing import Final


class ModuleName:
    """模块名称常量。"""

    MENTOR: Final[str] = "mentor"
    """辅导模块（默认）。"""

    RESOURCE: Final[str] = "resource"
    """资源生成模块。"""

    AVATAR: Final[str] = "avatar"
    """数字人模块。"""
