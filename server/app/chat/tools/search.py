"""搜索工具封装 — DuckDuckGo / Tavily / SerpApi / 讯飞 四路搜索。

WebSearchTool 会按既定顺序回退搜索引擎。
_redact_url_query_secrets 脱敏异常中的 API key，防止泄露到日志或响应。
"""

from __future__ import annotations

import asyncio
import serpapi
import re
import httpx
from typing import Any
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_tavily import TavilySearch
from langchain_core.tools import tool

from app.config import SERPAPI_KEY, TAVILY_KEY, SPARK_SEARCH_KEY
from app.infra.logging import get_logger

logger = get_logger(__name__)

# DuckDuckGo 搜索工具实例 — 免费无需 API key，作为首选搜索引擎
_duckduckgo_search_tool = DuckDuckGoSearchRun()
# Tavily 搜索工具实例 — 需要 API key，仅在配置时启用，最多返回 3 条结果
_tavily_search_tool = TavilySearch(tavily_api_key=TAVILY_KEY, max_results=3) if (TAVILY_KEY or "").strip() else None


def _redact_url_query_secrets(text: object) -> str:
    """脱敏异常文本中的 URL 查询参数，避免 api key 进入日志或响应。

    使用正则匹配 api_key=、key=、token= 等常见敏感参数名，替换为 [REDACTED]。
    """
    raw = str(text)
    # 快速检查：不含敏感标记则直接返回，避免不必要的正则匹配
    if not any(marker in raw.lower() for marker in ("api_key=", "key=", "token=")):
        return raw
    return re.sub(r"(?i)(api_key|key|token)=([^&\s]+)", r"\1=[REDACTED]", raw)


@tool("duckduckgo_search")
async def duckduckgo_search(query: str) -> str:
    """使用 DuckDuckGo 搜索网页，返回文本结果摘要。

    DuckDuckGo 免费无需 API key，作为默认搜索引擎。
    使用 asyncio.to_thread 将同步的 SDK 调用放到线程池执行，避免阻塞事件循环。
    """
    try:
        # DuckDuckGo SDK 是同步的，必须在线程池中执行
        result = await asyncio.to_thread(_duckduckgo_search_tool.run, query)
        logger.info(
            "[duckduckgo_search] query=%r result_preview=%r",
            query,
            str(result)[:300],
        )
        return str(result)
    except Exception as exc:
        logger.warning("[duckduckgo_search] failed: query=%r error=%s", query, exc)
        return f"DuckDuckGo 搜索失败: {exc}"

@tool("tavily_search")
async def tavily_search(query: str) -> str:
    """使用 Tavily 搜索网页，返回结构化搜索结果摘要。

    Tavily 是 AI 优化的搜索引擎，结果质量通常优于通用搜索引擎。
    """
    # Tavily 需要 API key，未配置时返回友好提示
    if _tavily_search_tool is None:
        return "Tavily 搜索不可用: 未配置 TAVILY_KEY"

    try:
        result = await asyncio.to_thread(_tavily_search_tool.run, query)
        logger.info(
            "[tavily_search] query=%r result_preview=%r",
            query,
            str(result)[:300],
        )
        return str(result)
    except Exception as exc:
        logger.warning("[tavily_search] failed: query=%r", query, exc)
        return f"Tavily 搜索失败: {exc}"

@tool("serp_search")
async def serp_search(query: str, location: str = "China", hl: str = "zh-CN", gl: str = "cn") -> str:
    """使用 SerpApi 搜索网页，返回结构化搜索结果摘要。

    Args:
        query: 搜索关键词。
        location: 搜索位置，默认中国。
        hl: 界面语言，默认中文。
        gl: 国家/地区，默认中国。

    Returns:
        搜索结果摘要字符串。
    """
    if not (SERPAPI_KEY or "").strip():
        return "SerpApi 搜索不可用: 未配置 SERPAPI_KEY"

    try:
        # 定义同步搜索函数，在线程池中执行
        def _search() -> dict[str, Any]:
            client = serpapi.Client(api_key=SERPAPI_KEY)
            return client.search({
                "q": query,
                "location": location,
                "hl": hl,
                "gl": gl,
                "google_domain": "google.com"
            })

        results = await asyncio.to_thread(_search)

        # 从 SerpApi 响应中提取有机搜索结果（排除广告等）
        organic_results = results.get("organic_results", [])
        if not organic_results:
            return "未找到相关搜索结果"

        # 格式化输出：每条结果包含标题、链接和摘要
        summaries = []
        for i, item in enumerate(organic_results[:5], 1):
            title = item.get("title", "无标题")
            link = item.get("link", "")
            snippet = item.get("snippet", "无摘要")
            summaries.append(f"{i}. {title}\n   链接: {link}\n   摘要: {snippet}")

        result_text = "\n\n".join(summaries)
        logger.info(
            "[serp_search] query=%r result_count=%d",
            query,
            len(organic_results),
        )
        return result_text
    except Exception as exc:
        # 脱敏异常信息，防止 API key 泄露到日志
        error = _redact_url_query_secrets(exc)
        logger.warning("[serp_search] failed: query=%r error=%s", query, error)
        return f"SerpApi 搜索失败: {error}"


@tool("spark_search")
async def spark_search(query: str) -> str:
    """讯飞搜索，返回结构化搜索结果摘要。

    使用讯飞开放平台搜索 API，支持中文语义搜索和重排序。
    """
    if not (SPARK_SEARCH_KEY or "").strip():
        return "讯飞搜索不可用: 未配置 SPARK_SEARCH_KEY"

    url = "https://search-api-open.cn-huabei-1.xf-yun.com/v2/search"
    if not query or not query.strip():
        return "讯飞搜索失败: query 不能为空"

    # 构造讯飞搜索 API 请求体：限制返回 10 条，开启重排序提升结果质量
    payload = {
        "search_params": {
            "query": query,
            "limit": 10,
            "enhance": {
                "open_rerank": True,  # 开启语义重排序，提升相关性
                "open_full_text": False  # 不返回全文，仅返回摘要
            }
        }
    }
    headers = {
        "Authorization": f"Bearer {SPARK_SEARCH_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # 使用 httpx 异步客户端发起 POST 请求，60 秒超时
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=payload)

        response.raise_for_status()
        data = response.json()

        # 讯飞 API 通过 success 字段标识请求是否成功
        if not data.get("success"):
            return f"讯飞搜索失败: {data}"

        # 从嵌套的响应结构中提取搜索结果文档列表
        documents = (
            data
            .get("data", {})
            .get("search_results", {})
            .get("documents", [])
        )

        if not documents:
            return "未找到相关搜索结果"

        # 格式化输出：最多取前 5 条结果，每条包含标题、链接和摘要
        summaries = []
        for i, doc in enumerate(documents[:5], 1):
            title = doc.get("name", "无标题")
            link = doc.get("url", "")
            # 优先使用 summary 字段，fallback 到 content 字段
            snippet = doc.get("summary", "") or doc.get("content", "无摘要")
            summaries.append(f"{i}. {title}\n   链接: {link}\n   摘要: {snippet}")

        return "\n\n".join(summaries)
    except Exception as exc:
        # 脱敏异常信息，防止 API key 泄露到日志
        error = _redact_url_query_secrets(exc)
        logger.warning("[spark_search] failed: query=%r error=%s", query, error)
        return f"讯飞搜索失败: {error}"
