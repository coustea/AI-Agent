"""Reranker compatibility shim.

This module re-exports reranker functionality from app.rag.optimization.reranker
for backward compatibility with existing imports.

New code should import directly from:
    from app.rag.optimization.reranker import rerank_candidates, is_rerank_enabled
"""
from __future__ import annotations

# Re-export all public functions
from app.rag.optimization.reranker import (
    get_cross_encoder,
    is_rerank_enabled,
    rerank_candidates,
)

__all__ = [
    "get_cross_encoder",
    "is_rerank_enabled",
    "rerank_candidates",
]