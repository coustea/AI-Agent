"""Two-stage hybrid routing for knowledge retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.config import (
    KB_COURSE_LINKAGE,
    KB_COURSE_ROUTING,
    KB_OLLAMA_BASE_URL,
    KB_ROUTING_KEYWORD_THRESHOLD,
    KB_ROUTING_LLM_CONFIDENCE,
    KB_ROUTING_LLM_MODEL,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

_COURSE_SOURCE_MAP: dict[str, tuple[str, ...]] = {
    "Java": ("Java从入门到精通（第5版）",),
    "计算机网络": ("计算机网络（第7版）",),
    "操作系统": ("计算机操作系统（慕课版）",),
    "数据结构": ("数据结构（C语言版）（第2版）",),
    "数据库": ("数据库系统概念（原书第6版）", "高性能MySQL（第4版）"),
    "Python": ("Python编程三剑客",),
    "Redis": ("Redis设计与实现",),
    "Vue": ("Vue.js Node.js全栈开发实战",),
    "算法": ("算法（第4版）",),
    "计算机组成原理": ("计算机组成原理 (谭志虎)",),
    "软件工程": ("软件工程案例教程（第三版）", "人月神话(二十周年纪念版)", "代码大全（第2版）"),
    "高等数学": ("张宇带你学高等数学",),
    "概率论": ("概率论与数理统计（慕课版）",),
}

_COURSE_ALIASES: dict[str, str] = {
    "计网": "计算机网络",
    "网络": "计算机网络",
    "os": "操作系统",
    "操作系统": "操作系统",
    "数据结构": "数据结构",
    "组成原理": "计算机组成原理",
    "计组": "计算机组成原理",
    "408操作系统": "操作系统",
    "408计算机网络": "计算机网络",
    "408数据结构": "数据结构",
    "408计算机组成原理": "计算机组成原理",
    # 408高频考点路由
    "OSI": "计算机网络",
    "OSI模型": "计算机网络",
    "七层模型": "计算机网络",
    "开放系统互连": "计算机网络",
    "TCP": "计算机网络",
    "UDP": "计算机网络",
    "IP地址": "计算机网络",
    "路由": "计算机网络",
    "以太网": "计算机网络",
    "CSMA": "计算机网络",
    "进程": "操作系统",
    "线程": "操作系统",
    "调度": "操作系统",
    "死锁": "操作系统",
    "信号量": "操作系统",
    "PV操作": "操作系统",
    "虚拟内存": "操作系统",
    "分页": "操作系统",
    "分段": "操作系统",
    "页表": "操作系统",
    "Cache": "计算机组成原理",
    "缓存": "计算机组成原理",
    "流水线": "计算机组成原理",
    "指令": "计算机组成原理",
    "寄存器": "计算机组成原理",
    "二叉树": "数据结构",
    "图": "数据结构",
    "排序": "数据结构",
    "查找": "数据结构",
    "栈": "数据结构",
    "队列": "数据结构",
}

_CHINESE_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9+#._-]{2,}")
_QUESTION_SPLIT_RE = re.compile(
    r"(?:什么是|什么叫|何谓|何为|是什么|为什么|怎么样|怎么办|如何|怎么|哪些|哪个|多少|是否|的|和|与|及|在|中)"
)
_BROAD_CONCEPT_QUERY_RE = re.compile(
    r"^(?:什么是|什么叫|何谓|何为|介绍(?:一下)?|概述(?:一下)?|解释(?:一下)?)"
)


@dataclass(frozen=True)
class _CourseScore:
    course: str
    score: float
    confidence: float = 1.0


@dataclass(frozen=True)
class QueryRouteResult:
    query: str
    source_filter: tuple[str, ...] | None = None
    route_confidence: float = 0.0
    route_mode: str = "none"
    allow_partial_routing: bool = False
    matched_terms: tuple[str, ...] = ()
    applied_filter_scope: str = "global"


def _extract_terms(query: str) -> list[str]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    def _expand_chinese_term(term: str) -> list[str]:
        pieces: list[str] = [term]
        for part in _QUESTION_SPLIT_RE.split(term):
            normalized_part = part.strip()
            if len(normalized_part) >= 2:
                pieces.append(normalized_part)

        expanded: list[str] = []
        seen_local: set[str] = set()
        for piece in pieces:
            if piece in seen_local:
                continue
            expanded.append(piece)
            seen_local.add(piece)
            if len(piece) >= 4:
                for window_size in (2, 3, 4):
                    for idx in range(len(piece) - window_size + 1):
                        sub = piece[idx : idx + window_size]
                        if sub and sub not in seen_local:
                            expanded.append(sub)
                            seen_local.add(sub)
        return expanded

    terms: list[str] = []
    for match in _ASCII_TERM_RE.findall(normalized_query):
        terms.append(match.strip())

    for match in _CHINESE_TERM_RE.findall(normalized_query):
        token = match.strip()
        if not token:
            continue
        terms.extend(_expand_chinese_term(token))

    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term and term not in seen:
            deduped.append(term)
            seen.add(term)
    return deduped


def _keyword_route(query: str) -> tuple[list[_CourseScore], tuple[str, ...]]:
    if not KB_COURSE_ROUTING:
        return [], ()

    terms = _extract_terms(query)
    if not terms:
        return [], ()

    lowered_terms = {term.lower() for term in terms}
    original_terms = set(terms)
    scored: list[_CourseScore] = []
    matched_terms: list[str] = []

    for course, keywords in KB_COURSE_ROUTING.items():
        if not isinstance(keywords, dict):
            continue

        total = 0.0
        has_strong_match = False
        course_exact_match = False
        course_lower = course.lower()
        if course in original_terms or course_lower in lowered_terms:
            total += 4.0
            has_strong_match = True
            course_exact_match = True
            matched_terms.append(course)

        for keyword, weight in keywords.items():
            keyword_lower = keyword.lower()
            exact_match = keyword in original_terms or keyword_lower in lowered_terms
            fuzzy_match = any(
                (
                    len(term) >= 3
                    and len(keyword) >= 3
                    and keyword_lower in term.lower()
                    and len(term) - len(keyword) <= 2
                )
                or (
                    len(term) >= 3
                    and len(keyword) >= 3
                    and term.lower() in keyword_lower
                    and len(keyword) - len(term) <= 2
                )
                for term in original_terms
            )

            if exact_match:
                total += float(weight)
                if float(weight) >= 2.0:
                    has_strong_match = True
                matched_terms.append(keyword)
            elif fuzzy_match:
                total += float(weight) * 0.5
                matched_terms.append(keyword)

        if total >= KB_ROUTING_KEYWORD_THRESHOLD or has_strong_match:
            scored.append(
                _CourseScore(
                    course=course,
                    score=total,
                    confidence=1.0 if course_exact_match else min(total / 5.0, 1.0),
                )
            )

    alias_boosts: dict[str, float] = {}
    for alias, target in _COURSE_ALIASES.items():
        alias_normalized = alias.strip()
        if not alias_normalized:
            continue
        alias_lower = alias_normalized.lower()
        if alias_normalized in original_terms or alias_lower in lowered_terms:
            alias_boosts[target] = alias_boosts.get(target, 0.0) + 4.0
            matched_terms.append(alias_normalized)

    for course, score in alias_boosts.items():
        scored.append(
            _CourseScore(
                course=course,
                score=score,
                confidence=min(score / 5.0, 1.0),
            )
        )

    merged_scores: dict[str, _CourseScore] = {}
    for item in scored:
        existing = merged_scores.get(item.course)
        if existing is None:
            merged_scores[item.course] = item
            continue
        merged_scores[item.course] = _CourseScore(
            course=item.course,
            score=existing.score + item.score,
            confidence=max(existing.confidence, item.confidence),
        )

    scored = sorted(merged_scores.values(), key=lambda item: item.score, reverse=True)
    deduped_terms = tuple(dict.fromkeys(term for term in matched_terms if term))
    return scored, deduped_terms


def _llm_route(query: str) -> list[_CourseScore]:
    if not KB_COURSE_ROUTING:
        return []

    course_names = list(KB_COURSE_ROUTING.keys())
    prompt = (
        "你是一个课程分类器。根据用户问题判断所属课程。\n"
        f"可选课程：{', '.join(course_names)}\n"
        f"用户问题：{query}\n"
        '请只返回 JSON，格式为：{"courses":[{"name":"课程名","confidence":0.9}]}\n'
        "只返回 confidence >= 0.3 的课程，按 confidence 降序排列。"
    )

    try:
        response = httpx.post(
            f"{KB_OLLAMA_BASE_URL}/api/generate",
            json={
                "model": KB_ROUTING_LLM_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
            timeout=5.0,
            trust_env=False,
        )
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("response", "")
        if not raw:
            return []

        parsed = json.loads(raw)
        courses_raw = parsed.get("courses", [])
        results: list[_CourseScore] = []
        for item in courses_raw:
            name = str(item.get("name", "")).strip()
            confidence = float(item.get("confidence", 0.0))
            if name in course_names and confidence >= KB_ROUTING_LLM_CONFIDENCE:
                results.append(
                    _CourseScore(course=name, score=confidence * 5.0, confidence=confidence)
                )
        results.sort(key=lambda item: item.confidence, reverse=True)
        return results
    except Exception:
        logger.debug("[knowledge_router] LLM routing failed, falling back to keywords")
        return []


def _expand_with_linkage(courses: list[_CourseScore]) -> list[_CourseScore]:
    if not KB_COURSE_LINKAGE:
        return courses

    expanded = list(courses)
    existing = {course.course for course in courses}
    for course_score in courses:
        for linked_course in KB_COURSE_LINKAGE.get(course_score.course, []):
            if linked_course in existing:
                continue
            expanded.append(
                _CourseScore(
                    course=linked_course,
                    score=course_score.score * 0.5,
                    confidence=course_score.confidence * 0.5,
                )
            )
            existing.add(linked_course)
    return expanded


def _courses_to_source_filter(courses: list[_CourseScore]) -> tuple[str, ...] | None:
    """Convert course routing results to canonical source IDs using source_registry."""
    if not courses:
        return None

    from app.rag.config.source_registry import get_course_primary_source

    seen: set[str] = set()
    sources: list[str] = []
    for course_score in courses:
        # Primary source from registry
        primary = get_course_primary_source(course_score.course)
        if primary and primary not in seen:
            sources.append(primary)
            seen.add(primary)
        # Fallback to hardcoded map (for backward compatibility)
        for source in _COURSE_SOURCE_MAP.get(course_score.course, ()):
            if source not in seen:
                sources.append(source)
                seen.add(source)
    return tuple(sources) if sources else None


def _primary_source_filter(course: str) -> tuple[str, ...] | None:
    """Get primary canonical source ID for a course."""
    from app.rag.config.source_registry import get_course_primary_source

    primary = get_course_primary_source(course)
    if primary:
        return (primary,)
    # Fallback to first entry in hardcoded map
    sources = _COURSE_SOURCE_MAP.get(course, ())
    return (sources[0],) if sources else None


def _normalize_course_name(course_name: str) -> str | None:
    normalized = (course_name or "").strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    if lowered in _COURSE_ALIASES:
        return _COURSE_ALIASES[lowered]

    for alias, target in _COURSE_ALIASES.items():
        if alias in lowered:
            return target

    if normalized in _COURSE_SOURCE_MAP:
        return normalized

    for course in _COURSE_SOURCE_MAP:
        if course in normalized or normalized in course:
            return course

    return None


def _is_broad_concept_query(query: str) -> bool:
    normalized = (query or "").strip()
    if not normalized:
        return False
    if _BROAD_CONCEPT_QUERY_RE.match(normalized):
        return True
    return bool(
        re.search(r"(?:的)?(?:定义|概念|含义|简介|概述)(?:是什么)?$", normalized)
    )


def route_query_sources(query: str, course_name: str | None = None) -> QueryRouteResult:
    normalized_query = (query or "").strip()
    raw_course_name = (course_name or "").strip()
    normalized_course = _normalize_course_name(course_name or "")
    if not normalized_query and not normalized_course:
        return QueryRouteResult(query=normalized_query, source_filter=None)

    if raw_course_name and any(ch in raw_course_name for ch in ("（", "(", "版")):
        return QueryRouteResult(
            query=normalized_query,
            source_filter=(raw_course_name,),
            route_confidence=1.0,
            route_mode="source_hint",
            allow_partial_routing=False,
            matched_terms=(raw_course_name,),
            applied_filter_scope="strict",
        )

    if normalized_course:
        source_filter = _primary_source_filter(normalized_course)
        return QueryRouteResult(
            query=normalized_query,
            source_filter=source_filter,
            route_confidence=1.0,
            route_mode="course_hint",
            allow_partial_routing=False,
            matched_terms=(normalized_course,),
            applied_filter_scope="strict",
        )

    keyword_result = _keyword_route(normalized_query)
    if isinstance(keyword_result, tuple) and len(keyword_result) == 2:
        keyword_courses, matched_terms = keyword_result
    else:
        keyword_courses = keyword_result
        matched_terms = ()

    keyword_single = keyword_courses[0] if len(keyword_courses) == 1 else None
    keyword_is_clear = bool(keyword_single and keyword_single.score >= 4.0)
    courses = _llm_route(normalized_query)
    route_mode = "llm"
    if keyword_is_clear and (
        not courses or len(courses) != 1 or courses[0].course != keyword_single.course
    ):
        courses = [keyword_single]
        route_mode = "keyword"
    elif keyword_is_clear and len(courses) == 1 and courses[0].course == keyword_single.course:
        courses = [keyword_single]
        route_mode = "keyword"
    elif not courses:
        courses = keyword_courses
        route_mode = "keyword" if courses else "none"

    courses = _expand_with_linkage(courses)
    if courses:
        courses.sort(key=lambda item: item.score, reverse=True)
        top_score = courses[0].score
        if top_score >= 2.0:
            narrowed = [course for course in courses if course.score >= top_score * 0.8]
            if narrowed:
                courses = narrowed
    route_confidence = max((course.confidence for course in courses), default=0.0)
    allow_partial_routing = len(courses) > 1 and route_confidence < 0.85
    if len(courses) == 1 and route_confidence >= 0.7:
        applied_scope = "strict"
    elif route_confidence >= 0.85:
        applied_scope = "strict"
    elif route_confidence >= 0.6 and courses:
        applied_scope = "hybrid"
    else:
        applied_scope = "boost_only"
    source_filter = _courses_to_source_filter(courses)
    if len(courses) == 1 and applied_scope == "strict" and not _is_broad_concept_query(normalized_query):
        source_filter = _primary_source_filter(courses[0].course)
    return QueryRouteResult(
        query=normalized_query,
        source_filter=source_filter,
        route_confidence=route_confidence,
        route_mode=route_mode,
        allow_partial_routing=allow_partial_routing,
        matched_terms=matched_terms,
        applied_filter_scope=applied_scope,
    )


def _normalize_source_identity_text(value: object) -> str:
    from app.rag.config.source_registry import normalize_source_identity_text

    return normalize_source_identity_text(value)


def _get_source_registry_alias_map() -> dict[str, str]:
    from app.rag.config.source_registry import load_source_registry_alias_map

    alias_map = load_source_registry_alias_map()
    if not alias_map:
        logger.warning("[knowledge_router] failed to load source registry alias map")
    return alias_map


def _matches_source_filter(metadata: dict, source_filter: tuple[str, ...]) -> bool:
    if not source_filter:
        return False

    candidate_identities: list[str] = []
    seen: set[str] = set()
    for key in ("canonical_source_id", "book_name", "source_stem", "book_title", "source", "file_name"):
        normalized = _normalize_source_identity_text(metadata.get(key))
        if normalized and normalized not in seen:
            candidate_identities.append(normalized)
            seen.add(normalized)

    if not candidate_identities:
        return False

    alias_map = _get_source_registry_alias_map()
    expected_identities: list[str] = []
    seen_expected: set[str] = set()
    for expected in source_filter:
        normalized = _normalize_source_identity_text(expected)
        if not normalized:
            continue
        resolved_canonical = _normalize_source_identity_text(alias_map.get(normalized, ""))
        for resolved in (normalized, resolved_canonical):
            if resolved and resolved not in seen_expected:
                expected_identities.append(resolved)
                seen_expected.add(resolved)

    for candidate in candidate_identities:
        for expected in expected_identities:
            if candidate == expected or expected in candidate or candidate in expected:
                return True

    return False
