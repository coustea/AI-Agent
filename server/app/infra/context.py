"""跨模块请求上下文：通过 ContextVar 在异步调用链中传递 user_id / session_id。

供 chat、avatar、profile、tools 等模块共享，
工具层无需显式传递用户身份即可获取当前调用者。
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_CURRENT_USER_ID: ContextVar[int | None] = ContextVar("current_user_id", default=None)
_CURRENT_SESSION_ID: ContextVar[str | None] = ContextVar("current_session_id", default=None)


@contextmanager
def runtime_context(user_id: int, session_id: str | None = None) -> Iterator[None]:
    """上下文管理器：在 with 块内设置当前 user_id/session_id，退出时自动恢复。"""
    user_token: Token[int | None] = _CURRENT_USER_ID.set(user_id)
    session_token: Token[str | None] = _CURRENT_SESSION_ID.set(session_id)
    try:
        yield
    finally:
        # In some async-generator cancellation paths, reset can run in a
        # different context; fail-safe cleanup avoids surfacing noisy errors.
        try:
            _CURRENT_USER_ID.reset(user_token)
        except ValueError:
            _CURRENT_USER_ID.set(None)
        try:
            _CURRENT_SESSION_ID.reset(session_token)
        except ValueError:
            _CURRENT_SESSION_ID.set(None)


