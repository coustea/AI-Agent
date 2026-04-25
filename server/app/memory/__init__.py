"""Public memory-layer exports.  # 记忆层公共API导出模块

This module serves as the single public entry point for the memory subsystem.
External callers should import only from this module, not from internal implementations.

模块职责：
- 导出 MemoryLayer 作为外部唯一入口
- 导出 PostChatMemoryOrchestrator 用于对话后处理流水线
- 导出 FactExtractionService 用于事实提取
- 导出 ProfileBuildingService/ProfileService 用于画像构建与持久化
- 导出辅助函数和常量供下游使用

设计原则：
- 外部模块只应依赖此文件导出的公共API
- 内部实现细节（_store, _fact, _profile）不应被外部直接导入
- 新增公共API时需同步更新 __all__ 列表
"""

from __future__ import annotations

from app.memory.layer import MemoryLayer
from app.memory.layer import PostChatMemoryOrchestrator
from app.memory._fact import FactExtractionService
from app.memory._profile import PROFILE_BUILDING_PROMPT, ProfileBuildingService, ProfileService, has_extractable_signal


__all__ = [
    "FactExtractionService",
    "MemoryLayer",
    "PROFILE_BUILDING_PROMPT",
    "PostChatMemoryOrchestrator",
    "ProfileBuildingService",
    "ProfileService",
    "has_extractable_signal",
]
