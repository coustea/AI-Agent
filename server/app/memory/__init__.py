"""记忆系统公共入口。"""

from __future__ import annotations

from app.memory.compression import SessionCompressor
from app.memory.context import MemoryContextBuilder
from app.memory.long_term import LongTermMemoryExtractor
from app.memory.profile import ProfileBuilder, calculate_score, is_onboarding_complete, normalize_onboarding
from app.memory.schemas import OnboardingResponse, OnboardingUpdate, ProfileResponse
from app.memory.service import MemoryService
from app.memory.store import ConcurrentUpdateError, MemoryStore
from app.memory.types import (
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    ProfileDimension,
    make_default_memory_json,
    make_default_profile_json,
    make_default_score_json,
    render_memory_markdown,
)
from app.memory.workflow import MemoryWorkflow

__all__ = [
    "MemoryService",
    "MemoryWorkflow",
    "MemoryStore",
    "ProfileBuilder",
    "SessionCompressor",
    "LongTermMemoryExtractor",
    "MemoryContextBuilder",
    "ConcurrentUpdateError",
    "ProfileDimension",
    "ALL_DIMENSIONS",
    "DIMENSION_NAMES",
    "make_default_profile_json",
    "make_default_score_json",
    "make_default_memory_json",
    "render_memory_markdown",
    "normalize_onboarding",
    "is_onboarding_complete",
    "calculate_score",
    "OnboardingUpdate",
    "OnboardingResponse",
    "ProfileResponse",
]
