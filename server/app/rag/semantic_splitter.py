"""Semantic splitter compatibility shim.

This module re-exports SemanticSplitter from app.rag.indexing.semantic_splitter
for backward compatibility with existing imports.

New code should import directly from:
    from app.rag.indexing.semantic_splitter import SemanticSplitter, HybridSplitter
"""
from __future__ import annotations

# Re-export the main classes and utility functions
from app.rag.indexing.semantic_splitter import (
    HybridSplitter,
    SemanticSplitter,
    create_splitter,
)

__all__ = [
    "SemanticSplitter",
    "HybridSplitter",
    "create_splitter",
]