"""ResearchAgent 工具注册表。

统一管理所有搜索工具和抓取工具，提供给 ResearchAgent 使用。
"""

from __future__ import annotations

from typing import Any

from app.infra.tool_excute import Tool
from app.infra.logging import get_logger
from app.shared.research.search_tools import (
    SearchQueryArgs,
    CurlArgs,
    WebFetchArgs,
    duckduckgo_search,
    duckduckgo_instant_answer,
    searxng_search,
    wikipedia_search,
    arxiv_search,
    github_search,
    stackoverflow_search,
    tavily_search,
    spark_search,
    curl_fetch,
    webfetch,
)

logger = get_logger(__name__)


# 工具名称常量
SEARCH_TOOL_NAMES = (
    "duckduckgo_search",
    "duckduckgo_instant_answer",
    "searxng_search",
    "wikipedia_search",
    "arxiv_search",
    "github_search",
    "stackoverflow_search",
    "tavily_search",
    "spark_search",
)

FETCH_TOOL_NAMES = (
    "curl_fetch",
    "webfetch",
)

RESEARCH_TOOL_ACTIONS: dict[str, str] = {
    "duckduckgo_search": "检索公开网页",
    "duckduckgo_instant_answer": "查询百科摘要",
    "searxng_search": "检索聚合搜索源",
    "wikipedia_search": "检索百科资料",
    "arxiv_search": "检索学术论文",
    "github_search": "检索开源项目",
    "stackoverflow_search": "检索技术问答",
    "tavily_search": "检索深度资料",
    "spark_search": "检索中文资料",
}


def _safe_handler(handler: Any, name: str) -> Any:
    """包装工具处理器，捕获异常并记录日志。"""
    async def wrapped(**kwargs: Any) -> Any:
        try:
            return await handler(**kwargs)
        except Exception as exc:
            logger.warning("[%s] failed: %s", name, exc)
            raise
    return wrapped


def build_search_tools() -> list[Tool]:
    """构建搜索工具列表。

    返回所有可用的搜索工具，包括免费工具和已配置的工具。
    """
    return [
        # 免费搜索引擎
        Tool(
            "duckduckgo_search",
            "DuckDuckGo 通用搜索（免费）",
            SearchQueryArgs,
            _safe_handler(duckduckgo_search, "duckduckgo_search"),
        ),
        Tool(
            "duckduckgo_instant_answer",
            "DuckDuckGo 即时答案和定义（免费）",
            SearchQueryArgs,
            _safe_handler(duckduckgo_instant_answer, "duckduckgo_instant_answer"),
        ),
        Tool(
            "searxng_search",
            "SearXNG 聚合搜索（免费，聚合多个引擎）",
            SearchQueryArgs,
            _safe_handler(searxng_search, "searxng_search"),
        ),
        Tool(
            "wikipedia_search",
            "Wikipedia 百科搜索（免费）",
            SearchQueryArgs,
            _safe_handler(wikipedia_search, "wikipedia_search"),
        ),
        Tool(
            "arxiv_search",
            "ArXiv 学术论文搜索（免费）",
            SearchQueryArgs,
            _safe_handler(arxiv_search, "arxiv_search"),
        ),
        Tool(
            "github_search",
            "GitHub 代码仓库搜索（免费）",
            SearchQueryArgs,
            _safe_handler(github_search, "github_search"),
        ),
        Tool(
            "stackoverflow_search",
            "StackOverflow 技术问答搜索（免费）",
            SearchQueryArgs,
            _safe_handler(stackoverflow_search, "stackoverflow_search"),
        ),

        # 已配置的搜索引擎
        Tool(
            "tavily_search",
            "Tavily AI 优化搜索（已配置 Key）",
            SearchQueryArgs,
            _safe_handler(tavily_search, "tavily_search"),
        ),
        Tool(
            "spark_search",
            "讯飞星火中文语义搜索（已配置 Key）",
            SearchQueryArgs,
            _safe_handler(spark_search, "spark_search"),
        ),
    ]


def build_fetch_tools() -> list[Tool]:
    """构建内容抓取工具列表。

    返回所有可用的抓取工具。
    """
    return [
        Tool(
            "curl_fetch",
            "curl 命令抓取网页（免费）",
            CurlArgs,
            _safe_handler(curl_fetch, "curl_fetch"),
        ),
        Tool(
            "webfetch",
            "HTTP GET 抓取网页（免费）",
            WebFetchArgs,
            _safe_handler(webfetch, "webfetch"),
        ),
    ]


def build_all_tools() -> list[Tool]:
    """构建所有工具列表（搜索 + 抓取）。

    返回完整的工具集，供 ResearchAgent 使用。
    """
    return build_search_tools() + build_fetch_tools()
