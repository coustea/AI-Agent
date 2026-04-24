"""ChatDoc 全局知识库检索工具。"""

from __future__ import annotations

import asyncio

from langchain_core.tools import tool

from app.infra.logging import get_logger
from app.knowledge_base.exceptions import ChatDocError
from app.knowledge_base.service import get_chatdoc_service
from app.tools.registry import register

logger = get_logger(__name__)


def _format_results(results: list[dict]) -> str:
    if not results:
        return (
            "全局计算机/AI 知识库当前没有可用资料或没有检索到相关内容。"
            "请告知主 TutorAgent 可以先基于自身知识进行教学回答，并提醒用户后续补充课程资料。"
        )

    lines = ["全局计算机/AI 知识库检索结果："]
    for idx, item in enumerate(results, start=1):
        content = str(item.get("content", "")).strip()
        score = item.get("score", 0)
        chunk_id = str(item.get("chunk_id", "")).strip()
        lines.append(f"{idx}. score={score} chunk_id={chunk_id}\n{content}")
    return "\n\n".join(lines)


async def _search_global_knowledge(query: str) -> str:
    service = get_chatdoc_service()
    if not service.enabled:
        return (
            "ChatDoc 未启用，无法检索全局计算机/AI 知识库。"
            "请告知主 TutorAgent 使用自身知识回答，并说明知识库暂不可用。"
        )

    try:
        results = await service.search_global(query=query, top_k=5)
    except ChatDocError as exc:
        logger.warning("[chatdoc_rag_search] ChatDoc failed: query=%r error=%s", query, exc)
        return f"全局知识库检索失败: {exc.message}。请使用自身知识继续回答。"
    except Exception as exc:
        logger.warning("[chatdoc_rag_search] failed: query=%r error=%s", query, exc)
        return f"全局知识库检索失败: {exc}。请使用自身知识继续回答。"

    logger.info("[chatdoc_rag_search] query=%r hits=%d", query, len(results))
    return _format_results(results)


@tool("chatdoc_rag_search")
def chatdoc_rag_search(query: str) -> str:
    """检索全局计算机科学与人工智能学习知识库，返回与问题相关的课程资料片段。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_search_global_knowledge(query))
    return (
        "当前运行环境已有事件循环，无法同步执行 ChatDoc 检索。"
        "请告知主 TutorAgent 使用自身知识回答，并说明知识库暂不可用。"
    )


register(chatdoc_rag_search)
