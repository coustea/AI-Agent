"""TutorAgent 工具构建和执行辅助函数。

从 nodes.py 中提取，保持节点文件只关注编排逻辑。
"""

from __future__ import annotations

from typing import Any

from app.chat.tools.knowledge import SearchKnowledgeBaseArgs, make_search_knowledge_base
from app.chat.tools.memory import (
    LONG_TERM_MEMORY_CATEGORY_ALIASES,
    GetLongTermMemoryArgs,
    make_get_long_term_memory,
)
from app.chat.tools.profile import GetLearnerProfileArgs, make_get_learner_profile
from app.chat.tools.search import (
    SearchQueryArgs,
    duckduckgo_instant_answer,
    duckduckgo_search,
    spark_search,
    tavily_search,
)
from app.chat.tools.web_research import (
    ExtractWebLinksArgs,
    FindInWebPageArgs,
    OpenWebPageArgs,
    ReadWebPdfArgs,
    WebResearchSession,
)
from app.chat.schemas import TutorTurnContext
from app.infra.tool_excute import Tool
from app.infra.logging import get_logger

logger = get_logger(__name__)

WEB_RESEARCH_TOOL_NAMES = (
    "duckduckgo_search",
    "duckduckgo_instant_answer",
    "tavily_search",
    "spark_search",
    "open_web_page",
    "find_in_web_page",
    "extract_web_links",
    "read_web_pdf",
)

TOOL_EVIDENCE_TYPES: dict[str, str] = {
    "get_learner_profile": "learner_profile",
    "get_long_term_memory": "long_term_memory",
    "search_knowledge_base": "knowledge_base",
    **{name: "web_search" for name in WEB_RESEARCH_TOOL_NAMES},
}


def _result_handler(handler, tool_name: str):
    """包装工具处理器，保留原始结果结构。"""
    async def _wrapped(**kwargs: Any) -> Any:
        try:
            return await handler(**kwargs)
        except Exception as exc:
            logger.warning("[%s] failed: error=%s", tool_name, exc)
            raise
    return _wrapped


def build_tutor_tools(request: TutorTurnContext) -> list[Tool]:
    """装配当前辅导请求可用的业务工具。"""
    web_session = WebResearchSession()
    return [
        Tool(
            "get_learner_profile",
            "Read learner profile when personalization, goals, preferences, or background matter.",
            GetLearnerProfileArgs,
            make_get_learner_profile(request),
        ),
        Tool(
            "get_long_term_memory",
            "Read durable learning memory for previous goals, preferences, weaknesses, strategies, or corrections.",
            GetLongTermMemoryArgs,
            make_get_long_term_memory(request),
        ),
        Tool(
            "search_knowledge_base",
            "Search local course knowledge base for definitions, concepts, textbook facts, and course material.",
            SearchKnowledgeBaseArgs,
            make_search_knowledge_base(),
        ),
        Tool(
            "duckduckgo_search",
            "General web search for articles, tutorials, blogs, and web content.",
            SearchQueryArgs,
            _result_handler(duckduckgo_search, "duckduckgo_search"),
        ),
        Tool(
            "duckduckgo_instant_answer",
            "Get instant answers, definitions, and encyclopedia summaries.",
            SearchQueryArgs,
            _result_handler(duckduckgo_instant_answer, "duckduckgo_instant_answer"),
        ),
        Tool(
            "tavily_search",
            "AI-optimized search with structured, relevance-ranked results.",
            SearchQueryArgs,
            _result_handler(tavily_search, "tavily_search"),
        ),
        Tool(
            "spark_search",
            "Chinese semantic search with reranking support.",
            SearchQueryArgs,
            _result_handler(spark_search, "spark_search"),
        ),
        Tool(
            "open_web_page",
            "Open and read a public web page selected from search results.",
            OpenWebPageArgs,
            _result_handler(web_session.open_page, "open_web_page"),
        ),
        Tool(
            "find_in_web_page",
            "Find an exact word or phrase inside an opened page.",
            FindInWebPageArgs,
            _result_handler(web_session.find_in_page, "find_in_web_page"),
        ),
        Tool(
            "extract_web_links",
            "List relevant links from an opened page.",
            ExtractWebLinksArgs,
            _result_handler(web_session.extract_links, "extract_web_links"),
        ),
        Tool(
            "read_web_pdf",
            "Read a public PDF and return page-aware excerpts.",
            ReadWebPdfArgs,
            _result_handler(web_session.read_pdf, "read_web_pdf"),
        ),
    ]
