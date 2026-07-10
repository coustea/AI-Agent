"""Generic computer-theory animation video generation module."""

from app.shared.cartoon.cartoon import (
    AuditResult,
    CartoonScene,
    CartoonVideoAgent,
    CartoonVideoDocument,
    CartoonGenerationError,
    CartoonGenerationResult,
)
from app.shared.cartoon.renderer import CartoonVideoRenderer, CartoonVideoRenderResult
from app.shared.cartoon.service import CartoonVideoResult, CartoonVideoService

__all__ = [
    "AuditResult",
    "CartoonScene",
    "CartoonVideoAgent",
    "CartoonVideoDocument",
    "CartoonGenerationError",
    "CartoonGenerationResult",
    "CartoonVideoRenderer",
    "CartoonVideoRenderResult",
    "CartoonVideoResult",
    "CartoonVideoService",
]