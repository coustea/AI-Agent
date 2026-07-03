"""RAG retrieval pipeline package.

This package contains the core retrieval pipeline components:
- cache: Caching and index management
- dense: Dense retrieval (vector similarity)
- sparse: Sparse retrieval (BM25)
- fusion: Result fusion and ranking
- context_formatter: Context formatting for LLM
- retriever: Main retrieval orchestrator

The main entry point is still app.rag.knowledge for backward compatibility.
New code can import from app.rag.pipeline for more granular control.

Pipeline flow:
1. Query routing (optimization/query_router) determines sources
2. Dense retrieval (pipeline/dense) for semantic matching
3. Sparse retrieval (pipeline/sparse) for keyword matching
4. Result fusion (pipeline/fusion) for merging and ranking
5. Context formatting (pipeline/context_formatter) for LLM input
"""
from __future__ import annotations

# Import from knowledge.py for backward compatibility
# New pipeline modules will gradually take over these functions
from app.rag.knowledge import (
    retrieve_knowledge,
    retrieve_dense_knowledge,
    retrieve_sparse_knowledge,
    merge_ranked_results,
    format_knowledge_context,
    aformat_knowledge_context,
    search_knowledge_base,
    make_search_knowledge_base,
    BM25Index,
    build_bm25_index,
    rank_with_bm25,
    clear_retrieval_caches,
)

__all__ = [
    "retrieve_knowledge",
    "retrieve_dense_knowledge",
    "retrieve_sparse_knowledge",
    "merge_ranked_results",
    "format_knowledge_context",
    "aformat_knowledge_context",
    "search_knowledge_base",
    "make_search_knowledge_base",
    "BM25Index",
    "build_bm25_index",
    "rank_with_bm25",
    "clear_retrieval_caches",
]