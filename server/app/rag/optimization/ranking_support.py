from __future__ import annotations

import re
from typing import Any, Callable

from app.rag.config.source_registry import normalize_book_title


LOW_VALUE_TEXT_MARKERS: tuple[str, ...] = ("前言", "目录", "致谢", "未知")

_DEFINITION_MARKERS: tuple[str, ...] = ("是指", "定义", "概念", "含义")
_PROCEDURE_MARKERS: tuple[str, ...] = ("步骤", "过程", "流程", "执行", "如何")
_COMPARISON_MARKERS: tuple[str, ...] = ("区别", "对比", "比较", "不同")
_EXAMPLE_MARKERS: tuple[str, ...] = ("例如", "比如", "示例", "例子")
_TERM_RE = re.compile(r"[A-Za-z0-9+#._-]{2,}|[\u4e00-\u9fff]{2,}")
_TOC_DOTTED_LINE_RE = re.compile(r"\.{4,}\s*\d+\s*$")
_SECTION_PAGE_LINE_RE = re.compile(r"^\s*\d+(?:\.\d+)+\s+.+\s\.{4,}\s*\d+\s*$")
_QUESTION_INTENT_RE = re.compile(
    r"^(?:什么是|什么叫|何谓|何为|介绍(?:一下)?|概述(?:一下)?|解释(?:一下)?)|(?:的)?(?:定义|概念|含义)(?:是什么)?$"
)
_EXERCISE_MARKERS: tuple[str, ...] = ("练习题", "思考题", "习题", "课后题", "选择题", "填空题", "判断题")
_FRONT_MATTER_MARKERS: tuple[str, ...] = ("封面", "版权", "前言", "目录", "丛书", "版次")
_VERTICAL_TEXT_RE = re.compile(r"(?:^|\n)(?:[\u4e00-\u9fffA-Za-z0-9#（）()]+(?:\n|$)){5,}")


def infer_chunk_type(text: str, metadata: dict[str, Any] | None = None) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return "noise"

    preview = normalized[:240]
    heading = str((metadata or {}).get("heading_path") or "").strip()
    if not heading and any(marker in preview for marker in LOW_VALUE_TEXT_MARKERS):
        return "frontmatter"
    if any(marker in preview for marker in _DEFINITION_MARKERS):
        return "definition"
    if any(marker in preview for marker in _COMPARISON_MARKERS):
        return "comparison"
    if any(marker in preview for marker in _PROCEDURE_MARKERS):
        return "procedure"
    if any(marker in preview for marker in _EXAMPLE_MARKERS):
        return "example"
    return "concept"


def extract_concept_terms(text: str, metadata: dict[str, Any] | None = None, *, limit: int = 8) -> tuple[str, ...]:
    values = [
        str(text or ""),
        str((metadata or {}).get("heading_path") or ""),
        str((metadata or {}).get("book_name") or (metadata or {}).get("book_title") or ""),
    ]
    terms: list[str] = []
    for value in values:
        for match in _TERM_RE.findall(value):
            term = match.strip()
            if len(term) < 2:
                continue
            if term not in terms:
                terms.append(term)
            if len(terms) >= limit:
                return tuple(terms)
    return tuple(terms)


def build_local_context_summary(text: str, metadata: dict[str, Any]) -> str:
    heading = str(metadata.get("heading_path") or metadata.get("h1") or metadata.get("h2") or "").strip()
    title = normalize_book_title(
        str(
            metadata.get("book_name")
            or metadata.get("book_title")
            or metadata.get("source_stem")
            or metadata.get("source")
            or metadata.get("file_name")
            or ""
        )
    )
    body = str(text or "").strip().replace("\r", " ").replace("\n", " ")
    snippet = body[:160].strip()
    parts = [part for part in (title, heading, snippet) if part]
    return " | ".join(parts)


def build_sparse_search_text(text: str, metadata: dict[str, Any]) -> str:
    title = normalize_book_title(
        str(
            metadata.get("book_name")
            or metadata.get("source_stem")
            or metadata.get("source")
            or metadata.get("file_name")
            or ""
        )
    )
    heading = str(metadata.get("heading_path") or metadata.get("h1") or metadata.get("h2") or "").strip()
    course = str(metadata.get("course") or "").strip()
    concept_tags = metadata.get("concept_tags") or ()
    concept_line = " ".join(str(tag).strip() for tag in concept_tags if str(tag).strip())
    local_summary = str(metadata.get("local_context_summary") or "").strip()
    return "\n".join(
        part
        for part in (str(text or "").strip(), heading, title, course, concept_line, local_summary)
        if part
    ).lower()


