from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_current_user_id: ContextVar[int | None] = ContextVar("chat_current_user_id", default=None)  # 协程安全的用户上下文
_current_session_id: ContextVar[str | None] = ContextVar("chat_current_session_id", default=None)


@contextmanager
def chat_runtime_context(user_id: int, session_id: str | None = None) -> Iterator[None]:
    """上下文管理器：在 with 块内设置当前 user_id/session_id，退出时自动恢复。"""
    user_token: Token[int | None] = _current_user_id.set(user_id)
    session_token: Token[str | None] = _current_session_id.set(session_id)
    try:
        yield
    finally:
        _current_user_id.reset(user_token)
        _current_session_id.reset(session_token)


def get_current_user_id() -> int | None:
    return _current_user_id.get()


def get_current_session_id() -> str | None:
    return _current_session_id.get()


def set_user_id(user_id: int | None) -> None:
    """Compatibility setter for callers that need to seed user context."""
    _current_user_id.set(user_id)


def set_session_id(session_id: str | None) -> None:
    """Compatibility setter for callers that need to seed session context."""
    _current_session_id.set(session_id)
