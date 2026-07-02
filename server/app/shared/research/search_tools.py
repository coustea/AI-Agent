"""免费搜索工具集 - 无需 API Key。

包含多种免费搜索引擎和专业搜索工具，确保信息来源多样化、可靠。
"""

from __future__ import annotations

import asyncio
import subprocess
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel, Field

from app.infra.logging import get_logger

logger = get_logger(__name__)


class SearchQueryArgs(BaseModel):
    """搜索查询参数。"""
    query: str = Field(description="Search query")


# ============================================================================
# DuckDuckGo 搜索（免费）
# ============================================================================

async def duckduckgo_search(query: str) -> str:
    """DuckDuckGo 搜索 - 免费，无需 API Key。

    使用 ddgs SDK 进行搜索。
    """
    from ddgs import DDGS

    try:
        client = DDGS()
        rows = await asyncio.to_thread(client.text, query, max_results=5)

        if not rows:
            return "DuckDuckGo 搜索未找到结果"

        result = "\n\n".join(
            f"{index}. {row.get('title') or '无标题'}\n"
            f"   链接: {row.get('href') or row.get('url') or ''}\n"
            f"   摘要: {row.get('body') or row.get('snippet') or '无摘要'}"
            for index, row in enumerate(rows[:5], 1)
        )

        logger.info("[duckduckgo_search] query=%r result_preview=%r", query, result[:300])
        return result

    except Exception as exc:
        logger.warning("[duckduckgo_search] failed: query=%r error=%s", query, exc)
        return f"DuckDuckGo 搜索失败: {exc}"


async def duckduckgo_instant_answer(query: str) -> str:
    """DuckDuckGo 即时答案 - 免费。

    用于获取定义、百科摘要等快速答案。
    """
    import urllib.parse

    encoded_query = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["curl", "-s", "--max-time", "15", url],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return f"DuckDuckGo API 请求失败"

        import json
        data = json.loads(result.stdout)
        output_parts = []

        # 提取摘要
        abstract = data.get("Abstract", "")
        if abstract:
            output_parts.append(f"摘要:\n{abstract}")

        # 提取即时答案
        answer = data.get("Answer", "")
        if answer:
            output_parts.append(f"答案:\n{answer}")

        # 提取定义
        definition = data.get("Definition", "")
        if definition:
            output_parts.append(f"定义:\n{definition}")

        if not output_parts:
            return "DuckDuckGo 即时答案未找到相关内容"

        return "\n\n".join(output_parts)

    except Exception as exc:
        logger.warning("[duckduckgo_instant_answer] failed: query=%r error=%s", query, exc)
        return f"DuckDuckGo 即时答案失败: {exc}"


# ============================================================================
# SearXNG 搜索（免费 - 开源聚合引擎）
# ============================================================================

