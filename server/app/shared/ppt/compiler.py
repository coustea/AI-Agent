"""
Markdown 教学课件编译器。

大模型只输出受约束 Markdown，本模块只负责把协议化 Markdown
编译为 PPTPlan。编译器不再兼容旧的 role / shape / system node / hierarchy
等结构，也不再根据标题或内容自动猜测页面类型。
"""

from __future__ import annotations

import re
from typing import cast

from app.shared.ppt.models import (
    ComparisonTable,
    CoverMeta,
    DensityMode,
    KeyPoint,
    KnowledgeBranch,
    MisconceptionItem,
    PPTPlan,
    PPTSlide,
    PPTTemplatePreference,
    ProcessStep,
    SlideType,
)


class PPTCompileError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        slide_index: int | None = None,
    ) -> None:
        self.slide_index = slide_index
        prefix = f"slide {slide_index + 1}: " if slide_index is not None else ""
        super().__init__(prefix + message)


SLIDE_TYPES: set[str] = {
    "cover",
    "agenda",
    "learning_goals",
    "hook_question",
    "definition",
    "concept_boundary",
    "mechanism_overview",
    "knowledge_explain",
    "comparison",
    "misconception",
    "knowledge_map",
    "closing",
}

DEFAULT_ANIMATION = {
    "cover": "reveal",
    "agenda": "trace",
    "learning_goals": "build",
    "hook_question": "focus",
    "definition": "reveal",
    "concept_boundary": "compare",
    "mechanism_overview": "trace",
    "knowledge_explain": "build",
    "comparison": "compare",
    "misconception": "resolve",
    "knowledge_map": "build",
    "closing": "focus",
}

_SLIDE_SEPARATOR = re.compile(r"^---\s*$", re.MULTILINE)
_SLIDE_HEADING = re.compile(r"^##\s+\[([a-z_]+)]\s+(.+?)\s*$", re.MULTILINE)
_LABEL_LINE = re.compile(r"^\*\*(?P<label>[^*：:]+)[:：]\*\*\s*(?P<value>.+?)\s*$")
_POINT_LINE = re.compile(
    r"^[-*]\s+\*\*(?P<label>.+?)[:：]?\*\*[:：]?\s*(?P<detail>.+?)\s*$"
)
_STEP_LINE = re.compile(
    r"^(?:[-*]|\d+[.)])\s+"
    r"\*\*"
    r"(?:(?P<key>[A-Za-z0-9_\-]+)\s*[|｜]\s*)?"
    r"(?P<title>.+?)"
    r"[:：]?"
    r"\*\*"
    r"[:：]?\s*"
    r"(?P<detail>.+?)\s*$"
)
_MISCONCEPTION_LINE = re.compile(
    r"^[-*]\s+"
    r"\*\*误区[:：]?\*\*\s*"
    r"(?P<myth>.+?)\s+"
    r"\*\*为什么错[:：]?\*\*\s*"
    r"(?P<reason>.+?)\s+"
    r"\*\*(?:正确理解|正解)[:：]?\*\*\s*"
    r"(?P<truth>.+?)\s*$"
)


def _clean(value: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized[:limit]


def _label_value(
    content: str,
    labels: tuple[str, ...],
    limit: int,
) -> str:
    expected = {label.lower() for label in labels}

    for line in content.splitlines():
        match = _LABEL_LINE.match(line.strip())
        if not match:
            continue

        label = match.group("label").strip().lower()
        if label in expected:
            return _clean(match.group("value"), limit)

    return ""


def _extract_notes(content: str) -> str:
    notes: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue

        text = stripped[1:].strip()
        text = re.sub(r"^(?:讲稿|开场讲稿)[:：]\s*", "", text)
        if text:
            notes.append(text)

    return _clean(" ".join(notes), 700)


def _extract_points(content: str) -> list[KeyPoint]:
    points: list[KeyPoint] = []

    for line in content.splitlines():
        match = _POINT_LINE.match(line.strip())
        if not match:
            continue

        label = _clean(match.group("label").rstrip("：:"), 32)

        if label.lower() in {"误区", "myth"}:
            continue

        points.append(
            KeyPoint(
                label=label,
                detail=_clean(match.group("detail"), 220),
            )
        )

    return points[:6]


def _extract_steps(content: str) -> list[ProcessStep]:
    steps: list[ProcessStep] = []

    for line in content.splitlines():
        match = _STEP_LINE.match(line.strip())
        if not match:
            continue

        raw_key = match.group("key") or str(len(steps) + 1)

        steps.append(
            ProcessStep(
                key=_clean(raw_key, 20),
                title=_clean(match.group("title").rstrip("：:"), 40),
                detail=_clean(match.group("detail"), 220),
            )
        )

    return steps[:7]


def _extract_table(content: str) -> ComparisonTable:
    table_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("|")
    ]

    if len(table_lines) < 3:
        return ComparisonTable()

    separator = table_lines[1]
    if not re.match(r"^\|[\s:|\-]+\|$", separator):
        return ComparisonTable()

    def parse_cells(line: str) -> list[str]:
        return [_clean(cell, 120) for cell in line.strip("|").split("|")]

    headers = parse_cells(table_lines[0])[:6]
    rows: list[list[str]] = []

    for line in table_lines[2:8]:
        row = parse_cells(line)
        if len(row) == len(headers):
            rows.append(row)

    return ComparisonTable(headers=headers, rows=rows)


def _extract_misconceptions(content: str) -> list[MisconceptionItem]:
    misconceptions: list[MisconceptionItem] = []

    for line in content.splitlines():
        match = _MISCONCEPTION_LINE.match(line.strip())
        if not match:
            continue

        misconceptions.append(
            MisconceptionItem(
                myth=_clean(match.group("myth"), 140),
                reason=_clean(match.group("reason"), 180),
                truth=_clean(match.group("truth"), 180),
            )
        )

    return misconceptions[:4]


