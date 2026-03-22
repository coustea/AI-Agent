"""Core API configuration and utilities."""

from .config import settings, Settings
from .deps import get_redis_service

__all__ = [
    "settings",
    "Settings",
    "get_redis_service",
]