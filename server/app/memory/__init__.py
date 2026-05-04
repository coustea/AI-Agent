"""Public memory-layer exports — 记忆层公共 API 导出模块。

模块职责：
- 导出 MemoryLayer 作为外部唯一入口
- 导出 PostChatMemoryOrchestrator 用于对话后处理流水线
- 导出 LongTermMemoryUpdateService 用于长期记忆更新
- 导出 ProfileBuildingService 用于画像构建

设计原则：
- 外部模块只应依赖此文件导出的公共 API
- 内部实现细节（_store, _fact, _profile）不应被外部直接导入
"""

from __future__ import annotations

from app.memory.layer import MemoryLayer, PostChatMemoryOrchestrator
from app.memory._fact import LongTermMemoryUpdateService
from app.memory._profile import ProfileBuildingService
from app.memory.memory_types import (
    ALL_PROFILE_DIMENSIONS,
    PROFILE_DIMENSION_NAMES,
    make_default_profile_json,
    make_default_long_term_memory_json,
    make_default_session_summary_json,
    render_profile_markdown,
    render_long_term_memory_markdown,
    render_session_summary_markdown,
)


__all__ = [
    "MemoryLayer",
    "PostChatMemoryOrchestrator",
    "LongTermMemoryUpdateService",
    "ProfileBuildingService",
    "ALL_PROFILE_DIMENSIONS",
    "PROFILE_DIMENSION_NAMES",
    "make_default_profile_json",
    "make_default_long_term_memory_json",
    "make_default_session_summary_json",
    "render_profile_markdown",
    "render_long_term_memory_markdown",
    "render_session_summary_markdown",
]
