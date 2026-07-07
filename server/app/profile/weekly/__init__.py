"""周度学习摘要构建器。

使用 5 个并行模块章节构建器从数据库聚合本周学习数据，
组装为结构化 Markdown，在内容超出阈值时通过 LLM 精炼。
"""

from app.profile.weekly.builder import build_digest, LLM_CONDENSE_THRESHOLD
from app.profile.weekly.types import DigestBuildResult, SectionResult

__all__ = [
    "LLM_CONDENSE_THRESHOLD",
    "build_digest",
    "DigestBuildResult",
    "SectionResult",
]
