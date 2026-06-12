"""长期记忆读取工具。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field

from app.chat.memory.service import get_chat_memory_service
from app.chat.memory.types import LTM_CATEGORIES
from app.chat.schemas import TutorTurnContext
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 长期记忆的合法分类枚举，LLM 只能从这些预定义类别中选择
# learning_background: 学习背景（学历、专业、先修知识等）
# long_term_goals: 长期学习目标
# learning_preferences: 学习偏好（如喜欢视频/文字、节奏快慢等）
# stable_weaknesses: 稳定的薄弱环节（多次暴露的知识盲区）
# interaction_rules: 交互规则（如回复语言、详细程度偏好）
# effective_strategies: 对该学习者有效的教学策略
# corrections: 对之前错误回答的修正记录
LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]


class GetLongTermMemoryArgs(BaseModel):
    """长期记忆查询工具的输入参数模型。"""
    category: LongTermMemoryCategory | None = Field(default=None, description="Canonical long-term-memory category.")
    reason: str = Field(default="", description="Why the tutor needs durable memory.")


# 类别别名映射：LLM 可能使用非标准名称，统一转换为内部类别
LONG_TERM_MEMORY_CATEGORY_ALIASES: dict[str, str] = {
    "goals_progress": "long_term_goals",
}


def _compact(text: str, *, limit: int = 3500) -> str:
    """截断过长文本，防止撑爆 LLM 上下文窗口。"""
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def make_get_long_term_memory(
    request: TutorTurnContext,
    memory_service: Any | None = None,
) -> Callable[..., Awaitable[str]]:
    """工厂函数：创建闭包绑定当前请求的长期记忆查询工具。

    闭包捕获 request.user_id，使 LLM 工具调用无需传递用户标识。
    """
    async def _impl(
        category: LongTermMemoryCategory | None = None,
        reason: str = "",
    ) -> str:
        # 使用注入的服务或获取默认全局服务实例
        svc = memory_service or get_chat_memory_service()
        # 标准化分类值：去除空白，空值视为查询全部分类
        category_value = str(category or "").strip() or None
        # 校验分类是否在合法范围内，防止 LLM 幻觉出不存在的分类
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        try:
            # 调用记忆服务获取指定分类的 Markdown 格式记忆内容
            markdown = await svc.get_memory_markdown(request.user_id, category=category_value)
        except Exception as exc:
            logger.warning("[get_long_term_memory] failed: %s", exc)
            return "暂时无法读取长期学习记忆。"
        # 将记忆内容与读取原因拼接，方便 LLM 理解上下文
        return _compact(f"长期记忆读取原因: {reason or '未提供'}\n{markdown}")

    return _impl
