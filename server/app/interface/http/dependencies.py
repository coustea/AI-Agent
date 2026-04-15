"""HTTP dependencies."""

from __future__ import annotations

from app.adapters.auth.security import get_current_user
from app.adapters.db.session import get_session
from app.bootstrap.container import AppContainer, get_container


def get_app_container() -> AppContainer:
    return get_container()


__all__ = ["get_app_container", "get_current_user", "get_session"]
