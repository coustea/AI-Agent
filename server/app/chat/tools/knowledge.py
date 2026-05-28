"""Local Chroma knowledge-base retrieval helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from app.config import (
    KB_COLLECTION,
    KB_DIR,
    KB_EMBED_MODEL,
    KB_ENABLED,
    KB_OLLAMA_BASE_URL,
    KB_TOP_K,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma | None:
    if not KB_ENABLED:
        logger.info("[knowledge] local KB disabled by config")
        return None

    db_dir = Path(KB_DIR)
    if not db_dir.exists():
        logger.warning("[knowledge] KB dir does not exist: %s", db_dir)
        return None

    try:
        embeddings = OllamaEmbeddings(
            model=KB_EMBED_MODEL,
            base_url=KB_OLLAMA_BASE_URL,
        )
        return Chroma(
            collection_name=KB_COLLECTION,
            embedding_function=embeddings,
            persist_directory=str(db_dir),
        )
    except Exception:
        logger.exception("[knowledge] failed to open KB vectorstore")
        return None


def retrieve_knowledge(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    vectorstore = _get_vectorstore()
    normalized_query = (query or "").strip()
    if vectorstore is None or not normalized_query:
        return []

    try:
        rows = vectorstore.similarity_search_with_score(
            normalized_query,
            k=top_k or KB_TOP_K,
        )
    except Exception:
        logger.exception("[knowledge] query failed")
        return []

    items: list[dict[str, Any]] = []
    for idx, (doc, score) in enumerate(rows, 1):
        items.append(
            {
                "rank": idx,
                "distance": float(score),
                "metadata": dict(doc.metadata or {}),
                "text": str(doc.page_content or "").strip(),
            }
        )
    return items


def format_knowledge_context(query: str, *, top_k: int | None = None) -> tuple[str, list[dict[str, Any]]]:
    rows = retrieve_knowledge(query, top_k=top_k)
    if not rows:
        return "", []

    parts: list[str] = []
    for item in rows:
        metadata = item.get("metadata") or {}
        title = metadata.get("book_title") or metadata.get("source") or metadata.get("file_name") or "未知来源"
        heading = metadata.get("heading_path") or metadata.get("section") or metadata.get("chapter") or ""
        distance = item.get("distance")
        score_text = f"{distance:.4f}" if isinstance(distance, (int, float)) else "NA"
        snippet = str(item.get("text") or "").replace("\r", " ").replace("\n", " ").strip()
        if len(snippet) > 700:
            snippet = snippet[:700].rstrip() + "..."
        header = f"[{item.get('rank', '?')}] 来源: {title}"
        if heading:
            header += f" | 位置: {heading}"
        header += f" | 距离: {score_text}"
        parts.append(f"{header}\n{snippet}")

    return "\n\n".join(parts), rows


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Search the local course knowledge base and return relevant textbook snippets."""
    context, rows = format_knowledge_context(query)
    if not rows:
        return "本地知识库没有检索到相关内容，或知识库尚未正确加载。"
    return context
