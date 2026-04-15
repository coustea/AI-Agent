"""Backward-compatible database exports.

The actual database implementation now lives in
``app.infrastructure.database.engine``. Keep this module as a stable import
path for legacy modules until the remaining refactor is complete.
"""

from app.infrastructure.database.engine import engine, get_session, init_db

__all__ = ["engine", "get_session", "init_db"]
