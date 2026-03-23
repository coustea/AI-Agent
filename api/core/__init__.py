"""Core API configuration and utilities."""

from .config import settings, Settings
from .dependencies import get_redis_client as get_redis_service

__all__ = [
    "settings",
    "Settings",
    "get_redis_service",
]