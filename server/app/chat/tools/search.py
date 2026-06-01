"""搜索工具封装。"""

from __future__ import annotations

import serpapi
import re
import requests
from langchain_community.tools import DuckDuckGoSearchRun, TavilySearchResults
from langchain_core.tools import tool
from sympy import false

from app.config import SERPAPI_KEY, TAVILY_KEY,SPARK_SEARCH_KEY
from app.infra.logging import get_logger

logger = get_logger(__name__)


def _redact_url_query_secrets(text: object) -> str:
    """脱敏异常文本中的 URL 查询参数，避免 api key 进入日志或响应。"""
    raw = str(text)
    if not any(marker in raw.lower() for marker in ("api_key=", "key=", "token=")):
        return raw
    return re.sub(r"(?i)(api_key|key|token)=([^&\s]+)", r"\1=[REDACTED]", raw)


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

@tool("tavily_search")
def tavily_search(query: str) -> str:
    """使用 Tavily 搜索网页，返回结构化搜索结果摘要。"""
    if not (TAVILY_KEY or "").strip():
        return "Tavily 搜索不可用: 未配置 TAVILY_KEY"

    try:
        search_tool = TavilySearchResults(tavily_api_key=TAVILY_KEY, max_results=3)
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

@tool("serp_search")
def serp_search(query: str, location: str = "China", hl: str = "zh-CN", gl: str = "cn") -> str:
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
        client = serpapi.Client(api_key=SERPAPI_KEY)
        results = client.search({
            "q": query,
            "location": location,
            "hl": hl,
            "gl": gl,
            "google_domain": "google.com"
        })

        # 提取有机搜索结果
        organic_results = results.get("organic_results", [])
        if not organic_results:
            return "未找到相关搜索结果"

        # 格式化输出
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
        error = _redact_url_query_secrets(exc)
        logger.warning("[serp_search] failed: query=%r error=%s", query, error)
        return f"SerpApi 搜索失败: {error}"


@tool("spark_search")
def spark_search(query: str):
    """
    讯飞搜索封装函数
    """
    url = "https://search-api-open.cn-huabei-1.xf-yun.com/v2/search"
    if not query or not query.strip():
        raise ValueError("query 不能为空")

    payload = {
        "search_params": {
            "query": query,
            "limit": 10,
            "enhance": {
                "open_rerank": True,
                "open_full_text": False
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {SPARK_SEARCH_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"讯飞搜索失败: {data}")

    documents = (
        data
        .get("data", {})
        .get("search_results", {})
        .get("documents", [])
    )

    results = []

    for doc in documents:
        item = {
            "title": doc.get("name", ""),
            "summary": doc.get("summary", ""),
            "url": doc.get("url", ""),
            "published_date": doc.get("published_date", "")
        }

        content = doc.get("content", "")
        if content:
            item["content"] = content

        results.append(item)

    return {
        "query": query,
        "results": results
    }

