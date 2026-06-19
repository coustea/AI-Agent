"""两阶段混合路由：LLM 意图识别（主） + 加权关键词匹配（备选）。

路由策略：
  1. Stage 1 — LLM 路由：通过 Ollama 本地模型识别查询所属课程，返回带置信度的课程列表
  2. Stage 2 — 关键词路由：基于配置的加权关键词表计算各课程匹配分数，作为 LLM 失败时的备选
  3. 课程关联扩展：通过 course_linkage 配置将关联课程加入结果
  4. 源过滤转换：将课程名映射为知识库书名子串，用于 Chroma source_filter
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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

# 课程名 → 知识库书名子串映射
# 用于将路由结果转换为 Chroma source_filter
_COURSE_SOURCE_MAP: dict[str, tuple[str, ...]] = {
    "Java": ("Java从入门到精通",),
    "计算机网络": ("计算机网络",),
    "操作系统": ("操作系统",),
    "数据结构": ("数据结构",),
    "数据库": ("数据库",),
    "Python": ("Python",),
    "Redis": ("Redis",),
    "Vue": ("Vue",),
    "算法": ("算法",),
    "计算机组成原理": ("计算机组成",),
    "软件工程": ("软件工程",),
    "高等数学": ("高等数学",),
    "线性代数": ("线性代数",),
    "概率论": ("概率论",),
}

# 中文分词正则：匹配连续 2 个及以上的中文字符
_CHINESE_TERM_RE = re.compile(r"[一-鿿]{2,}")
# 英文/数字分词正则：匹配连续 2 个及以上的字母、数字、+、#、.、-
_ASCII_TERM_RE = re.compile(r"[A-Za-z0-9+#.-]{2,}")


@dataclass(frozen=True)
class _CourseScore:
    """课程匹配评分结果。"""

    course: str
    score: float
    confidence: float = 1.0


@dataclass(frozen=True)
class QueryRouteResult:
    """查询路由结果。"""

    query: str
    source_filter: tuple[str, ...] | None = None


def _extract_terms(query: str) -> list[str]:
    """从查询文本中提取中英文分词结果。

    英文/数字直接按正则提取；中文先提取连续片段，
    再用滑动窗口提取 2~4 字符子串，确保短/中关键词也能匹配。
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    terms: list[str] = []
    for match in _ASCII_TERM_RE.findall(normalized_query):
        token = match.strip()
        if token:
            terms.append(token)
    for match in _CHINESE_TERM_RE.findall(normalized_query):
        token = match.strip()
        if token:
            terms.append(token)
            # 滑动窗口提取 2~4 字符子串，覆盖关键词如"多线程"、"三次握手"
            if len(token) >= 4:
                for window_size in (2, 3, 4):
                    for i in range(len(token) - window_size + 1):
                        sub = token[i : i + window_size]
                        if sub not in terms:
                            terms.append(sub)

    return list(dict.fromkeys(terms))


def _keyword_route(query: str) -> list[_CourseScore]:
    """加权关键词匹配路由。

    遍历 KB_COURSE_ROUTING 中每个课程的关键词表，
    对查询中命中的关键词累加权重。入选条件：
    - 总分 >= KB_ROUTING_KEYWORD_THRESHOLD，或
    - 存在单个独占关键词（weight >= 2.0）精确匹配
    """
    if not KB_COURSE_ROUTING:
        return []

    terms = _extract_terms(query)
    if not terms:
        return []

    # 构建小写词到原始词的映射，用于大小写不敏感匹配
    lowered_terms = {t.lower(): t for t in terms}
    # 同时保留原始中文词
    all_terms_set = set(terms) | set(lowered_terms.keys())

    scored: list[_CourseScore] = []
    for course, keywords in KB_COURSE_ROUTING.items():
        if not isinstance(keywords, dict):
            continue
        total = 0.0
        has_exclusive_match = False
        for keyword, weight in keywords.items():
            kw_lower = keyword.lower()
            # 精确匹配（大小写不敏感）
            if keyword in all_terms_set or kw_lower in lowered_terms:
                total += weight
                if weight >= 2.0:
                    has_exclusive_match = True
            elif any(kw_lower in t or t in kw_lower for t in all_terms_set):
                total += weight * 0.5  # 子串匹配降权

        if total >= KB_ROUTING_KEYWORD_THRESHOLD or has_exclusive_match:
            scored.append(_CourseScore(course=course, score=total, confidence=min(total / 5.0, 1.0)))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def _llm_route(query: str) -> list[_CourseScore]:
    """LLM 意图识别路由。

    通过 Ollama 本地模型识别查询所属课程。
    使用 format: "json" 获取结构化输出，5s 超时。
    任何错误均静默降级，返回空列表。
    """
    if not KB_COURSE_ROUTING:
        return []

    course_names = list(KB_COURSE_ROUTING.keys())
    prompt = (
        "你是一个课程分类器。根据用户的问题，判断它属于哪门课程。\n"
        f"可选课程：{', '.join(course_names)}\n"
        f'用户问题：{query}\n'
        '请以JSON格式回答，格式为：{"courses": [{"name": "课程名", "confidence": 0.9}]}\n'
        "只返回置信度 >= 0.3 的课程，按置信度降序排列。只返回JSON，不要其他内容。"
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
        )
        response.raise_for_status()
        data = response.json()
        raw_response = data.get("response", "")
        if not raw_response:
            return []

        import json

        parsed = json.loads(raw_response)
        courses_raw = parsed.get("courses", [])
        results: list[_CourseScore] = []
        for item in courses_raw:
            name = str(item.get("name", "")).strip()
            confidence = float(item.get("confidence", 0.0))
            if name in course_names and confidence >= KB_ROUTING_LLM_CONFIDENCE:
                results.append(_CourseScore(course=name, score=confidence * 5.0, confidence=confidence))

        results.sort(key=lambda s: s.confidence, reverse=True)
        return results
    except Exception:
        logger.debug("[knowledge_router] LLM routing failed, falling back to keywords")
        return []


