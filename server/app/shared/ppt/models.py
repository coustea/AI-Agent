from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DensityMode = Literal["speaker_led", "reading_first"]

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
    template: str = Field(
        default="auto",
        min_length=1,
        max_length=64,
        pattern=r"^(auto|[a-z0-9]+(?:-[a-z0-9]+)*)$",
    )

    explanation_style: Literal[
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

    focus: list[
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


class ResourcePPTRequest(PPTModel):
    learning_need: str = Field(min_length=1)
    learning_scenario: str = Field(min_length=1)
    profile: dict[str, Any] | str
    teaching_plan: str | None = None
    artifacts: list[PPTSource] = Field(default_factory=list, max_length=16)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class PathPPTRequest(PPTModel):
    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    artifacts: list[PPTSource] = Field(default_factory=list, max_length=16)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)

    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)

    knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    generation_focus: list[str] = Field(default_factory=list, max_length=12)

    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = Field(min_length=1)
    tutorial_markdown: str = Field(min_length=1)


class PPTTemplatePreference(PPTModel):
    family: TemplateFamily = "auto"
    scheme: ColorScheme = "auto"
    keywords: list[str] = Field(default_factory=list, max_length=6)


class KeyPoint(PPTModel):
    label: str = Field(min_length=1, max_length=32)
    detail: str = Field(min_length=1, max_length=220)


class ProcessStep(PPTModel):
    key: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=40)
    detail: str = Field(min_length=1, max_length=220)


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
    myth: str = Field(min_length=1, max_length=140)
    reason: str = Field(min_length=1, max_length=180)
    truth: str = Field(min_length=1, max_length=180)


class KnowledgeBranch(PPTModel):
    label: str = Field(min_length=1, max_length=32)
    keywords: list[str] = Field(min_length=1, max_length=6)


class CoverMeta(PPTModel):
    presenter: str = Field(default="", max_length=40)
    organization: str = Field(default="", max_length=60)
    date: str = Field(default="", max_length=30)
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
    cover_meta: CoverMeta = Field(default_factory=CoverMeta)

    animation: AnimationKind = "reveal"

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

        return self


class PPTPlan(PPTModel):
    title: str = Field(min_length=1, max_length=72)
    subtitle: str = Field(default="", max_length=120)
    purpose: str = Field(min_length=1, max_length=220)
    audience: str = Field(min_length=1, max_length=140)
    narrative: str = Field(min_length=1, max_length=600)

    density: DensityMode = "reading_first"
    language: str = "zh-CN"
    template_preference: PPTTemplatePreference = Field(default_factory=PPTTemplatePreference)

    slides: list[PPTSlide] = Field(min_length=14, max_length=18)

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

        if middle.count("knowledge_explain") < 3:
            raise ValueError("teaching deck requires at least three knowledge_explain slides")

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
    path: Path
    plan: PPTPlan
    plan_markdown: str = ""
    template_id: str
    template_name: str
    slide_count: int