from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SlideType = Literal[
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
]

AnimationKind = Literal[
    "reveal",
    "focus",
    "trace",
    "compare",
    "build",
    "resolve",
]

TemplateFamily = Literal["auto", "teaching", "technical"]
ColorScheme = Literal["auto", "light", "dark"]


class PPTModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class PPTSource(PPTModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class PPTPreferences(PPTModel):
    """PPT 生成偏好 — 四项参数只影响大纲 LLM 内容输出。"""

    template: Literal[
        "auto",
        "teaching",
        "technical",
        "case_study",
        "exam_review",
    ] = "auto"

    narrative_style: Literal[
        "concept",
        "case_driven",
        "problem_led",
        "review",
    ] = "concept"

    density: Literal[
        "concise",
        "standard",
        "detailed",
    ] = "standard"

    emphasis: list[
        Literal[
            "core_concepts",
            "cases",
            "pitfalls",
            "derivation",
        ]
    ] = Field(
        default_factory=lambda: ["core_concepts"],
        min_length=1,
        max_length=4,
    )


class ResourcePPT(PPTModel):
    """资源生成 PPT 请求 — 字段对齐 ResourceInput。"""

    username: str = ""
    learning_need: str = Field(min_length=1)
    learning_scenario: str = "self_study"
    profile: dict[str, Any] | str = Field(default_factory=dict)
    teaching_plan: str | None = None
    artifacts: list[PPTSource] = Field(default_factory=list, max_length=16)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class PathPPT(PPTModel):
    """路径规划 PPT 请求。"""

    username: str = ""
    profile: dict[str, Any] | str = Field(default_factory=dict)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)

    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = "beginner"

    knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=24)

    # 教程核心内容（仅标题、摘要、知识点、核心知识点讲解部分）
    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = ""
    tutorial_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_core_content: str = Field(min_length=1)


class PPTTemplatePreference(PPTModel):
    family: TemplateFamily = "auto"
    scheme: ColorScheme = "auto"
    keywords: list[str] = Field(default_factory=list, max_length=6)


class KeyPoint(PPTModel):
    label: str = Field(min_length=1, max_length=32)
    detail: str = Field(min_length=16, max_length=220)


class ProcessStep(PPTModel):
    key: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=40)
    detail: str = Field(min_length=16, max_length=220)


class ComparisonTable(PPTModel):
    headers: list[str] = Field(default_factory=list, max_length=6)
    rows: list[list[str]] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_width(self) -> "ComparisonTable":
        if not self.headers and not self.rows:
            return self

        if len(self.headers) < 2:
            raise ValueError("comparison table requires at least two columns")

        width = len(self.headers)

        if any(len(row) != width for row in self.rows):
            raise ValueError("comparison table row width must match headers")

        return self


class MisconceptionItem(PPTModel):
    myth: str = Field(min_length=8, max_length=140)
    reason: str = Field(min_length=16, max_length=180)
    truth: str = Field(min_length=16, max_length=180)


class KnowledgeBranch(PPTModel):
    label: str = Field(min_length=1, max_length=32)
    keywords: list[str] = Field(min_length=1, max_length=6)


class CoverContent(PPTModel):
    """LLM 可生成的封面内容，不包含发布身份或时间。"""

    keywords: list[str] = Field(default_factory=list, max_length=6)