def low_value_chunk_penalty(metadata: dict[str, Any], text: str) -> float:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return 0.0

    heading = str(metadata.get("heading_path") or "").strip()
    preview = normalized_text[:200]
    penalty = 0.0

    if not heading:
        penalty += 0.02

    if any(marker in preview for marker in LOW_VALUE_TEXT_MARKERS):
        penalty += 0.02

    if heading and any(marker in heading for marker in _EXERCISE_MARKERS):
        penalty += 0.03

    if any(marker in preview for marker in _FRONT_MATTER_MARKERS):
        penalty += 0.03

    if _VERTICAL_TEXT_RE.search(normalized_text[:160]):
        penalty += 0.04

    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        if len(lines) <= 3 and len(first_line) >= 6 and first_line in normalized_text[1:160]:
            penalty += 0.02

    return penalty


def is_low_value_sparse_chunk(metadata: dict[str, Any], text: str) -> bool:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return True

    heading = str(metadata.get("heading_path") or "").strip()
    preview = normalized_text[:200]

    if _TOC_DOTTED_LINE_RE.search(preview) or _SECTION_PAGE_LINE_RE.match(preview):
        return True

    if heading and (_TOC_DOTTED_LINE_RE.search(heading) or "........" in heading):
        return True

    if heading and any(marker in heading for marker in _EXERCISE_MARKERS):
        return True

    if heading:
        if any(marker in preview for marker in _FRONT_MATTER_MARKERS):
            return True
        return False

    if any(marker in preview for marker in LOW_VALUE_TEXT_MARKERS):
        return True

    if any(marker in preview for marker in _FRONT_MATTER_MARKERS):
        return True

    if _VERTICAL_TEXT_RE.search(normalized_text[:160]):
        return True

    lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]
    if len(lines) <= 3 and lines and len(lines[0]) >= 6:
        return True

    return False


def is_definition_query(query_text: str) -> bool:
    normalized = str(query_text or "").strip()
    if not normalized:
        return False
    return bool(_QUESTION_INTENT_RE.search(normalized))


def definition_query_bonus(
    metadata: dict[str, Any],
    text: str,
    *,
    query_text: str,
    query_terms: tuple[str, ...] = (),
) -> float:
    if not is_definition_query(query_text):
        return 0.0

    heading = str(metadata.get("heading_path") or "").casefold()
    content = str(text or "").casefold()
    bonus = 0.0
    chunk_type = infer_chunk_type(text, metadata)

    if chunk_type == "definition":
        bonus += 0.03
    elif chunk_type == "concept":
        bonus += 0.015
    elif chunk_type == "procedure":
        bonus -= 0.01

    if any(marker in heading for marker in ("定义", "概念", "概述", "简介")):
        bonus += 0.02

    if any(marker in content[:220] for marker in ("是指", "定义为", "通常指", "是研究")):
        bonus += 0.02

    if any(marker in heading for marker in _EXERCISE_MARKERS):
        bonus -= 0.04

    normalized_terms = tuple(term.casefold() for term in query_terms if term)
    if normalized_terms and any(term in content[:220] for term in normalized_terms):
        bonus += 0.01

    return bonus


def _count_query_term_hits(blob: str, query_terms: tuple[str, ...]) -> int:
    normalized_blob = str(blob or "").casefold()
    if not normalized_blob:
        return 0
    return sum(1 for term in query_terms if term and term in normalized_blob)


def semantic_concept_tag_bonus(metadata: dict[str, Any], query_terms: tuple[str, ...]) -> float:
    normalized_terms = tuple(term.casefold() for term in query_terms if term)
    if not normalized_terms:
        return 0.0

    concept_tags = metadata.get("concept_tags") or ()
    tag_blob = " ".join(str(tag or "").casefold() for tag in concept_tags)
    tag_hits = _count_query_term_hits(tag_blob, normalized_terms)
    if tag_hits <= 0:
        return 0.0

    coverage = tag_hits / len(normalized_terms)
    bonus = 0.008 * tag_hits
    if metadata.get("semantic_split"):
        bonus += 0.03
        if coverage >= 0.67:
            bonus += 0.03
        if coverage >= 1.0:
            bonus += 0.02
    return bonus


