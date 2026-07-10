"""周概要构建器共享类型定义。"""

# 定义周摘要章节结果与整体构建结果的共享数据结构
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# 单个模块的周摘要章节结果（Markdown + 统计 + 原始长度）
@dataclass
class SectionResult:
    """单个模块的周摘要章节结果。

    Attributes:
        markdown: 该章节的 Markdown 内容（不含 ``## 标题``，仅含正文）。
        stats: 该模块的统计字典，用于汇总到全局概览。
              如 ``{"dialogue_turns": 5}`` 或 ``{"resources_generated": 3}``。
        raw_length: 原始数据的字符总长度，用于判断是否需要 LLM 精炼。
    """

    markdown: str = ""
    stats: dict[str, Any] = field(default_factory=dict)
    raw_length: int = 0


# 周摘要构建器的完整输出（聚合所有章节）
@dataclass
class DigestBuildResult:
    """周摘要构建器的完整输出。

    Attributes:
        markdown: 完整的周度学习摘要 Markdown（含标题和所有章节）。
        stats: 各模块统计的合并字典，供持久化到 ``WeeklyLearningDigest.stats``。
        courses_active: 本周活跃课程/主题列表。
        raw_length: 所有原始数据的总字符长度。
    """

    markdown: str = ""
    stats: dict[str, Any] = field(default_factory=dict)
    courses_active: list[str] = field(default_factory=list)
    raw_length: int = 0