async def searxng_search(query: str) -> str:
    """SearXNG 搜索 - 开源聚合搜索引擎，免费。

    聚合 Google、Bing、DuckDuckGo、Wikipedia 等多个引擎。
    """
    # 使用公共 SearXNG 实例
    url = "https://searx.be/search"
    params = {
        "q": query,
        "format": "json",
        "engines": "google,bing,duckduckgo,wikipedia",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if not results:
            return "SearXNG 搜索未找到结果"

        output = []
        for item in results[:5]:
            output.append(
                f"{item.get('title', '无标题')}\n"
                f"引擎: {item.get('engine', '')}\n"
                f"链接: {item.get('url', '')}\n"
                f"摘要: {item.get('content', '无摘要')}"
            )

        return "\n\n".join(output)

    except Exception as exc:
        logger.warning("[searxng_search] failed: query=%r error=%s", query, exc)
        return f"SearXNG 搜索失败: {exc}"


# ============================================================================
# Wikipedia 搜索（免费）
# ============================================================================

async def wikipedia_search(query: str) -> str:
    """Wikipedia API 搜索 - 免费，无需 API Key。

    支持英文和中文 Wikipedia。
    """
    url_en = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": 3,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 英文搜索
            response_en = await client.get(url_en, params=params)
            data_en = response_en.json()

            # 中文搜索
            url_zh = "https://zh.wikipedia.org/w/api.php"
            response_zh = await client.get(url_zh, params=params)
            data_zh = response_zh.json()

        results = []

        # 处理英文结果
        for item in data_en.get("query", {}).get("search", []):
            title = item.get("title", "")
            results.append(
                f"[英文百科] {title}\n"
                f"链接: https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            )

        # 处理中文结果
        for item in data_zh.get("query", {}).get("search", []):
            title = item.get("title", "")
            results.append(
                f"[中文百科] {title}\n"
                f"链接: https://zh.wikipedia.org/wiki/{title}"
            )

        if not results:
            return "Wikipedia 搜索未找到结果"

        return "\n\n".join(results)

    except Exception as exc:
        logger.warning("[wikipedia_search] failed: query=%r error=%s", query, exc)
        return f"Wikipedia 搜索失败: {exc}"


# ============================================================================
# ArXiv 搜索（免费 - 学术论文）
# ============================================================================

async def arxiv_search(query: str) -> str:
    """ArXiv 学术论文搜索 - 免费。

    用于搜索学术论文、研究资料。
    """
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": 3,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            root = ET.fromstring(response.text)

        entries = root.findall("entry")
        if not entries:
            return "ArXiv 搜索未找到结果"

        results = []
        for entry in entries:
            title = entry.find("title").text.strip() if entry.find("title") else ""
            summary = entry.find("summary").text.strip()[:150] if entry.find("summary") else ""
            link = entry.find("id").text if entry.find("id") else ""

            results.append(
                f"[学术论文] {title}\n"
                f"摘要: {summary}\n"
                f"链接: {link}"
            )

        return "\n\n".join(results)

    except Exception as exc:
        logger.warning("[arxiv_search] failed: query=%r error=%s", query, exc)
        return f"ArXiv 搜索失败: {exc}"


# ============================================================================
# GitHub 搜索（免费）
# ============================================================================

async def github_search(query: str) -> str:
    """GitHub 仓库搜索 - 免费（无 Token 有速率限制）。

    用于搜索代码仓库、开源项目。
    """
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "per_page": 3, "sort": "relevance"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        items = data.get("items", [])
        if not items:
            return "GitHub 搜索未找到结果"

        results = []
        for item in items:
            results.append(
                f"[代码仓库] {item.get('full_name', '')}\n"
                f"描述: {item.get('description', '')}\n"
                f"Stars: {item.get('stargazers_count', 0)}\n"
                f"链接: {item.get('html_url', '')}"
            )

        return "\n\n".join(results)

    except Exception as exc:
        logger.warning("[github_search] failed: query=%r error=%s", query, exc)
        return f"GitHub 搜索失败: {exc}"


# ============================================================================
# StackOverflow 搜索（免费）
# ============================================================================

async def stackoverflow_search(query: str) -> str:
    """StackOverflow 技术问答搜索 - 免费。

    用于搜索技术问题、编程解答。
    """
    url = "https://api.stackexchange.com/2.3/search"
    params = {
        "order": "desc",
        "sort": "relevance",
        "intitle": query,
        "site": "stackoverflow",
        "pagesize": 3,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        items = data.get("items", [])
        if not items:
            return "StackOverflow 搜索未找到结果"

        results = []
        for item in items:
            results.append(
                f"[技术问答] {item.get('title', '')}\n"
                f"得分: {item.get('score', 0)} | 回答数: {item.get('answer_count', 0)}\n"
                f"链接: {item.get('link', '')}"
            )

        return "\n\n".join(results)

    except Exception as exc:
        logger.warning("[stackoverflow_search] failed: query=%r error=%s", query, exc)
        return f"StackOverflow 搜索失败: {exc}"


# ============================================================================
# 已配置的搜索工具（Tavily 和 Spark）
# ============================================================================

async def tavily_search(query: str) -> str:
    """Tavily AI 优化搜索 - 已配置 API Key。

    提供高质量、结构化的搜索结果。
    """
    from app.config import TAVILY_KEY
    from tavily import AsyncTavilyClient

    if not TAVILY_KEY:
        return "Tavily 搜索不可用: 未配置 API Key"

    try:
        client = AsyncTavilyClient(api_key=TAVILY_KEY)
        response = await client.search(query, max_results=5)

        results = response.get("results", [])
        if not results:
            return "Tavily 搜索未找到结果"

        output = []
        for item in results:
            output.append(
                f"{item.get('title', '无标题')}\n"
                f"链接: {item.get('url', '')}\n"
                f"摘要: {item.get('content', '无摘要')}"
            )

        return "\n\n".join(output)

    except Exception as exc:
        logger.warning("[tavily_search] failed: query=%r error=%s", query, exc)
        return f"Tavily 搜索失败: {exc}"


async def spark_search(query: str) -> str:
    """讯飞星火中文语义搜索 - 已配置 API Key。

    中文优化，支持语义重排序。
    """
    from app.config import SPARK_SEARCH_KEY

    if not SPARK_SEARCH_KEY:
        return "讯飞搜索不可用: 未配置 API Key"

    url = "https://search-api-open.cn-huabei-1.xf-yun.com/v2/search"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {SPARK_SEARCH_KEY}"},
                json={"query": query, "top_k": 5}
            )
            data = response.json()

        results = data.get("results", [])
        if not results:
            return "讯飞搜索未找到结果"

        output = []
        for item in results:
            output.append(
                f"{item.get('title', '无标题')}\n"
                f"链接: {item.get('url', '')}\n"
                f"摘要: {item.get('snippet', '无摘要')}"
            )

        return "\n\n".join(output)

    except Exception as exc:
        logger.warning("[spark_search] failed: query=%r error=%s", query, exc)
        return f"讯飞搜索失败: {exc}"


# ============================================================================
# 内容抓取工具
# ============================================================================

class CurlArgs(BaseModel):
    """curl 参数。"""
    url: str = Field(description="URL to fetch")
    max_time: int = Field(default=15, description="Max time in seconds")


async def curl_fetch(url: str, max_time: int = 15) -> str:
    """curl 命令抓取 - 免费。

    使用 curl 命令抓取网页内容，支持重定向。
    """
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["curl", "-s", "-L", f"--max-time={max_time}", url],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return f"curl 失败: 返回码 {result.returncode}"

        return result.stdout

    except Exception as exc:
        logger.warning("[curl_fetch] failed: url=%r error=%s", url, exc)
        return f"curl 异常: {exc}"


class WebFetchArgs(BaseModel):
    """webfetch 参数。"""
    url: str = Field(description="URL to fetch")


async def webfetch(url: str) -> str:
    """HTTP 抓取 - 免费。

    简单的 HTTP GET 请求抓取网页内容。
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    except Exception as exc:
        logger.warning("[webfetch] failed: url=%r error=%s", url, exc)
        return f"webfetch 失败: {exc}"