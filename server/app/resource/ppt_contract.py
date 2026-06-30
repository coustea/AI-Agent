"""PPT 数据契约定义 - 完全对齐前端 TypeScript 类型。

本模块定义教学课件的布局驱动数据结构，直接映射到前端 PptSlide 和 PPTDocument 类型。
前端负责样式渲染，后端只负责内容组织和槽位分配。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# === 对齐前端的类型定义 ===

ThemeType = Literal["logic-blue", "paper-light", "lab-light"]

LayoutId = Literal[
    "HeroCover",
    "DualPane",
    "TriplePane",
    "DiagramFocus",
    "FlowCanvas",
    "CompareTable",
    "CardCluster",
    "KnowledgeMap",
]

SlideRole = Literal[
    "cover",
    "objectives",
    "prerequisite",
    "problem_intro",
    "roadmap",
    "concept",
    "analogy",
    "principle_diagram",
    "process_demo",
    "mechanism_breakdown",
    "concept_relation",
    "concept_compare",
    "misconception",
    "summary",
    "next_steps",
    "algorithm_visualization",
    "code_walkthrough",
    "architecture_diagram",
]

BlockType = Literal[
    "Text",
    "Callout",
    "KeyPoint",
    "Diagram",
    "FlowChart",
    "Table",
    "CardList",
    "Formula",
    "CodeSnippet",
]


# === Block 定义（对齐前端 SlideBlock 类型）===

class BaseBlock(BaseModel):
    """Block 基类"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: BlockType


class TextBlock(BaseModel):
    """文本块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["Text"]
    content: str = Field(min_length=1)
    format: Literal["plain", "markdown"] = "plain"


class CalloutBlock(BaseModel):
    """提示框块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["Callout"]
    intent: Literal["info", "warning", "success", "danger"]
    icon: str = Field(min_length=1)
    content: str = Field(min_length=1)


class KeyPointBlock(BaseModel):
    """关键点块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["KeyPoint"]
    label: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DiagramNode(BaseModel):
    """图节点"""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class DiagramEdge(BaseModel):
    """图边"""
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    label: str | None = None


class DiagramBlock(BaseModel):
    """结构图块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["Diagram"]
    direction: Literal["LR", "TB", "RL", "BT"]
    nodes: list[DiagramNode] = Field(min_length=2)
    edges: list[DiagramEdge] = Field(min_length=1)


class FlowStep(BaseModel):
    """流程步骤"""
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    state_before: str | None = None
    state_after: str | None = None


class FlowChartBlock(BaseModel):
    """流程图块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["FlowChart"]
    steps: list[FlowStep] = Field(min_length=2)


class TableBlock(BaseModel):
    """表格块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["Table"]
    columns: list[str] = Field(min_length=2)
    rows: list[list[str]] = Field(min_length=1)

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v: list[list[str]], info) -> list[list[str]]:
        if info.data.get("columns"):
            col_count = len(info.data["columns"])
            for i, row in enumerate(v):
                if len(row) != col_count:
                    raise ValueError(f"第 {i+1} 行列数 {len(row)} 与表头列数 {col_count} 不匹配")
        return v


class CardItem(BaseModel):
    """卡片项"""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    icon: str | None = None


class CardListBlock(BaseModel):
    """卡片列表块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["CardList"]
    cards: list[CardItem] = Field(min_length=1)


class FormulaBlock(BaseModel):
    """公式块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["Formula"]
    formula: str = Field(min_length=1)


class CodeHighlight(BaseModel):
    """代码高亮"""
    model_config = ConfigDict(extra="forbid")

    line: int = Field(ge=1)
    note: str = Field(min_length=1)


class CodeSnippetBlock(BaseModel):
    """代码片段块"""
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(pattern=r"^block-[a-zA-Z0-9_-]+$")
    type: Literal["CodeSnippet"]
    language: str = Field(min_length=1)
    code: str = Field(min_length=1)
    highlights: list[CodeHighlight] = Field(default_factory=list)


# === PptSlide 定义（对齐前端）===

class PptSlide(BaseModel):
    """PPT 幻灯片 - 完全对齐前端 PptSlide 类型"""
    model_config = ConfigDict(extra="forbid")

    id: str | None = None  # 可选，前端自动生成
    index: int | None = None  # 可选，前端自动计算
    role: SlideRole
    title: str
    subtitle: str | None = None
    layout: LayoutId | None = None  # 可选，前端根据 role 推断
    slots: dict[str, list[dict[str, Any]]]  # 槽位映射到 block 列表
    takeaway: str
    speaker_notes: str | None = None

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, v: dict[str, list]) -> dict[str, list]:
        """验证 slots 非空"""
        if not v:
            raise ValueError("slots 不能为空")
        for slot_name, blocks in v.items():
            if not isinstance(blocks, list) or len(blocks) == 0:
                raise ValueError(f"slots['{slot_name}'] 必须是非空数组")
        return v


# === PPTDocument 定义（对齐前端）===

class PPTDocument(BaseModel):
    """PPT 文档 - 完全对齐前端 PPTDocument 类型"""
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["teaching-lesson"] = "teaching-lesson"
    theme_id: ThemeType = "logic-blue"
    title: str
    audience: str
    slides: list[PptSlide] = Field(min_length=6, max_length=16)

    @field_validator("slides")
    @classmethod
    def validate_slides_structure(cls, v: list[PptSlide]) -> list[PptSlide]:
        """验证幻灯片结构"""
        if len(v) < 6:
            raise ValueError(f"幻灯片数量 {len(v)} 少于最小要求 6 页")
        if len(v) > 16:
            raise ValueError(f"幻灯片数量 {len(v)} 超过最大限制 16 页")
        return v


# === 辅助函数 ===

PPT_MANIFEST_PATH = Path(__file__).resolve().parent / "templates" / "ppt_manifest.json"


@lru_cache(maxsize=1)
def load_ppt_manifest() -> dict[str, Any]:
    """加载 PPT manifest（前端布局配置）"""
    return json.loads(PPT_MANIFEST_PATH.read_text(encoding="utf-8"))
