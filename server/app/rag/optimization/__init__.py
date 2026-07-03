"""RAG optimization package.

This package contains modules for query optimization and result ranking:
- query_router: Query routing and source filtering
- query_rewrite: Query rewriting and expansion
- retrieval_profiles: Retrieval profile configuration
- ranking_support: Ranking and fusion utilities
- reranker: Result reranking

Query optimization pipeline:
1. query_router determines which knowledge sources to search
2. query_rewrite expands or rewrites the query for better retrieval
3. ranking_support provides ranking and fusion utilities
4. reranker re-ranks results for better relevance
"""
from __future__ import annotations

# Re-export commonly used functions and classes for convenience
from app.rag.optimization.query_router import (
    QueryRouteResult,
    route_query_sources,
)

from app.rag.optimization.query_rewrite import (
    compute_retrieval_confidence,
)

__all__ = [
    "QueryRouteResult",
    "route_query_sources",
    "compute_retrieval_confidence",
]