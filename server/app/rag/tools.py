"""Tool boundary for RAG-backed knowledge retrieval."""

from __future__ import annotations

from app.infra.tool_excute import Tool
from app.rag.knowledge import SearchKnowledgeBaseArgs, make_search_knowledge_base


def as_tool() -> Tool:
    """Return the platform Tool object for local textbook knowledge search."""
    return Tool(
        "search_knowledge_base",
        (
            "Search the local textbook/course/408 concept knowledge base. "
            "Use for CS textbook definitions, principles, mechanisms, comparisons, processes, and exam-style concepts; "
            "not for code debugging, project implementation, study planning, chat, or current/latest information."
        ),
        SearchKnowledgeBaseArgs,
        make_search_knowledge_base(),
    )


__all__ = ["SearchKnowledgeBaseArgs", "as_tool", "make_search_knowledge_base"]