def _expand_with_linkage(courses: list[_CourseScore]) -> list[_CourseScore]:
    """通过课程关联扩展课程列表。

    使用 KB_COURSE_LINKAGE 配置，将已匹配课程的关联课程以较低置信度加入结果。
    """
    if not KB_COURSE_LINKAGE:
        return courses

    existing = {cs.course for cs in courses}
    expanded = list(courses)

    for cs in courses:
        linked = KB_COURSE_LINKAGE.get(cs.course, [])
        for linked_course in linked:
            if linked_course not in existing:
                expanded.append(
                    _CourseScore(
                        course=linked_course,
                        score=cs.score * 0.5,
                        confidence=cs.confidence * 0.5,
                    )
                )
                existing.add(linked_course)

    return expanded


def _courses_to_source_filter(courses: list[_CourseScore]) -> tuple[str, ...] | None:
    """将课程列表转换为 source_filter。

    通过 _COURSE_SOURCE_MAP 将课程名映射为知识库书名子串。
    无匹配时返回 None（不过滤）。
    """
    if not courses:
        return None

    sources: list[str] = []
    seen: set[str] = set()
    for cs in courses:
        book_titles = _COURSE_SOURCE_MAP.get(cs.course)
        if book_titles:
            for title in book_titles:
                if title not in seen:
                    sources.append(title)
                    seen.add(title)

    return tuple(sources) if sources else None


def route_query_sources(query: str, course_name: str | None = None) -> QueryRouteResult:
    """两阶段混合路由入口。

    优先级：
    1. 如果 course_name 直接映射到课程，作为强信号使用
    2. Stage 1: LLM 路由（主）
    3. Stage 2: 关键词路由（备选，当 LLM 无结果时）
    4. 课程关联扩展
    5. 转换为 source_filter
    """
    normalized_query = (query or "").strip()
    normalized_course_name = (course_name or "").strip()

    # 如果 course_name 直接映射到课程，作为强信号
    if normalized_course_name:
        # 尝试精确匹配课程名
        if normalized_course_name in _COURSE_SOURCE_MAP:
            source_filter = _courses_to_source_filter(
                [_CourseScore(course=normalized_course_name, score=10.0, confidence=1.0)]
            )
            return QueryRouteResult(query=normalized_query, source_filter=source_filter)

        # 尝试模糊匹配：course_name 包含课程名或课程名包含 course_name
        for course_key in _COURSE_SOURCE_MAP:
            if course_key in normalized_course_name or normalized_course_name in course_key:
                source_filter = _courses_to_source_filter(
                    [_CourseScore(course=course_key, score=10.0, confidence=1.0)]
                )
                return QueryRouteResult(query=normalized_query, source_filter=source_filter)

    # Stage 1: LLM 路由
    courses = _llm_route(normalized_query)

    # Stage 2: 关键词路由（当 LLM 无结果时作为备选）
    if not courses:
        courses = _keyword_route(normalized_query)

    # 课程关联扩展
    courses = _expand_with_linkage(courses)

    # 转换为 source_filter
    source_filter = _courses_to_source_filter(courses)

    return QueryRouteResult(query=normalized_query, source_filter=source_filter)
