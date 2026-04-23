"""Pure policies for long-term memory quality, merge, and ranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from app.memory.helpers import normalize_text

_TERM_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)

_SOURCE_WEIGHTS: dict[str, float] = {
    "fact_agent": 1.0,
    "conversation": 0.94,
}

_INITIAL_IMPORTANCE_BY_TYPE: dict[str, float] = {
    "preference": 0.66,
    "goal": 0.7,
    "weakness": 0.62,
    "fact": 0.58,
    "background": 0.54,
}

_MIN_OVERLAP_BY_TYPE: dict[str, float] = {
    "preference": 0.4,
    "goal": 0.4,
    "weakness": 0.4,
    "fact": 0.45,
    "background": 0.45,
}


@dataclass(frozen=True, slots=True)
class MergeDecision:
    candidate: Any
    match_score: float
    relation: str


def normalize_memory_text(content: str | None) -> str:
    return normalize_text(content or "")


def clamp_importance(value: float | None, *, default: float = 0.5) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def source_weight(source: str | None) -> float:
    if not source:
        return 1.0
    return _SOURCE_WEIGHTS.get(source.strip().lower(), 0.96)


def initial_fact_importance(memory_type: str, source: str | None = "fact_agent") -> float:
    base = _INITIAL_IMPORTANCE_BY_TYPE.get((memory_type or "").strip().lower(), 0.55)
    return clamp_importance(base * source_weight(source))


def weight_importance_for_source(importance: float | None, source: str | None) -> float:
    base = clamp_importance(importance)
    return clamp_importance(base * source_weight(source))


def _extract_terms(content: str | None) -> set[str]:
    normalized = normalize_memory_text(content)
    if not normalized:
        return set()

    terms: set[str] = set()
    for chunk in _TERM_PATTERN.findall(normalized):
        if not chunk:
            continue
        if chunk.isascii():
            terms.add(chunk)
            continue
        if len(chunk) == 1:
            terms.add(chunk)
            continue
        terms.add(chunk)
        terms.update(chunk[index : index + 2] for index in range(len(chunk) - 1))
    return terms


def content_information_score(content: str | None) -> float:
    normalized = normalize_memory_text(content)
    if not normalized:
        return 0.0
    terms = _extract_terms(normalized)
    alpha_bonus = sum(1 for char in normalized if char.isalpha())
    digit_bonus = sum(1 for char in normalized if char.isdigit())
    return float(len(normalized) + len(terms) * 4 + alpha_bonus * 0.5 + digit_bonus)


def choose_more_informative_content(existing_content: str | None, new_content: str | None) -> str:
    existing = existing_content or ""
    incoming = new_content or ""
    if content_information_score(incoming) > content_information_score(existing):
        return incoming
    return existing


def memory_overlap_score(new_text: str | None, existing_text: str | None) -> float:
    normalized_new = normalize_memory_text(new_text)
    normalized_existing = normalize_memory_text(existing_text)
    if not normalized_new or not normalized_existing:
        return 0.0
    if normalized_new == normalized_existing:
        return 1.0

    new_terms = _extract_terms(normalized_new)
    existing_terms = _extract_terms(normalized_existing)
    if not new_terms or not existing_terms:
        return 0.0

    intersection = new_terms & existing_terms
    union = new_terms | existing_terms
    return len(intersection) / len(union)


def classify_merge_relation(memory_type: str, new_text: str | None, existing_text: str | None) -> tuple[str, float]:
    normalized_new = normalize_memory_text(new_text)
    normalized_existing = normalize_memory_text(existing_text)
    if not normalized_new or not normalized_existing:
        return "none", 0.0
    if normalized_new == normalized_existing:
        return "exact", 1.0
    if normalized_new in normalized_existing or normalized_existing in normalized_new:
        return "containment", 0.95

    overlap = memory_overlap_score(normalized_new, normalized_existing)
    threshold = _MIN_OVERLAP_BY_TYPE.get((memory_type or "").strip().lower(), 0.55)
    if overlap >= threshold:
        return "overlap", 0.7 + overlap * 0.25
    return "none", 0.0


def score_merge_candidate(memory_type: str, new_text: str | None, candidate: Any) -> MergeDecision | None:
    relation, relation_score = classify_merge_relation(memory_type, new_text, getattr(candidate, "content", None))
    if relation_score <= 0:
        return None

    candidate_importance = clamp_importance(getattr(candidate, "importance", None))
    evidence_count = max(1, int(getattr(candidate, "evidence_count", 1) or 1))
    last_seen_at = getattr(candidate, "last_seen_at", None) or getattr(candidate, "created_at", None)
    recency_score = last_seen_at.timestamp() if isinstance(last_seen_at, datetime) else 0.0
    tiebreak_score = candidate_importance * 0.05 + min(evidence_count, 10) * 0.03 + recency_score / 1_000_000_000_000
    return MergeDecision(candidate=candidate, match_score=relation_score + tiebreak_score, relation=relation)


def rank_merge_candidates(memory_type: str, new_text: str | None, candidates: Iterable[Any]) -> list[MergeDecision]:
    ranked = [decision for candidate in candidates if (decision := score_merge_candidate(memory_type, new_text, candidate))]
    ranked.sort(
        key=lambda item: (
            item.match_score,
            clamp_importance(getattr(item.candidate, "importance", None)),
            max(1, int(getattr(item.candidate, "evidence_count", 1) or 1)),
            (getattr(item.candidate, "last_seen_at", None) or getattr(item.candidate, "created_at", None) or datetime.min),
            len(normalize_memory_text(getattr(item.candidate, "content", None))),
        ),
        reverse=True,
    )
    return ranked


def bump_importance(
    importance: float | None,
    *,
    source: str | None = None,
    evidence_count: int = 1,
    match_score: float = 0.0,
) -> float:
    base = weight_importance_for_source(importance, source)
    evidence_bonus = min(max(evidence_count - 1, 0), 6) * 0.04
    match_bonus = max(0.0, min(1.0, match_score)) * 0.08
    return clamp_importance(base + evidence_bonus + match_bonus)


def rank_context_memory(memory: Any) -> tuple[float, int, datetime]:
    importance = clamp_importance(getattr(memory, "importance", None))
    evidence_count = max(1, int(getattr(memory, "evidence_count", 1) or 1))
    quality = (
        importance * source_weight(getattr(memory, "source", None))
        + min(max(evidence_count - 1, 0), 6) * 0.06
    )
    last_seen_at = getattr(memory, "last_seen_at", None) or getattr(memory, "created_at", None) or datetime.min
    return quality, evidence_count, last_seen_at
