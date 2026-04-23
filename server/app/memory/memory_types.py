"""长期记忆类型常量与类型定义（单一真源）。"""  # 所有记忆类型常量的唯一来源

from __future__ import annotations

from typing import Final, Literal, TypeAlias

# 数据库 user_memory.memory_type 允许值
MEMORY_TYPE_PREFERENCE: Final[str] = "preference"  # 偏好类型：用户学习偏好
MEMORY_TYPE_GOAL: Final[str] = "goal"  # 目标类型：学习目标
MEMORY_TYPE_WEAKNESS: Final[str] = "weakness"  # 薄弱点类型：知识薄弱点
MEMORY_TYPE_FACT: Final[str] = "fact"  # 事实类型：稳定事实信息
MEMORY_TYPE_BACKGROUND: Final[str] = "background"  # 背景类型：用户背景信息
MEMORY_TYPE_SUMMARY: Final[str] = "summary"  # 摘要类型：对话压缩摘要

ALL_MEMORY_TYPES: Final[tuple[str, ...]] = (  # 所有支持的记忆类型元组
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_WEAKNESS,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_SUMMARY,
)

# FactAgent 只产出这 5 类，不含 summary
FACT_AGENT_MEMORY_TYPES: Final[tuple[str, ...]] = (  # 事实提取Agent产出的类型（不含摘要）
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_WEAKNESS,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_BACKGROUND,
)

MemoryType: TypeAlias = Literal[  # 全部记忆类型的类型别名
    "preference",
    "goal",
    "weakness",
    "fact",
    "background",
    "summary",
]

FactAgentMemoryType: TypeAlias = Literal[  # 事实提取Agent产出类型的别名
    "preference",
    "goal",
    "weakness",
    "fact",
    "background",
]

