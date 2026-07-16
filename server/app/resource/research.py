"""资源生成中的受控网页检索。

网页检索不属于资源 Agent 基类。只有明确导入本模块的规划和阅读流程可以使用它。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.shared.research.agent import ResearchAgent
from app.shared.research.schemas import ResearchEvent, ResearchReport, ResearchTask


async def research_web(
    query: str,
    *,
    objective: str,
    event_handler: Callable[[ResearchEvent], Awaitable[None]] | None = None,
) -> ResearchReport:
    """执行一次网页检索，结果仅由调用方在当前阶段使用。"""
    return await ResearchAgent(event_handler=event_handler).run(
        ResearchTask(
            query=query,
            objective=objective,
            depth="standard",
            sources={"web"},
        )
    )
