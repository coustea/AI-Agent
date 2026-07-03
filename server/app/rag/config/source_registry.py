from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


NOISE_TERMS: tuple[str, ...] = ("z-library.sk", "1lib.sk", "z-lib.sk")
SOURCE_IDENTITY_KEYS: tuple[str, ...] = (
    "canonical_source_id",
    "book_name",
    "source_stem",
    "book_title",
    "source",
    "file_name",
)


def normalize_book_title(source: str) -> str:
    title = source
    for term in NOISE_TERMS:
        title = title.replace(term, "")
    title = re.sub(r"\(\s*,?\s*\)", "", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip(" ()")


def normalize_source_identity_text(value: Any) -> str:
    text = normalize_book_title(str(value or ""))
    text = text.casefold().strip()
    if not text:
        return ""
    return "".join(ch for ch in text if ch.isalnum())


def extract_source_identities(metadata: dict[str, Any]) -> tuple[str, ...]:
    identities: list[str] = []
    seen: set[str] = set()
    for key in SOURCE_IDENTITY_KEYS:
        normalized = normalize_source_identity_text(metadata.get(key))
        if normalized and normalized not in seen:
            identities.append(normalized)
            seen.add(normalized)
    return tuple(identities)


def extract_canonical_source_identity(metadata: dict[str, Any]) -> str:
    identities = extract_source_identities(metadata)
    return identities[0] if identities else ""


def matches_source_filter(
    metadata: dict[str, Any],
    source_filter: tuple[str, ...] | None,
    *,
    alias_map: dict[str, str] | None = None,
) -> bool:
    if not source_filter:
        return True

    candidate_identities = extract_source_identities(metadata)
    if not candidate_identities:
        return False

    resolved_alias_map = alias_map if alias_map is not None else load_source_registry_alias_map()
    expected_identities: list[str] = []
    seen_expected: set[str] = set()
    for item in source_filter:
        normalized = normalize_source_identity_text(item)
        if not normalized:
            continue
        resolved_canonical = normalize_source_identity_text(resolved_alias_map.get(normalized, ""))
        for resolved in (normalized, resolved_canonical):
            if resolved and resolved not in seen_expected:
                expected_identities.append(resolved)
                seen_expected.add(resolved)

    for candidate in candidate_identities:
        for expected in expected_identities:
            if candidate == expected or expected in candidate or candidate in expected:
                return True
    return False


@lru_cache(maxsize=1)
def load_source_registry() -> dict[str, Any]:
    """Load the full source registry configuration."""
    registry_path = Path(__file__).with_name("source_registry.json")
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def load_source_registry_alias_map() -> dict[str, str]:
    """Build alias -> canonical_source_id mapping from registry."""
    payload = load_source_registry()
    alias_map: dict[str, str] = {}
    for item in payload.get("sources") or []:
        canonical = normalize_source_identity_text(item.get("canonical_source_id"))
        if not canonical:
            continue
        alias_map[canonical] = canonical
        for alias in item.get("aliases") or []:
            normalized_alias = normalize_source_identity_text(alias)
            if normalized_alias:
                alias_map[normalized_alias] = canonical
    return alias_map


def get_source_priority(source: str) -> int:
    """Get priority for a source (higher = more authoritative)."""
    payload = load_source_registry()
    canonical = resolve_to_canonical_source(source)
    if not canonical:
        return 50  # Default priority

    for item in payload.get("sources") or []:
        if normalize_source_identity_text(item.get("canonical_source_id")) == canonical:
            return int(item.get("priority", 50))
    return 50


def get_source_trust_tier(source: str) -> str:
    """Get trust tier for a source: primary/secondary/supplementary/classic."""
    payload = load_source_registry()
    canonical = resolve_to_canonical_source(source)
    if not canonical:
        return "unknown"

    for item in payload.get("sources") or []:
        if normalize_source_identity_text(item.get("canonical_source_id")) == canonical:
            return str(item.get("trust_tier", "unknown"))
    return "unknown"


def resolve_to_canonical_source(source: str) -> str:
    """Resolve any source/alias to its canonical source ID."""
    alias_map = load_source_registry_alias_map()
    normalized = normalize_source_identity_text(source)
    return alias_map.get(normalized, "")


def get_course_primary_source(course_name: str) -> str | None:
    """Get the primary source textbook for a course."""
    payload = load_source_registry()
    course_map = payload.get("course_primary_sources") or {}
    return course_map.get(course_name)


def get_source_domain(source: str) -> str:
    """Get domain for a source (e.g., 'computer_network', 'operating_system')."""
    payload = load_source_registry()
    canonical = resolve_to_canonical_source(source)
    if not canonical:
        return "unknown"

    for item in payload.get("sources") or []:
        if normalize_source_identity_text(item.get("canonical_source_id")) == canonical:
            return str(item.get("domain", "unknown"))
    return "unknown"
