"""Pipeline cache and index management.

This module provides thin wrappers around knowledge.py cache functions.
The actual implementation lives in knowledge.py; this module exists for
organizational clarity and future pipeline decomposition.

During the refactor transition, all cache management stays in knowledge.py
to avoid breaking existing callers.
"""
from __future__ import annotations

from typing import Any

from app.config import KB_EMBED_MODEL, KB_OLLAMA_BASE_URL
from app.infra.logging import get_logger

logger = get_logger(__name__)


def get_rag_embeddings():
    """Get the RAG embeddings instance.

    Delegates to knowledge.py for backward compatibility.
    """
    from app.rag.knowledge import get_rag_embeddings as _get_embeddings
    return _get_embeddings()


def _get_cached_embedding(query: str) -> tuple[float, ...] | None:
    """Get cached embedding for a query.

    Delegates to knowledge.py embedding cache with circuit breaker.
    """
    # Import the actual implementation from knowledge.py
    from app.rag.knowledge import _get_cached_embedding
    return _get_cached_embedding(query)


def _get_vectorstore():
    """Get or create the Chroma vector store instance.

    Delegates to knowledge.py module-level cache.
    """
    from app.rag.knowledge import _get_vectorstore
    return _get_vectorstore()


def _get_sparse_corpus() -> list[dict[str, Any]]:
    """Load the sparse corpus from Chroma for BM25 indexing.

    Delegates to knowledge.py for paginated corpus loading.
    """
    from app.rag.knowledge import _get_sparse_corpus
    return _get_sparse_corpus()


def _get_bm25_index():
    """Get or create the BM25 index.

    Delegates to knowledge.py module-level cache.
    """
    from app.rag.knowledge import _get_bm25_index
    return _get_bm25_index()


def clear_retrieval_caches() -> None:
    """Clear all retrieval-related caches.

    Delegates to knowledge.py for comprehensive cache clearing.
    """
    from app.rag.knowledge import clear_retrieval_caches
    clear_retrieval_caches()


# Note: All cache state (_vectorstore, _sparse_corpus, _bm25_index, embedding cache)
# is managed in knowledge.py. This module is a thin shim for the pipeline package.