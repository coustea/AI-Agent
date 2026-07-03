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
    "Java": ("Java从入门到精通",),
    "计算机网络": ("计算机网络",),
    "操作系统": ("计算机操作系统",),
    "数据结构": ("数据结构",),
    "数据库": ("数据库系统概念", "高性能MySQL"),
    "Python": ("Python",),
    "Redis": ("Redis",),
    "Vue": ("Vue",),
    "算法": ("算法（第4版）",),
    "计算机组成原理": ("计算机组成原理", "计算机系统解密", "深入理解计算机系统"),
    "软件工程": ("软件工程", "人月神话", "代码大全"),
    "高等数学": ("高等数学", "微积分", "张宇带你学高等数学"),
    "线性代数": ("线性代数", "矩阵", "行列式"),
    "概率论": ("概率论", "数理统计",),
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
}

_CHINESE_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9+#._-]{2,}")


@dataclass(frozen=True)
class _CourseScore:
    course: str
    score: float
    confidence: float = 1.0


@dataclass(frozen=True)
class QueryRouteResult:
    query: str
    source_filter: tuple[str, ...] | None = None


def _extract_terms(query: str) -> list[str]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    terms: list[str] = []
    for match in _ASCII_TERM_RE.findall(normalized_query):
        terms.append(match.strip())

    for match in _CHINESE_TERM_RE.findall(normalized_query):
        token = match.strip()
        if not token:
            continue
        terms.append(token)
        if len(token) >= 4:
            for window_size in (2, 3, 4):
                for idx in range(len(token) - window_size + 1):
                    sub = token[idx : idx + window_size]
                    terms.append(sub)

    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term and term not in seen:
            deduped.append(term)
            seen.add(term)
    return deduped


def _keyword_route(query: str) -> list[_CourseScore]:
    if not KB_COURSE_ROUTING:
        return []

    terms = _extract_terms(query)
    if not terms:
        return []

    lowered_terms = {term.lower() for term in terms}
    original_terms = set(terms)
    scored: list[_CourseScore] = []

    for course, keywords in KB_COURSE_ROUTING.items():
        if not isinstance(keywords, dict):
            continue

        total = 0.0
        has_strong_match = False
        for keyword, weight in keywords.items():
            keyword_lower = keyword.lower()
            exact_match = keyword in original_terms or keyword_lower in lowered_terms
            fuzzy_match = any(
                keyword_lower in term.lower() or term.lower() in keyword_lower
                for term in original_terms
            )

            if exact_match:
                total += float(weight)
                if float(weight) >= 2.0:
                    has_strong_match = True
            elif fuzzy_match:
                total += float(weight) * 0.5

        if total >= KB_ROUTING_KEYWORD_THRESHOLD or has_strong_match:
            scored.append(
                _CourseScore(
                    course=course,
                    score=total,
                    confidence=min(total / 5.0, 1.0),
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored


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
    if not courses:
        return None

    seen: set[str] = set()
    sources: list[str] = []
    for course_score in courses:
        for source in _COURSE_SOURCE_MAP.get(course_score.course, ()):
            if source not in seen:
                sources.append(source)
                seen.add(source)
    return tuple(sources) if sources else None


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


def route_query_sources(query: str, course_name: str | None = None) -> QueryRouteResult:
    normalized_query = (query or "").strip()
    normalized_course = _normalize_course_name(course_name or "")
    if not normalized_query and not normalized_course:
        return QueryRouteResult(query=normalized_query, source_filter=None)

    if normalized_course:
        source_filter = _courses_to_source_filter(
            [_CourseScore(course=normalized_course, score=10.0, confidence=1.0)]
        )
        return QueryRouteResult(query=normalized_query, source_filter=source_filter)

    courses = _llm_route(normalized_query)
    if not courses:
        courses = _keyword_route(normalized_query)

    courses = _expand_with_linkage(courses)
    return QueryRouteResult(
        query=normalized_query,
        source_filter=_courses_to_source_filter(courses),
    )
