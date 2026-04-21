"""DuckDuckGo 搜索工具封装。

通过 langchain_community.tools.DuckDuckGoSearchRun 接入统一工具注册表。
"""

from __future__ import annotations

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool

from app.infra.logging import get_logger
from app.tools.registry import register
from app.config import TAVILY_API_KEY

logger = get_logger(__name__)


@tool("duckduckgo_search")
def duckduckgo_search(query: str) -> str:
    """使用 DuckDuckGo 搜索网页，返回文本结果摘要。"""
    try:
        search_tool = DuckDuckGoSearchRun()
        result = search_tool.run(query)
        logger.info(
            "[duckduckgo_search] query=%r result_preview=%r",
            query,
            str(result)[:300],
        )
        return str(result)
    except Exception as exc:
        logger.warning("[duckduckgo_search] failed: query=%r error=%s", query, exc)
        return f"DuckDuckGo 搜索失败: {exc}"

@tool('tavily_search')
def tavily_search(query: str) -> str:
    try:
        search_tool = TavilySearchResults(tavily_api_key=TAVILY_API_KEY,max_results=3)
        result = search_tool.run(query)
        logger.info(
            "[tavily_search] query=%r result_preview=%r",
            query,
            str(result)[:300],
        )
        return str(result)
    except Exception as exc:
        logger.warning("[tavily_search] failed: query=%r", query, exc)
        return f"Tavily 搜索失败: {exc}"

register(duckduckgo_search)
register(tavily_search)
