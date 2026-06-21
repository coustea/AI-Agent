"""搜索工具封装 — 按用途分类的独立搜索工具。

工具分类：
  - duckduckgo_search: 通用网页搜索（DDGS SDK）
  - duckduckgo_instant_answer: 即时答案/定义/百科摘要（直接 API）
  - tavily_search: AI 优化搜索（需要 API key）
  - spark_search: 中文语义搜索（讯飞）
  - academic_search: 学术搜索（未来扩展）
  - news_search: 新闻搜索（未来扩展）

每个工具独立，agent 根据问题类型选择合适的搜索工具。
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import urllib.parse

import httpx
from ddgs import DDGS
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient

from app.config import TAVILY_KEY, SPARK_SEARCH_KEY
from app.infra.logging import get_logger

logger = get_logger(__name__)


class SearchQueryArgs(BaseModel):
    query: str = Field(description="Search query.")

# DuckDuckGo 搜索客户端 — 通用网页搜索
_duckduckgo_search_client = DDGS()

# Tavily SDK 客户端 — AI 优化搜索（需要 API key）
_tavily_search_client = AsyncTavilyClient(api_key=TAVILY_KEY) if (TAVILY_KEY or "").strip() else None


def _redact_url_query_secrets(text: object) -> str:
    """脱敏异常文本中的 URL 查询参数，避免 api key 进入日志或响应。"""
    raw = str(text)
    if not any(marker in raw.lower() for marker in ("api_key=", "key=", "token=")):
        return raw
    return re.sub(r"(?i)(api_key|key|token)=([^&\s]+)", r"\1=[REDACTED]", raw)


# ---------------------------------------------------------------------------
# 通用网页搜索工具
# ---------------------------------------------------------------------------


async def duckduckgo_search(query: str) -> str:
    """通用网页搜索工具，返回搜索结果摘要。

    适用场景：需要查找网页、文章、教程、博客等通用内容。
    使用 DuckDuckGo 搜索引擎，免费无需 API key。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果文本摘要
    """
    try:
        rows = await asyncio.to_thread(_duckduckgo_search_client.text, query, max_results=5)
        if not rows:
            return "未找到相关搜索结果"
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
    """即时答案搜索工具，返回定义、摘要、百科信息。

    适用场景：
      - 查询术语定义（如 "什么是机器学习"）
      - 获取百科摘要（如 "Python 语言介绍"）
      - 快速答案（如 "Python 作者是谁"）

    使用 DuckDuckGo Instant Answer API，返回结构化的即时答案。

    Args:
        query: 查询关键词（术语、概念、人物等）

    Returns:
        即时答案、定义和相关主题
    """
    if not query or not query.strip():
        return "查询不能为空"

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
            return f"DuckDuckGo API 请求失败: curl 返回 {result.returncode}"

        data = json.loads(result.stdout)
        output_parts = []

        # 提取摘要
        abstract = data.get("Abstract", "")
        abstract_source = data.get("AbstractSource", "")
        abstract_url = data.get("AbstractURL", "")
        if abstract:
            source_info = f" (来源: {abstract_source})" if abstract_source else ""
            output_parts.append(f"摘要{source_info}:\n{abstract}")
            if abstract_url:
                output_parts.append(f"详细链接: {abstract_url}")

        # 提取即时答案
        answer = data.get("Answer", "")
        if answer:
            output_parts.append(f"答案:\n{answer}")

        # 提取定义
        definition = data.get("Definition", "")
        definition_source = data.get("DefinitionSource", "")
        if definition:
            source_info = f" (来源: {definition_source})" if definition_source else ""
            output_parts.append(f"定义{source_info}:\n{definition}")

        # 提取相关主题（最多 5 个）
        related_topics = data.get("RelatedTopics", [])[:5]
        if related_topics:
            topics_text = []
            for topic in related_topics:
                if isinstance(topic, dict):
                    text = topic.get("Text", "")
                    first_url = topic.get("FirstURL", "")
                    if text:
                        topic_entry = f"  - {text}"
                        if first_url:
                            topic_entry += f"\n    链接: {first_url}"
                        topics_text.append(topic_entry)
            if topics_text:
                output_parts.append("相关主题:\n" + "\n".join(topics_text))

        if not output_parts:
            return f"未找到关于 '{query}' 的即时答案"

        return "\n\n".join(output_parts)

    except json.JSONDecodeError as exc:
        logger.warning("[duckduckgo_instant_answer] JSON 解析失败: query=%r error=%s", query, exc)
        return "DuckDuckGo API 响应格式错误"
    except subprocess.TimeoutExpired:
        logger.warning("[duckduckgo_instant_answer] 超时: query=%r", query)
        return "DuckDuckGo API 请求超时"
    except Exception as exc:
        error = _redact_url_query_secrets(exc)
        logger.warning("[duckduckgo_instant_answer] failed: query=%r error=%s", query, error)
        return f"DuckDuckGo API 搜索失败: {error}"


# ---------------------------------------------------------------------------
# AI 优化搜索工具
# ---------------------------------------------------------------------------


async def tavily_search(query: str) -> str:
    """AI 优化搜索工具，返回高质量结构化结果。

    适用场景：
      - 需要高质量、相关性强的搜索结果
      - 研究性问题的深度搜索
      - 需要结构化答案的复杂查询

    使用 Tavily 搜索引擎（AI 优化），需要配置 TAVILY_KEY。

    Args:
        query: 搜索关键词

    Returns:
        结构化搜索结果摘要
    """
    if _tavily_search_client is None:
        return "Tavily 搜索不可用: 未配置 TAVILY_KEY"

    try:
        response = await _tavily_search_client.search(query, max_results=5)
        rows = response.get("results") or []
        if not rows:
            return "未找到相关搜索结果"
        result = "\n\n".join(
            f"{index}. {row.get('title') or '无标题'}\n"
            f"   链接: {row.get('url') or ''}\n"
            f"   摘要: {row.get('content') or '无摘要'}"
            for index, row in enumerate(rows[:5], 1)
        )
        logger.info("[tavily_search] query=%r result_preview=%r", query, result[:300])
        return result
    except Exception as exc:
        logger.warning("[tavily_search] failed: query=%r error=%s", query, exc)
        return f"Tavily 搜索失败: {exc}"


# ---------------------------------------------------------------------------
# 中文语义搜索工具
# ---------------------------------------------------------------------------


async def spark_search(query: str) -> str:
    """中文语义搜索工具，返回中文优化的搜索结果。

    适用场景：
      - 中文内容的深度搜索
      - 需要语义理解而非关键词匹配
      - 中文教育、学术内容的检索

    使用讯飞开放平台搜索 API，支持语义重排序。

    Args:
        query: 搜索关键词（中文）

    Returns:
        中文语义搜索结果（最多 5 条）
    """
    if not (SPARK_SEARCH_KEY or "").strip():
        return "讯飞搜索不可用: 未配置 SPARK_SEARCH_KEY"

    url = "https://search-api-open.cn-huabei-1.xf-yun.com/v2/search"
    if not query or not query.strip():
        return "查询不能为空"

    payload = {
        "search_params": {
            "query": query,
            "limit": 10,
            "enhance": {
                "open_rerank": True,
                "open_full_text": False,
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {SPARK_SEARCH_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=payload)

        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            return f"讯飞搜索失败: {data}"

        documents = data.get("data", {}).get("search_results", {}).get("documents", [])

        if not documents:
            return "未找到相关搜索结果"

        summaries = []
        for i, doc in enumerate(documents[:5], 1):
            title = doc.get("name", "无标题")
            link = doc.get("url", "")
            snippet = doc.get("summary", "") or doc.get("content", "无摘要")
            summaries.append(f"{i}. {title}\n   链接: {link}\n   摘要: {snippet}")

        return "\n\n".join(summaries)

    except Exception as exc:
        error = _redact_url_query_secrets(exc)
        logger.warning("[spark_search] failed: query=%r error=%s", query, error)
        return f"讯飞搜索失败: {error}"
