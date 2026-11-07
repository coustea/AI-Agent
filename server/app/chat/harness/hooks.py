"""Agent 循环的钩子总线。

循环只保留「请求模型 → 派发工具 → 追加消息」三步，其余全部通过钩子外挂：

    run_started     循环开始前（附件分析、上下文构建、工具装配）
    step_started    每轮推理开始（思考活动、首轮 turn.started）
    text_delta      模型流式产出一段增量文本（转 text.delta）
    turn_finished   模型不再请求工具（text.completed）
    tools_started   一批 tool_calls 就绪（一次 assistant 落库 + 逐个 running 活动）
    tool_finished   单个工具结果就绪（tool 消息落库 + 活动终态 + 产物收集）
    run_finished    运行结束（最终回答落库、终态事件、后台记忆任务）

钩子异常一律就地隔离并记日志，不允许打断推理循环。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from app.infra.logging import get_logger

logger = get_logger(__name__)

HookName = Literal[
    "run_started",
    "step_started",
    "text_delta",
    "turn_finished",
    "tools_started",
    "tool_finished",
    "run_finished",
]

HookHandler = Callable[..., Awaitable[None]]


class HookBus:
    """按事件名注册与触发异步钩子。"""

    def __init__(self) -> None:
        """初始化钩子注册表。"""
        self._handlers: dict[str, list[HookHandler]] = defaultdict(list)

    def on(self, name: HookName, handler: HookHandler) -> None:
        """注册一个钩子处理函数。"""
        self._handlers[name].append(handler)

    async def trigger(self, name: HookName, *args: Any, **kwargs: Any) -> None:
        """依次触发某事件的全部钩子，单个钩子失败不影响后续与循环。"""
        for handler in self._handlers.get(name, ()):
            try:
                await handler(*args, **kwargs)
            except Exception:
                logger.exception("[Hook] %s 处理失败: %s", name, getattr(handler, "__name__", handler))


__all__ = ["HookBus", "HookHandler", "HookName"]
