from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


DensityMode = Literal["speaker_led", "reading_first"]
SlideRole = Literal[
    "cover",
    "section",
    "hook",
    "explain",
    "derive",
    "case",
    "practice",
    "summary",
    "closing",
]
ContentShape = Literal[
    "statement",
    "concept",
    "sequence",
    "comparison",
    "system",
    "code",
    "formula",
    "quiz",
    "misconception",  # 新增：误区纠正
    "hierarchy",      # 新增：层级结构
    "timeline",       # 新增：时间线
    "matrix",         # 新增：矩阵表格
]
AnimationKind = Literal["reveal", "focus", "trace", "compare", "build", "resolve"]
TemplateFamily = Literal["auto", "editorial", "technical"]
ColorScheme = Literal["auto", "light", "dark"]


class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PPTSource(PPTModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


class PPTPreferences(PPTModel):
    """用户可配置的 PPT 内容与视觉偏好。"""
    template: str = Field(
        default="auto",
        min_length=1,
        max_length=64,
        pattern=r"^(auto|[a-z0-9]+(?:-[a-z0-9]+)*)$",
    )
    explanation_style: Literal["concept", "case_driven", "problem_led", "review"] = "concept"
    density: Literal["concise", "standard", "detailed"] = "standard"
    focus: list[Literal["core_concepts", "cases", "pitfalls", "derivation"]] = Field(
        default_factory=lambda: ["core_concepts"],
        min_length=1,
    )


class ResourcePPTRequest(PPTModel):
    learning_need: str = Field(min_length=1)
    learning_scenario: str = Field(min_length=1)
    profile: dict[str, Any] | str
    teaching_plan: str | None
    artifacts: list[PPTSource] = Field(default_factory=list)
    preferences: PPTPreferences = Field(
        default_factory=PPTPreferences
    )


class PathPPTRequest(PPTModel):
    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str
    artifacts: list[PPTSource] = Field(default_factory=list)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)
    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    generation_focus: list[str] = Field(default_factory=list)
    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = Field(min_length=1)
    tutorial_markdown: str = Field(min_length=1)


class PPTTemplatePreference(PPTModel):
    family: TemplateFamily = "auto"
    scheme: ColorScheme = "auto"
    keywords: list[str] = Field(default_factory=list, max_length=6)


class KeyPoint(PPTModel):
    label: str = Field(min_length=1, max_length=28)
    detail: str = Field(min_length=1, max_length=200)  # 增加字数上限


class ProcessStep(PPTModel):
    title: str = Field(min_length=1, max_length=32)
    detail: str = Field(min_length=1, max_length=200)  # 增加字数上限


class ComparisonSide(PPTModel):
    title: str = Field(min_length=1, max_length=32)
    points: list[str] = Field(min_length=1, max_length=6)  # 增加点数上限


class SystemNode(PPTModel):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,23}$")
    label: str = Field(min_length=1, max_length=24)
    detail: str = Field(default="", max_length=120)  # 增加字数上限
    layer: str = Field(default="", max_length=20)

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip()
        if s and not s[0].isalpha():
            s = "n" + s
        import re
        s = re.sub(r"[^a-zA-Z0-9_-]", "_", s)
        return s[:24]

    @field_validator("layer", mode="before")
    @classmethod
    def serialize_layer(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class HierarchyNode(PPTModel):
    """层级结构节点（新增）"""
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,23}$")
    label: str = Field(min_length=1, max_length=28)
    detail: str = Field(default="", max_length=120)
    level: int = Field(default=0, ge=0, le=5)
    children: list[str] = Field(default_factory=list)


class TimelineEvent(PPTModel):
    """时间线事件（新增）"""
    time: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=32)
    detail: str = Field(default="", max_length=120)


class MatrixCell(PPTModel):
    """矩阵单元格（新增）"""
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=100)
    highlight: bool = Field(default=False)


class PPTSlide(PPTModel):
    role: SlideRole
    shape: ContentShape
    title: str = Field(min_length=1, max_length=54)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        mapping = {
            "code": "explain",
            "content": "explain",
            "system": "explain",
            "formula": "explain",
            "quiz": "practice",
            "sequence": "explain",
            "comparison": "explain",
            "misconception": "practice",
            "hierarchy": "explain",
            "timeline": "explain",
            "matrix": "explain",
        }
        return mapping.get(value, value)
    subtitle: str = Field(default="", max_length=110)
    eyebrow: str = Field(default="", max_length=28)
    statement: str = Field(default="", max_length=150)
    points: list[KeyPoint] = Field(default_factory=list, max_length=6)
    steps: list[ProcessStep] = Field(default_factory=list, max_length=6)
    comparison: list[ComparisonSide] = Field(default_factory=list, max_length=2)
    nodes: list[SystemNode] = Field(default_factory=list, max_length=8)
    code: str = Field(default="", max_length=1800)
    code_language: str = Field(default="", max_length=20)
    formula: str = Field(default="", max_length=160)
    question: str = Field(default="", max_length=160)
    answer: str = Field(default="", max_length=180)
    takeaway: str = Field(default="", max_length=140)
    speaker_notes: str = Field(default="", max_length=500)
    animation: AnimationKind = "reveal"
    preferred_layout: str = Field(default="", max_length=40)

    # 新增字段
    hierarchy: list[HierarchyNode] = Field(default_factory=list, max_length=10)
    timeline: list[TimelineEvent] = Field(default_factory=list, max_length=8)
    matrix: list[MatrixCell] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_shape_content(self) -> "PPTSlide":
        """Soft validation: log missing content but don't block compilation."""
        # 编译器可能调整 shape，内容不一定完全匹配，不再强制报错
        return self

    @model_validator(mode="after")
    def validate_statement_and_takeaway(self) -> "PPTSlide":
        """Soft validation: statement/takeaway recommended but not mandatory."""
        # 编译器/LLM 可能不总是提供 statement 和 takeaway，
        # 渲染器会用 title/question 作为 fallback，不再强制报错
        return self


class PPTPlan(PPTModel):
    title: str = Field(min_length=1, max_length=64)
    subtitle: str = Field(default="", max_length=120)
    purpose: str = Field(min_length=1, max_length=180)
    audience: str = Field(min_length=1, max_length=120)
    density: DensityMode
    narrative: str = Field(min_length=1, max_length=500)
    language: str = "zh-CN"
    template_preference: PPTTemplatePreference = Field(
        default_factory=PPTTemplatePreference
    )
    slides: list[PPTSlide] = Field(min_length=3, max_length=20)  # 增加上限到20

    @field_validator("slides", mode="before")
    @classmethod
    def deserialize_slides(cls, v: Any) -> Any:
        import json
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                pass
        return v

    @model_validator(mode="after")
    def validate_deck_rhythm(self) -> "PPTPlan":
        if self.slides[0].role != "cover":
            raise ValueError("the first slide must use the cover role")
        if self.slides[-1].role not in {"summary", "closing"}:
            raise ValueError("the final slide must summarize or close the lesson")
        return self


class PPTArtifact(PPTModel):
    path: Path
    plan: PPTPlan
    template_id: str
    template_name: str
    slide_count: int