def _extract_branches(content: str) -> list[KnowledgeBranch]:
    branches: list[KnowledgeBranch] = []

    for point in _extract_points(content):
        keywords = [
            _clean(item, 24)
            for item in re.split(r"[、,，/|｜]", point.detail)
            if item.strip()
        ][:6]

        if keywords:
            branches.append(KnowledgeBranch(label=point.label, keywords=keywords))

    return branches[:7]


def _extract_keywords(text: str, limit: int = 6) -> list[str]:
    return [
        _clean(item, 24)
        for item in re.split(r"[、,，]", text)
        if item.strip()
    ][:limit]


def _extract_cover_meta(content: str) -> CoverMeta:
    return CoverMeta(
        presenter=_label_value(content, ("授课教师", "授课老师", "汇报人", "讲授人", "作者"), 40),
        organization=_label_value(content, ("课程章节", "课程", "章节", "单位", "学院"), 60),
        date=_label_value(content, ("授课时间", "日期", "时间"), 30),
        keywords=_extract_keywords(_label_value(content, ("关键词", "keywords"), 160)),
    )


def _parse_slide(block: str, index: int) -> PPTSlide:
    heading_match = _SLIDE_HEADING.search(block)

    if not heading_match:
        raise PPTCompileError(
            "missing '## [type] title' heading",
            slide_index=index,
        )

    raw_type = heading_match.group(1)
    title = heading_match.group(2)

    if raw_type not in SLIDE_TYPES:
        raise PPTCompileError(
            f"unknown slide type: {raw_type}",
            slide_index=index,
        )

    slide_type = cast(SlideType, raw_type)
    content = block[heading_match.end() :].strip()

    statement = _label_value(content, ("核心观点", "核心问题", "定义"), 180)
    question = _label_value(content, ("核心问题", "问题"), 180)
    takeaway = _label_value(content, ("总结金句", "结论", "takeaway"), 160)

    points = (
        _extract_points(content)
        if slide_type
        in {
            "learning_goals",
            "hook_question",
            "definition",
            "concept_boundary",
            "knowledge_explain",
        }
        else []
    )

    steps = (
        _extract_steps(content)
        if slide_type in {"agenda", "mechanism_overview"}
        else []
    )

    table = (
        _extract_table(content)
        if slide_type in {"concept_boundary", "comparison"}
        else ComparisonTable()
    )

    if slide_type == "concept_boundary" and table.rows and points:
        raise PPTCompileError(
            "concept_boundary must use either bullet points or a table, not both",
            slide_index=index,
        )

    try:
        return PPTSlide(
            type=slide_type,
            title=_clean(title, 64),
            subtitle=_label_value(content, ("副标题", "subtitle"), 120),
            eyebrow=_label_value(content, ("页眉", "eyebrow"), 32),
            statement=statement,
            question=question,
            points=points,
            steps=steps,
            table=table,
            misconceptions=(
                _extract_misconceptions(content)
                if slide_type == "misconception"
                else []
            ),
            branches=_extract_branches(content) if slide_type == "knowledge_map" else [],
            takeaway=takeaway,
            speaker_notes=_extract_notes(content),
            cover_meta=_extract_cover_meta(content) if slide_type == "cover" else CoverMeta(),
            animation=DEFAULT_ANIMATION[slide_type],  # type: ignore[arg-type]
        )
    except ValueError as exc:
        raise PPTCompileError(str(exc), slide_index=index) from exc


def _extract_global_metadata(markdown: str) -> dict[str, str | list[str]]:
    prefix = _SLIDE_SEPARATOR.split(markdown, maxsplit=1)[0]

    title_match = re.search(r"^#\s+(.+)$", prefix, re.MULTILINE)
    title = _clean(title_match.group(1), 72) if title_match else "教学课件"

    return {
        "title": title,
        "subtitle": _label_value(prefix, ("副标题", "subtitle"), 120),
        "purpose": _label_value(prefix, ("教学目的", "目的", "purpose"), 220)
        or f"系统讲解{title}",
        "audience": _label_value(prefix, ("目标受众", "受众", "audience"), 140)
        or "高校本科学生",
        "narrative": _label_value(prefix, ("叙事主线", "主线", "narrative"), 600)
        or f"围绕{title}建立完整知识结构",
        "keywords": _extract_keywords(_label_value(prefix, ("关键词", "keywords"), 180)),
    }


def compile_ppt_plan(
    markdown: str,
    *,
    density: DensityMode = "reading_first",
    template_family: str = "auto",
    template_scheme: str = "auto",
) -> PPTPlan:
    if not markdown.strip():
        raise PPTCompileError("LLM returned empty Markdown")

    metadata = _extract_global_metadata(markdown)
    blocks = _SLIDE_SEPARATOR.split(markdown)
    slide_blocks = [block.strip() for block in blocks if _SLIDE_HEADING.search(block)]

    if not 14 <= len(slide_blocks) <= 18:
        raise PPTCompileError(f"expected 14-18 slides, got {len(slide_blocks)}")

    slides = [_parse_slide(block, index) for index, block in enumerate(slide_blocks)]

    try:
        return PPTPlan(
            title=str(metadata["title"]),
            subtitle=str(metadata["subtitle"]),
            purpose=str(metadata["purpose"]),
            audience=str(metadata["audience"]),
            narrative=str(metadata["narrative"]),
            density=density,
            template_preference=PPTTemplatePreference(
                family=template_family,
                scheme=template_scheme,
                keywords=metadata["keywords"],
            ),
            slides=slides,
        )
    except ValueError as exc:
        raise PPTCompileError(str(exc)) from exc