"""联网搜索工具 — Web 搜索降级链（tavily → duckduckgo → spark）。"""

from __future__ import annotations

from app.chat.tools.search import duckduckgo_search, spark_search, tavily_search
from app.infra.logging import get_logger

logger = get_logger(__name__)


class WebSearchTool:
    """联网搜索工具：按优先级依次尝试 tavily → duckduckgo → spark。

    返回第一个有效结果。有效 = 非空且不含"不可用"/"失败"/"未找到"等标记。
    全部失败时返回空字符串。
    """

    async def search(self, query: str) -> tuple[str, str | None]:
        """执行搜索，返回 (结果文本, 使用的工具名)"""
        candidates = [
            ("tavily_search", tavily_search),
            ("duckduckgo_search", duckduckgo_search),
            ("spark_search", spark_search),
        ]
        for tool_name, tool in candidates:
            try:
                result = str(await tool.ainvoke({"query": query}) if hasattr(tool, "ainvoke") else await tool(query)).strip()
            except Exception as exc:
                logger.warning("[WebSearchTool] %s 失败: %s", tool_name, exc)
                continue
            if result and "不可用" not in result and "失败" not in result and "未找到" not in result:
                return result, tool_name
        return "", None
