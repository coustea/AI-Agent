"""PPT 数据契约定义。

本模块定义教学课件的语义数据结构（SlideIntent），遵循多媒体学习原则，
专注于计算机理论的学术语义，由前端 LayoutDecisionEngine 自主决定布局排版。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ThemeId = Literal["technical-blueprint", "editorial-academic", "modern-classroom"]
ExplanationStyle = Literal["conceptual", "procedural", "comparative"]
VisualEmphasis = Literal["minimal", "balanced", "rich"]

SlideRole = Literal[
    "cover",
    "section",
    "definition",
    "concept",
    "hierarchy",
    "architecture",
    "state_transition",
    "sequence",
    "data_flow",
    "protocol_stack",
    "process",
    "comparison",
    "cause_effect",
    "worked_example",
    "knowledge_map",
    "ending",
]


class ContentElement(BaseModel):
    """Slide 内部的教学内容元素"""
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "concept",
        "definition",
        "statement",
        "step",
        "entity",
        "metric",
        "hierarchy_node",
        "state_node",
        "sequence_participant",
        "process_node",
        "formula",
        "image",
        "icon",
        "table",
        "quote",
        "code",
    ]
    content: str | None = Field(default=None, max_length=500)
    label: str | None = Field(default=None, max_length=64)
    properties: dict[str, Any] | list[Any] | None = Field(default=None)


class Relation(BaseModel):
    """内容元素之间的关系定义"""
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "parent_child",
        "dependency",
        "transition",
        "sequence",
        "data_flow",
        "comparison",
        "cause_effect",
        "association",
    ]
    source: str
    target: str
    label: str | None = Field(default=None, max_length=64)


class SlideIntent(BaseModel):
    """Slide 教学语义意图，不定义具体 Slot 坐标与版式"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^slide-[0-9]{2}$")
    role: SlideRole
    title: str = Field(min_length=2, max_length=64)
    key_message: str = Field(min_length=4, max_length=120)
    elements: list[ContentElement] = Field(min_length=1)
    relations: list[Relation] | None = Field(default=None)
    density: Literal["light", "medium", "dense"] = "medium"
    visual_hints: dict[str, Any] | None = Field(default=None)


class PptDocument(BaseModel):
    """重构后的完整 PPT 教学语义文档模型"""
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["teaching-lesson"]
    theme_id: ThemeId
    explanation_style: ExplanationStyle
    visual_emphasis: VisualEmphasis
    title: str = Field(min_length=2, max_length=64)
    audience: str = Field(min_length=2, max_length=60)
    slides: list[SlideIntent] = Field(min_length=2)


PPT_MANIFEST_PATH = Path(__file__).resolve().parent / "templates" / "ppt_manifest.json"


@lru_cache(maxsize=1)
def load_ppt_manifest() -> dict[str, Any]:
    return json.loads(PPT_MANIFEST_PATH.read_text(encoding="utf-8"))