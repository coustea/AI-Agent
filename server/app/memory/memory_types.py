"""长期记忆类型常量与类型定义（单一真源）。  # 记忆类型字符串与类型别名的单一真源

模块职责：
- 定义所有记忆类型的字符串常量，确保下游（DB/JSON/前端/缓存/日志）引用一致
- 提供类型别名用于静态类型检查和 Pydantic 校验
- 区分"全部记忆类型"与"事实提取产出类型"

设计原则：
- 这些字符串值会持久化到 DB/JSON，修改会引发历史数据兼容问题
- 新增类型必须配套数据迁移，并同步更新 Literal 联合类型
- fact agent 只产出 FACT_AGENT_MEMORY_TYPES 子集，summary 由压缩流程生成

下游使用示例：
- 存储层写入：memory_type=MEMORY_TYPE_PREFERENCE
- 类型校验：memory_type in ALL_MEMORY_TYPES
- FactAgent 输出约束：FactAgentMemoryType 类型注解
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

# NOTE: 这些字符串值会持久化到 DB/JSON（以及可能出现在前端/缓存/日志中）；修改/重命名会引发历史数据兼容问题，必须配套数据迁移，并同步更新下方 Literal 联合类型与所有调用方。
# 数据库 user_memory.memory_type 的允许值（新增类型请先加常量，再更新 ALL_MEMORY_TYPES/MemoryType，并确认相关 agent/服务端逻辑是否需要支持）

MEMORY_TYPE_PREFERENCE: Final[str] = "preference"  # 偏好类型：用户相对稳定的偏好（如学习/表达/反馈偏好），用于长期个性化
MEMORY_TYPE_GOAL: Final[str] = "goal"  # 目标类型：用户阶段性或长期目标（如学习目标/计划意图），用于规划与提醒
MEMORY_TYPE_WEAKNESS: Final[str] = "weakness"  # 薄弱点类型：用户知识或能力薄弱点（待补强点），用于诊断与练习推荐
MEMORY_TYPE_FACT: Final[str] = "fact"  # 事实类型：与用户相关且相对稳定的事实信息（可验证/可复用），用于减少重复询问
MEMORY_TYPE_BACKGROUND: Final[str] = "background"  # 背景类型：用户背景画像信息（如经历/上下文约束），用于更贴合语境的回答
MEMORY_TYPE_SUMMARY: Final[str] = "summary"  # 摘要类型：对话压缩后的摘要性记忆（浓缩上下文），通常由压缩流程生成而非事实抽取

ALL_MEMORY_TYPES: Final[tuple[str, ...]] = (  # 代码侧"支持的全部记忆类型"枚举：常用于遍历/校验/过滤；新增/删除类型时需与 MemoryType 保持一致
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_WEAKNESS,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_SUMMARY,
)

# 事实提取流程（fact agent）只产出这 5 类，不含 summary：summary 属于"对话压缩"产物，语义与写入策略不同
FACT_AGENT_MEMORY_TYPES: Final[tuple[str, ...]] = (  # fact agent 允许写入/返回的记忆类型子集（用于约束 agent 输出与下游处理逻辑）
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_WEAKNESS,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_BACKGROUND,
)

# NOTE: Literal 联合会参与 FastAPI/Pydantic 的入参校验、类型提示与序列化；必须与常量值及 ALL_MEMORY_TYPES 完全一致，否则会出现"运行可写入但类型不允许/或反之"的偏差。
MemoryType: TypeAlias = Literal[  # 记忆类型字符串的受限联合类型：用于在类型层面显式列出所有允许值
    "preference",
    "goal",
    "weakness",
    "fact",
    "background",
    "summary",
]

# NOTE: fact agent 只会产出此子集；summary 由对话压缩流程生成并写入（两者不要混用，以免把摘要当作事实类记忆处理）。
FactAgentMemoryType: TypeAlias = Literal[  # fact agent 记忆类型子集的类型别名：用于约束抽取结果/接口返回，避免输出 summary 等非抽取类类型
    "preference",
    "goal",
    "weakness",
    "fact",
    "background",
]