def heading_only_match_penalty(
    metadata: dict[str, Any],
    text: str,
    query_terms: tuple[str, ...],
) -> float:
    normalized_terms = tuple(term.casefold() for term in query_terms if term)
    if not normalized_terms:
        return 0.0

    heading = str(metadata.get("heading_path") or "").casefold()
    if not heading or _count_query_term_hits(heading, normalized_terms) <= 0:
        return 0.0

    concept_tags = metadata.get("concept_tags") or ()
    tag_blob = " ".join(str(tag or "").casefold() for tag in concept_tags)
    summary = str(metadata.get("local_context_summary") or "").casefold()
    trusted_support_hits = _count_query_term_hits(f"{tag_blob}\n{summary}", normalized_terms)
    if trusted_support_hits > 0:
        return 0.0

    heading_hits = _count_query_term_hits(heading, normalized_terms)
    content_hits = _count_query_term_hits(str(text or ""), normalized_terms)
    if content_hits >= len(normalized_terms):
        return min(0.12, 0.03 * heading_hits)
    return min(0.30, 0.09 * heading_hits)


def rrf_score(rank: int, constant: int) -> float:
    return 1.0 / (constant + rank)


def merge_ranked_results(
    *,
    dense_rows: list[dict[str, Any]],
    sparse_rows: list[dict[str, Any]],
    top_k: int,
    source_filter: tuple[str, ...] | None,
    metadata_key: Callable[[dict[str, Any]], tuple[str, str]],
    matches_source_filter: Callable[[dict[str, Any], tuple[str, ...] | None], bool],
    rrf_k: int = 60,
    original_boost: float = 1.0,
    route_match_boost: float = 0.0,
    heading_term_boost: float = 0.0,
    direct_hit_boost: float = 0.0,
    short_chunk_penalty: float = 0.0,
    query_terms: tuple[str, ...] = (),
    query_text: str = "",
) -> list[dict[str, Any]]:
    merged_scores: dict[tuple[str, str], dict[str, Any]] = {}
    normalized_terms = tuple(term.casefold() for term in query_terms if term)

    for rows in (dense_rows, sparse_rows):
        for item in rows:
            metadata = dict(item.get("metadata") or {})
            key = metadata_key(metadata)
            score = rrf_score(int(item.get("rank") or 0), rrf_k)
            if item.get("_is_original"):
                score *= original_boost
            score -= low_value_chunk_penalty(metadata, str(item.get("text") or ""))
            if matches_source_filter(metadata, source_filter):
                score += route_match_boost
            heading = str(metadata.get("heading_path") or "").casefold()
            content = str(item.get("text") or "").casefold()
            if normalized_terms and heading and any(term in heading for term in normalized_terms):
                score += heading_term_boost
            if normalized_terms and any(term in content for term in normalized_terms):
                score += direct_hit_boost
            score += semantic_concept_tag_bonus(metadata, query_terms)
            score -= heading_only_match_penalty(metadata, str(item.get("text") or ""), query_terms)
            if len(str(item.get("text") or "").strip()) < 120:
                score -= short_chunk_penalty
            score += definition_query_bonus(
                metadata,
                str(item.get("text") or ""),
                query_text=query_text,
                query_terms=query_terms,
            )
            existing = merged_scores.get(key)
            if existing is None:
                # Preserve source_scope field from input
                item_copy = {**item, "metadata": metadata, "fusion_score": score}
                if "source_scope" in item:
                    item_copy["source_scope"] = item["source_scope"]
                merged_scores[key] = {
                    "item": item_copy,
                    "score": score,
                }
            else:
                existing["score"] += score
                if item.get("rank", 9999) < existing["item"].get("rank", 9999):
                    item_copy = {**item, "metadata": metadata, "fusion_score": existing["score"]}
                    if "source_scope" in item:
                        item_copy["source_scope"] = item["source_scope"]
                    existing["item"] = item_copy
                else:
                    existing["item"]["fusion_score"] = existing["score"]

    ordered = sorted(
        merged_scores.values(),
        key=lambda item: (
            0 if matches_source_filter(item["item"].get("metadata") or {}, source_filter) else 1,
            -item["score"],
            item["item"].get("rank", 9999),
        ),
    )

    result: list[dict[str, Any]] = []
    for index, candidate in enumerate(ordered[:top_k], start=1):
        item = dict(candidate["item"])
        item["rank"] = index
        item["fusion_score"] = candidate["score"]
        result.append(item)
    return result
