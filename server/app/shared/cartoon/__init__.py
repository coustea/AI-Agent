"""动画讲解视频生成模块。"""

from app.shared.cartoon.cartoon import (
    AuditResult,
    CartoonGenerationError,
    CartoonGenerationResult,
    CartoonScene,
    CartoonVideoAgent,
    CartoonVideoDocument,
)
from app.shared.cartoon.renderer import CartoonVideoRenderer, CartoonVideoRenderResult
from app.shared.cartoon.service import CartoonService

__all__ = [
    # 服务层（统一入口）
    "CartoonService",
    # 底层组件
    "CartoonVideoAgent",
    "CartoonVideoRenderer",
    "CartoonVideoRenderResult",
    # 数据结构
    "AuditResult",
    "CartoonScene",
    "CartoonVideoDocument",
    "CartoonGenerationError",
    "CartoonGenerationResult",
]