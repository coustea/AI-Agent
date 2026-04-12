from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_current_user_id: ContextVar[int | None] = ContextVar("chat_current_user_id", default=None)


@contextmanager
def chat_runtime_context(user_id: int) -> Iterator[None]:
    """为工具调用注入当前对话用户上下文。"""
    token: Token[int | None] = _current_user_id.set(user_id)
    try:
        yield
    finally:
        _current_user_id.reset(token)


def get_current_user_id() -> int | None:
    return _current_user_id.get()
