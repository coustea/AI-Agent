"""Retrieval profiles compatibility shim.

This module re-exports retrieval_profiles functionality from app.rag.optimization.retrieval_profiles
for backward compatibility with existing imports.

New code should import directly from:
    from app.rag.optimization.retrieval_profiles import RetrievalProfile, resolve_retrieval_profile
"""
from __future__ import annotations

# Re-export all public classes and functions
from app.rag.optimization.retrieval_profiles import (
    RetrievalProfile,
    resolve_retrieval_profile,
)

__all__ = [
    "RetrievalProfile",
    "resolve_retrieval_profile",
]