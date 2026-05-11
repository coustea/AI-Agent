"""Store 基类。

模块职责：
- 提供数据库引擎访问
- 定义公共方法
"""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine


class BaseStore:
    """Store 基类。"""

    def __init__(self) -> None:
        self.engine = engine

    async def _get_session(self) -> AsyncSession:
        """获取数据库会话。"""
        return AsyncSession(self.engine)
