from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import (
    KB_PROFILE_BALANCED_MULTIPLIER,
    KB_PROFILE_CONCEPTUAL_DENSE_MULTIPLIER,
    KB_PROFILE_EXACT_SPARSE_MULTIPLIER,
    KB_PROFILE_MIN_TOP_K,
)


_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9+#._-]{2,}")
_CONCEPTUAL_MARKERS: tuple[str, ...] = (
    "什么",
    "为什么",
    "如何",
    "原理",
    "区别",
    "机制",
    "怎么",
    "compare",
    "difference",
    "explain",
    "why",
    "how",
)


@dataclass(frozen=True)
class RetrievalProfile:
    name: str
    dense_k: int
    sparse_k: int
    enable_rewrite: bool = True


def _is_exact_query(query: str) -> bool:
    normalized = (query or "").strip()
    if not normalized:
        return False
    if " " in normalized:
        return False
    return bool(_ASCII_TERM_RE.fullmatch(normalized))


def _is_conceptual_query(query: str) -> bool:
    normalized = (query or "").strip().casefold()
    if not normalized:
        return False
    return any(marker in normalized for marker in _CONCEPTUAL_MARKERS)


def resolve_retrieval_profile(query: str, *, top_k: int) -> RetrievalProfile:
    base_k = max(int(top_k or 0), KB_PROFILE_MIN_TOP_K)

    if _is_exact_query(query):
        return RetrievalProfile(
            name="exact",
            dense_k=base_k,
            sparse_k=base_k * KB_PROFILE_EXACT_SPARSE_MULTIPLIER,
            enable_rewrite=False,
        )

    if _is_conceptual_query(query):
        return RetrievalProfile(
            name="conceptual",
            dense_k=base_k * KB_PROFILE_CONCEPTUAL_DENSE_MULTIPLIER,
            sparse_k=base_k,
            enable_rewrite=True,
        )

    return RetrievalProfile(
        name="balanced",
        dense_k=base_k * KB_PROFILE_BALANCED_MULTIPLIER,
        sparse_k=base_k * KB_PROFILE_BALANCED_MULTIPLIER,
        enable_rewrite=True,
    )