class PPTSlide(PPTModel):
    type: SlideType

    title: str = Field(min_length=1, max_length=64)
    subtitle: str = Field(default="", max_length=120)
    eyebrow: str = Field(default="", max_length=32)

    statement: str = Field(default="", max_length=180)
    question: str = Field(default="", max_length=180)

    points: list[KeyPoint] = Field(default_factory=list, max_length=6)
    steps: list[ProcessStep] = Field(default_factory=list, max_length=7)
    table: ComparisonTable = Field(default_factory=ComparisonTable)
    misconceptions: list[MisconceptionItem] = Field(default_factory=list, max_length=4)
    branches: list[KnowledgeBranch] = Field(default_factory=list, max_length=7)

    takeaway: str = Field(default="", max_length=160)
    speaker_notes: str = Field(default="", max_length=700)
    cover: CoverContent = Field(default_factory=CoverContent)

    @model_validator(mode="after")
    def validate_required_content(self) -> "PPTSlide":
        has_table = bool(self.table.headers and self.table.rows)

        required_content = {
            "cover": bool((self.question or self.statement) and self.subtitle),
            "agenda": bool(self.statement and self.steps),
            "learning_goals": bool(self.statement and self.points),
            "hook_question": bool((self.question or self.statement) and self.points),
            "definition": bool(self.statement and self.points),
            "concept_boundary": bool(self.statement and (self.points or has_table)),
            "mechanism_overview": bool(self.statement and self.steps),
            "knowledge_explain": bool(self.statement and self.points),
            "comparison": bool(self.statement and has_table),
            "misconception": bool(self.statement and self.misconceptions),
            "knowledge_map": bool(self.statement and self.branches),
            "closing": bool(self.statement and self.takeaway),
        }

        if not required_content[self.type]:
            raise ValueError(
                f"slide {self.type!r} is missing required teaching content"
            )

        minimum_items = {
            "agenda": 3,
            "learning_goals": 3,
            "hook_question": 3,
            "definition": 3,
            "concept_boundary": 2,
            "mechanism_overview": 3,
            "knowledge_explain": 3,
            "comparison": 2,
            "misconception": 2,
            "knowledge_map": 2,
        }
        item_count = {
            "agenda": len(self.steps),
            "learning_goals": len(self.points),
            "hook_question": len(self.points),
            "definition": len(self.points),
            "concept_boundary": max(len(self.points), len(self.table.rows)),
            "mechanism_overview": len(self.steps),
            "knowledge_explain": len(self.points),
            "comparison": len(self.table.rows),
            "misconception": len(self.misconceptions),
            "knowledge_map": len(self.branches),
        }

        required_count = minimum_items.get(self.type)
        if required_count and item_count[self.type] < required_count:
            raise ValueError(
                f"slide {self.type!r} needs at least {required_count} teaching items"
            )

        return self


class PPTPlan(PPTModel):
    title: str = Field(min_length=1, max_length=72)
    language: str = "zh-CN"
    template_preference: PPTTemplatePreference = Field(default_factory=PPTTemplatePreference)

    slides: list[PPTSlide] = Field(min_length=13, max_length=15)

    @model_validator(mode="after")
    def validate_teaching_rhythm(self) -> "PPTPlan":
        types = [slide.type for slide in self.slides]

        prefix = [
            "cover",
            "agenda",
            "learning_goals",
            "hook_question",
            "definition",
            "concept_boundary",
            "mechanism_overview",
        ]

        suffix = [
            "comparison",
            "misconception",
            "knowledge_map",
            "closing",
        ]

        if types[: len(prefix)] != prefix:
            raise ValueError(
                "teaching deck prefix must be: "
                f"{prefix}"
            )

        if types[-len(suffix) :] != suffix:
            raise ValueError(
                "teaching deck suffix must be: "
                f"{suffix}"
            )

        middle = types[len(prefix) : -len(suffix)]

        if middle.count("knowledge_explain") < 2:
            raise ValueError("teaching deck requires at least two knowledge_explain slides")

        unexpected = [
            slide_type
            for slide_type in middle
            if slide_type not in {"knowledge_explain", "concept_boundary"}
        ]

        if unexpected:
            raise ValueError(
                "middle teaching slides may only be knowledge_explain "
                f"or extra concept_boundary, got {unexpected}"
            )

        if middle.count("concept_boundary") > 1:
            raise ValueError("teaching deck allows at most one extra concept_boundary slide")

        return self


class PPTArtifact(PPTModel):
    title: str = Field(min_length=1)
    path: Path
    generated_at: datetime
    template_id: str
    template_name: str
    slide_count: int
    html_url: str = ""
