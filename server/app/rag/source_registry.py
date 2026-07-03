"""Source registry compatibility shim.

This module re-exports source_registry functionality from app.rag.config.source_registry
for backward compatibility with existing imports.

New code should import directly from:
    from app.rag.config.source_registry import extract_canonical_source_identity, matches_source_filter
"""
from __future__ import annotations

# Re-export all public functions
from app.rag.config.source_registry import (
    extract_canonical_source_identity,
    extract_source_identities,
    get_course_primary_source,
    get_source_domain,
    get_source_priority,
    get_source_trust_tier,
    load_source_registry,
    load_source_registry_alias_map,
    matches_source_filter,
    normalize_book_title,
    normalize_source_identity_text,
    resolve_to_canonical_source,
)

__all__ = [
    "extract_canonical_source_identity",
    "extract_source_identities",
    "get_course_primary_source",
    "get_source_domain",
    "get_source_priority",
    "get_source_trust_tier",
    "load_source_registry",
    "load_source_registry_alias_map",
    "matches_source_filter",
    "normalize_book_title",
    "normalize_source_identity_text",
    "resolve_to_canonical_source",
]