"""搜索工具封装 — DuckDuckGo / Tavily / 讯飞 三路搜索。

WebSearchTool 会按既定顺序回退搜索引擎。
_redact_url_query_secrets 脱敏异常中的 API key，防止泄露到日志或响应。
"""

from __future__ import annotations

import asyncio
import re
import httpx
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_tavily import TavilySearch
from langchain_core.tools import tool

from app.config import TAVILY_KEY, SPARK_SEARCH_KEY
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
