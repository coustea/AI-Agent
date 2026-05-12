"""记忆层公共 API 导出模块。

领域驱动设计架构：
- core/     核心工具和基类
- session/  会话领域
- message/  消息领域
- summary/  概要领域
- profile/  画像领域
- memory/   长期记忆领域
- context/  上下文领域
- pipeline/ 后处理流水线

外部模块推荐使用：
- MemoryLayer: 记忆层主入口
- PipelineService: 后处理流水线

高级用法：
- 各 Store 类: 直接访问存储层
- 各 Service 类: 直接访问服务层
"""

from __future__ import annotations

# 主入口
from app.memory.layer import MemoryLayer

# 流水线
from app.memory.pipeline.service import PipelineService

# Store 类（高级用法）
from app.memory.session.store import SessionStore
from app.memory.message.store import MessageStore
from app.memory.summary.store import SummaryStore
from app.memory.profile.store import ProfileStore
from app.memory.memory.store import LongTermMemoryStore

# Service 类（高级用法）
from app.memory.session.service import SessionService
from app.memory.message.service import MessageService
from app.memory.summary.service import SummaryService
from app.memory.profile.service import ProfileService
from app.memory.memory.service import LongTermMemoryService
from app.memory.context.service import ContextService

# 工具函数
from app.memory.profile.types import (
    ProfileDimension,
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    make_default_profile_json,
    make_default_score_json,
)
from app.memory.profile.service import (
    normalize_onboarding,
    is_onboarding_complete,
    calculate_score,
)

__all__ = [
    # 主入口
    "MemoryLayer",
    # 流水线
    "PipelineService",
    # Store 类
    "SessionStore",
    "MessageStore",
    "SummaryStore",
    "ProfileStore",
    "LongTermMemoryStore",
    # Service 类
    "SessionService",
    "MessageService",
    "SummaryService",
    "ProfileService",
    "LongTermMemoryService",
    "ContextService",
    # 工具函数
    "ProfileDimension",
    "ALL_DIMENSIONS",
    "DIMENSION_NAMES",
    "make_default_profile_json",
    "make_default_score_json",
    "normalize_onboarding",
    "is_onboarding_complete",
    "calculate_score",
]
