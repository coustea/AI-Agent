"""Retrieval support compatibility shim.

This module re-exports ranking_support functionality from app.rag.optimization.ranking_support
for backward compatibility with existing imports.

New code should import directly from:
    from app.rag.optimization.ranking_support import merge_ranked_results, build_sparse_search_text
"""
from __future__ import annotations

# Re-export all public functions
from app.rag.optimization.ranking_support import (
    build_local_context_summary,
    build_sparse_search_text,
    definition_query_bonus,
    extract_concept_terms,
    infer_chunk_type,
    is_definition_query,
    is_low_value_sparse_chunk,
    low_value_chunk_penalty,
    merge_ranked_results,
    rrf_score,
)

__all__ = [
    "build_local_context_summary",
    "build_sparse_search_text",
    "definition_query_bonus",
    "extract_concept_terms",
    "infer_chunk_type",
    "is_definition_query",
    "is_low_value_sparse_chunk",
    "low_value_chunk_penalty",
    "merge_ranked_results",
    "rrf_score",
]