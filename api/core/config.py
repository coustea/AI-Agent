"""Core API configuration module.

This module exports settings from db.models for backward compatibility.
"""

from api.db.models import settings, Settings

__all__ = ["settings", "Settings"]
