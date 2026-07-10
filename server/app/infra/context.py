"""跨模块请求上下文管理。

通过 Python 的 ContextVar 在异步调用链中传递 user_id / session_id，
供 chat、avatar、profile、tools 等模块共享。

典型用法：
    with runtime_context(user_id=123, session_id="abc"):
        # 在此块内，任何地方都可以通过 get_current_context() 获取 user_id
        ...

ContextVar 的特性：
- 每个异步任务（asyncio.Task）拥有独立的上下文副本
- 任务内的所有函数调用共享同一份上下文
- 任务结束后自动恢复到父任务的上下文
"""

# 本模块基于 ContextVar 在异步调用链中传递用户与会话上下文，供各模块共享
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

# 当前用户 ID 的上下文变量，默认为 None（无用户上下文）
_CURRENT_USER_ID: ContextVar[int | None] = ContextVar("current_user_id", default=None)
# 当前会话 ID 的上下文变量，默认为 None
_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar("current_session_id", default=None)


# 上下文管理器：在 with 块内设置 user_id/session_id，退出时容错恢复
@contextmanager
def runtime_context(user_id: int, session_id: str | None = None) -> Iterator[None]:
    """上下文管理器：在 with 块内设置当前 user_id/session_id，退出时自动恢复。

    用于在请求处理链中传递用户身份，避免逐层手动传递参数。

    Args:
        user_id: 当前用户 ID
        session_id: 当前会话 ID（可选）
    """
    # 设置上下文变量，保存旧的 Token 用于恢复
    user_token: Token[int | None] = _CURRENT_USER_ID.set(user_id)
    session_token: Token[str | None] = _CURRENT_SESSION_ID.set(session_id)
    try:
        yield
    finally:
        # 安全恢复上下文：在某些异步生成器取消路径中，
        # reset 可能在不同上下文中运行，需要容错处理
        try:
            _CURRENT_USER_ID.reset(user_token)
        except ValueError:
            _CURRENT_USER_ID.set(None)
        try:
            _CURRENT_SESSION_ID.reset(session_token)
        except ValueError:
            _CURRENT_SESSION_ID.set(None)
