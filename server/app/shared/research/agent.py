"""ResearchAgent - 独立的搜索子 Agent。

可以被 chat、resource、path 等模块调用。
只负责搜索和返回结构化结果，不涉及 LLM 总结、存储或业务逻辑。
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute
from app.shared.research.schemas import (
    ResearchError,
    ResearchEvent,
    ResearchEventHandler,
    ResearchReport,
    ResearchSourceItem,
    ResearchTask,
)
from app.shared.research.tools import (
    RESEARCH_TOOL_ACTIONS,
    SEARCH_TOOL_NAMES,
    build_search_tools,
)

logger = get_logger(__name__)


# ============================================================================
# 失败标记（用于过滤无效搜索结果）
# ============================================================================

FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到结果",
    "未找到相关",
    "无可用搜索结果",
    "API Key",
    "未配置",
    "不可用",
    "失败",
)


# ============================================================================
# ResearchAgent 实现
# ============================================================================

class ResearchAgent:
    """搜索子 Agent。

    特点：
    1. 只负责搜索和总结，不存储数据
    2. 多引擎并发搜索，竞速返回
    3. 大模型总结搜索结果，提高质量
    4. 无状态，每次调用独立
    """

    def __init__(
        self,
        *,
        tools: list[Any] | None = None,
        event_handler: ResearchEventHandler | None = None,
    ) -> None:
        """初始化 ResearchAgent。

        Args:
            tools: 工具列表（可选，默认使用所有搜索工具）
            event_handler: 事件回调（可选，用于监听执行进度）
        """
        self.tools = list(tools) if tools is not None else build_search_tools()
        self.event_handler = event_handler

    async def run(self, task: ResearchTask) -> ResearchReport:
        """执行搜索任务，返回结构化结果。

        流程：
        1. 多引擎并发搜索
        2. 解析搜索结果为结构化数据
        3. 去重并返回

        Args:
            task: 搜索任务定义

        Returns:
            ResearchReport: 搜索结果报告
        """
        logger.info("[ResearchAgent] starting search: query=%r", task.query)

        # 1. 创建请求级 ToolExcute
        tool_excute = ToolExcute(
            tools=self.tools,
            event_handler=self._emit_event,
        )

        # 2. 并发搜索
        search_tasks = [
            self._search_tool(tool_excute, tool_name, task.query)
            for tool_name in SEARCH_TOOL_NAMES
        ]
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # 3. 解析有效结果
        sources: list[ResearchSourceItem] = []
        errors: list[ResearchError] = []

        for i, result in enumerate(all_results):
            if isinstance(result, Exception):
                logger.debug("[ResearchAgent] result[%d] is exception: %s", i, result)
                errors.append(ResearchError(
                    stage="search",
                    code="tool_error",
                    message=str(result),
                    recoverable=True,
                ))
                continue

            if self._is_valid_result(result):
                tool_name, result_text = result
                parsed = self._parse_search_text(result_text, tool_name)
                sources.extend(parsed)
                logger.debug("[ResearchAgent] result[%d] parsed %d items", i, len(parsed))
            else:
                reason = "too_short" if len(str(result).strip()) < 50 else "failure_marker"
                logger.debug("[ResearchAgent] result[%d] invalid reason=%s", i, reason)
                errors.append(ResearchError(
                    stage="filter",
                    code="invalid_result",
                    message="搜索结果无效或为失败标记",
                    recoverable=True,
                ))

        # 4. 去重（按 URL）
        unique_sources: list[ResearchSourceItem] = []
        seen_urls = set()
        for s in sources:
            if s.url and s.url not in seen_urls:
                unique_sources.append(s)
                seen_urls.add(s.url)

        logger.info("[ResearchAgent] completed: query=%r sources=%d", task.query, len(unique_sources))

        # 5. 返回报告
        return ResearchReport(
            query=task.query,
            sources=unique_sources,
            errors=errors,
        )

        logger.info("[ResearchAgent] completed: query=%r context_length=%d", task.query, len(summary))
        return report

    async def _emit_event(self, event: dict[str, Any]) -> None:
        """补充展示语义后，把生命周期事件交还给调用方。"""
        if self.event_handler is None:
            return
        payload = dict(event)
        tool_name = str(payload.get("tool_name") or "")
        payload["action"] = RESEARCH_TOOL_ACTIONS.get(tool_name, "核验研究资料")
        await self.event_handler(payload)

    async def _search_tool(
        self,
        tool_excute: ToolExcute,
        tool_name: str,
        query: str,
    ) -> Any:
        """调用单个搜索工具。

        Args:
            tool_excute: 工具执行器
            tool_name: 工具名称
            query: 搜索查询

        Returns:
            搜索结果（可能是异常）
        """
        try:
            result = await tool_excute.execute({
                "id": f"{tool_name}-{uuid4().hex}",
                "name": tool_name,
                "args": {"query": query},
            })
            logger.debug("[ResearchAgent] tool=%s success result_len=%d", tool_name, len(str(result)))
            return tool_name, str(result)
        except Exception as exc:
            logger.warning("[ResearchAgent] tool=%s failed: %s", tool_name, exc)
            return exc

    def _is_valid_result(self, result: Any) -> bool:
        """检查搜索结果是否有效。

        Args:
            result: 搜索结果

        Returns:
            是否有效
        """
        if isinstance(result, Exception):
            return False

        text = str(result[1] if isinstance(result, tuple) and len(result) == 2 else result)
        if len(text.strip()) < 50:
            return False

        # 过滤失败标记
        for marker in FAILURE_MARKERS:
            if marker in text:
                return False

        return True

    def _parse_search_text(self, text: str, source: str) -> list[ResearchSourceItem]:
        """解析搜索工具返回的格式化字符串为结构化数据。

        Args:
            text: 搜索结果文本（格式："{index}. {title}\n   链接: {url}\n   摘要: {snippet}"）
            source: 来源工具名称

        Returns:
            结构化搜索结果列表
        """
        results: list[ResearchSourceItem] = []
        lines = text.split("\n")
        current: dict[str, str] = {"source": source}

        for line in lines:
            line = line.strip()

            # 匹配标题行（数字开头）
            if line and line[0].isdigit() and ". " in line:
                # 保存前一个结果
                if current.get("url"):
                    results.append(ResearchSourceItem(
                        source=current.get("source", source),
                        title=current.get("title", ""),
                        url=current.get("url", ""),
                        summary=current.get("summary", ""),
                    ))
                current = {"source": source}
                current["title"] = line.split(". ", 1)[-1]

            # 匹配链接行
            elif "链接:" in line or "链接 :" in line:
                url = line.split("链接:")[-1].split("链接 :")[-1].strip()
                if url.startswith("http"):
                    current["url"] = url

            # 匹配摘要行
            elif "摘要:" in line or "摘要 :" in line:
                snippet = line.split("摘要:")[-1].split("摘要 :")[-1].strip()
                current["summary"] = snippet

        # 添加最后一个结果
        if current.get("url"):
            results.append(ResearchSourceItem(
                source=current.get("source", source),
                title=current.get("title", ""),
                url=current.get("url", ""),
                summary=current.get("summary", ""),
            ))

        return results
