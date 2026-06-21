"""PPT 数据契约定义。

本模块定义教学课件的数据结构，严格遵循多媒体学习原则，
专注于讲解而非练习，减少认知负担。

SlideRole 遵循教学流程顺序：
1. cover - 封面
2. objectives - 学习目标
3. prerequisite - 前置知识
4. problem_intro - 问题导入
5. roadmap - 知识路线图
6. concept - 核心概念讲解
7. analogy - 直观类比解释
8. principle_diagram - 原理图解
9. process_demo - 过程演示
10. mechanism_breakdown - 关键机制拆解
11. concept_relation - 概念关系梳理
12. concept_compare - 易混概念对比
13. misconception - 常见误解纠正
14. summary - 知识框架总结
15. next_steps - 后续知识衔接
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Difficulty = Literal["beginner", "intermediate", "advanced"]
LessonDepth = Literal["quick", "standard", "deep"]
ThemeId = Literal["logic-blue", "paper-light", "lab-light"]

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
    # Computer theory teaching roles
    "algorithm_visualization",
    "code_walkthrough",
    "architecture_diagram",
]

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

PPT_MANIFEST_PATH = Path(__file__).resolve().parent / "templates" / "ppt_manifest.json"


class TextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["Text"]
    content: str = Field(min_length=1, max_length=120)
    format: Literal["plain", "markdown"] = "plain"


class CalloutBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["Callout"]
    intent: Literal["info", "warning", "success", "danger"]
    icon: str = Field(min_length=1, max_length=4)
    content: str = Field(min_length=1, max_length=100)


class KeyPointBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["KeyPoint"]
    label: str = Field(min_length=1, max_length=16)
    content: str = Field(min_length=1, max_length=48)


class DiagramNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=24)
    label: str = Field(min_length=1, max_length=36)


class DiagramEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=24)
    target: str = Field(min_length=1, max_length=24)
    label: str | None = Field(default=None, max_length=24)


class DiagramBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["Diagram"]
    direction: Literal["LR", "TB", "RL", "BT"]
    nodes: list[DiagramNode] = Field(min_length=2, max_length=8)
    edges: list[DiagramEdge] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_graph(self) -> "DiagramBlock":
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("diagram node IDs must be unique")
        allowed = set(ids)
        for edge in self.edges:
            if edge.source not in allowed or edge.target not in allowed:
                raise ValueError("diagram edge endpoints must exist")
        return self


class FlowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=16)
    title: str = Field(min_length=1, max_length=36)
    description: str = Field(min_length=1, max_length=72)
    state_before: str | None = Field(default=None, max_length=48)
    state_after: str | None = Field(default=None, max_length=48)


class FlowChartBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["FlowChart"]
    steps: list[FlowStep] = Field(min_length=3, max_length=6)

    @model_validator(mode="after")
    def validate_steps(self) -> "FlowChartBlock":
        ids = [step.step_id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("flow step IDs must be unique")
        return self


class TableBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["Table"]
    columns: list[str] = Field(min_length=2, max_length=4)
    rows: list[list[str]] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def validate_table(self) -> "TableBlock":
        if any(not column.strip() for column in self.columns):
            raise ValueError("table columns must be non-empty")
        width = len(self.columns)
        if any(len(row) != width for row in self.rows):
            raise ValueError("every row cell count must match columns")
        if any(not cell.strip() for row in self.rows for cell in row):
            raise ValueError("table cells must be non-empty")
        return self


class CardItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=24)
    content: str = Field(min_length=1, max_length=72)
    icon: str | None = Field(default=None, max_length=4)


class CardListBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["CardList"]
    cards: list[CardItem] = Field(min_length=2, max_length=5)


class FormulaBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["Formula"]
    formula: str = Field(min_length=1, max_length=120)


class CodeHighlight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=48)


class CodeSnippetBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    type: Literal["CodeSnippet"]
    language: str = Field(min_length=1, max_length=24)
    code: str = Field(min_length=1)
    highlights: list[CodeHighlight] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_code(self) -> "CodeSnippetBlock":
        lines = [line for line in self.code.splitlines() if line.strip()]
        if not 1 <= len(lines) <= 20:
            raise ValueError("code must contain 1 to 20 non-empty lines")
        if any(h.line > len(lines) for h in self.highlights):
            raise ValueError("highlight line must be within code line count")
        return self


SlideBlock = (
    TextBlock
    | CalloutBlock
    | KeyPointBlock
    | DiagramBlock
    | FlowChartBlock
    | TableBlock
    | CardListBlock
    | FormulaBlock
    | CodeSnippetBlock
)


class PptSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^slide-[0-9]{2}$")
    index: int = Field(ge=1, le=16)
    role: SlideRole
    title: str = Field(min_length=2, max_length=32)
    subtitle: str | None = Field(default=None, max_length=48)
    layout: LayoutId
    slots: dict[str, list[SlideBlock]]
    takeaway: str = Field(min_length=1, max_length=60)
    speaker_notes: str = Field(min_length=10, max_length=140)

    @model_validator(mode="after")
    def validate_slots(self) -> "PptSlide":
        if not self.slots:
            raise ValueError("slide must have at least one slot")
        for slot_name, blocks in self.slots.items():
            if not blocks:
                raise ValueError(f"slot {slot_name} cannot be empty")
        return self


class PptDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["teaching-lesson"]
    theme_id: ThemeId
    title: str = Field(min_length=2, max_length=32)
    audience: str = Field(min_length=2, max_length=60)
    slides: list[PptSlide] = Field(min_length=6, max_length=16)

    @model_validator(mode="after")
    def validate_structure(self) -> "PptDocument":
        indexes = [slide.index for slide in self.slides]
        if indexes != list(range(1, len(self.slides) + 1)):
            raise ValueError("slide indexes must be contiguous from 1")
        ids = [slide.id for slide in self.slides]
        if len(ids) != len(set(ids)):
            raise ValueError("slide IDs must be unique")
        roles = [slide.role for slide in self.slides]
        if roles[0] != "cover":
            raise ValueError("deck must start with cover")
        if roles[-1] != "summary":
            raise ValueError("deck must end with summary")
        return self


class BlockBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_chars: int | None = Field(default=None, ge=1, le=240)
    max_lines: int | None = Field(default=None, ge=1, le=24)
    min_items: int | None = Field(default=None, ge=1, le=8)
    max_items: int | None = Field(default=None, ge=1, le=8)
    min_columns: int | None = Field(default=None, ge=2, le=4)
    max_columns: int | None = Field(default=None, ge=2, le=4)
    min_rows: int | None = Field(default=None, ge=2, le=6)
    max_rows: int | None = Field(default=None, ge=2, le=6)


class CompiledBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    slot: str
    type: BlockType
    instruction: str
    budget: BlockBudget


class CompiledSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slide_id: str
    index: int
    role: SlideRole
    title: str
    subtitle: str | None
    teaching_intent: str = Field(min_length=8, max_length=100)
    unique_value: str = Field(min_length=4, max_length=60)
    layout: LayoutId
    blocks: list[CompiledBlock]


class CompiledChapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=24)
    objective: str = Field(min_length=8, max_length=100)
    slides: list[CompiledSlide] = Field(min_length=1, max_length=4)


class CompiledDeck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["teaching-lesson"]
    theme_id: ThemeId
    title: str
    audience: str
    chapters: list[CompiledChapter] = Field(min_length=2, max_length=4)


class SlideContentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slide_id: str
    blocks: list[SlideBlock] = Field(min_length=1)
    takeaway: str = Field(min_length=1, max_length=60)
    speaker_notes: str = Field(min_length=10, max_length=140)


class ChapterDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str
    slides: list[SlideContentDraft] = Field(min_length=1, max_length=4)


class SlideBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slide_id: str = Field(pattern=r"^slide-[0-9]{2}$")
    index: int = Field(ge=1, le=16)
    role: SlideRole
    title: str = Field(min_length=2, max_length=32)
    subtitle: str | None = Field(default=None, max_length=48)
    teaching_intent: str = Field(min_length=8, max_length=100)
    unique_value: str = Field(min_length=4, max_length=60)
    composition_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_role(self) -> "SlideBlueprint":
        valid_roles = {
            "cover", "objectives", "prerequisite", "problem_intro", "roadmap",
            "concept", "analogy", "principle_diagram", "process_demo",
            "mechanism_breakdown", "concept_relation", "concept_compare",
            "misconception", "summary", "next_steps",
        }
        if self.role not in valid_roles:
            raise ValueError(f"invalid role: {self.role}")
        return self


class ChapterBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=24)
    objective: str = Field(min_length=8, max_length=100)
    slides: list[SlideBlueprint] = Field(min_length=1, max_length=4)


class DeckBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: Literal["teaching-lesson"]
    theme_id: ThemeId
    title: str = Field(min_length=2, max_length=32)
    audience: str = Field(min_length=2, max_length=60)
    narrative: str = Field(min_length=10, max_length=180)
    primary_example: str = Field(min_length=4, max_length=100)
    terminology: dict[str, str] = Field(min_length=1, max_length=12)
    chapters: list[ChapterBlueprint] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def validate_structure(self) -> "DeckBlueprint":
        slides = [slide for chapter in self.chapters for slide in chapter.slides]
        indexes = [slide.index for slide in slides]
        if indexes != list(range(1, len(slides) + 1)):
            raise ValueError("slide indexes must be contiguous from 1")
        ids = [slide.slide_id for slide in slides]
        if len(ids) != len(set(ids)):
            raise ValueError("slide IDs must be unique")
        titles = [slide.title.strip().casefold() for slide in slides]
        if len(titles) != len(set(titles)):
            raise ValueError("slide titles must be unique")
        if slides[0].role != "cover":
            raise ValueError("deck must start with cover")
        if slides[-1].role != "summary":
            raise ValueError("deck must end with summary")
        return self


@lru_cache(maxsize=1)
def load_ppt_manifest() -> dict[str, Any]:
    return json.loads(PPT_MANIFEST_PATH.read_text(encoding="utf-8"))


def depth_page_range(depth: LessonDepth) -> range:
    return {
        "quick": range(6, 9),
        "standard": range(9, 13),
        "deep": range(13, 17),
    }[depth]


def validate_blueprint(blueprint: DeckBlueprint, depth: LessonDepth) -> None:
    slide_count = sum(len(chapter.slides) for chapter in blueprint.chapters)
    if slide_count not in depth_page_range(depth):
        raise ValueError(f"slide count {slide_count} is invalid for depth {depth}")
    slides = [slide for chapter in blueprint.chapters for slide in chapter.slides]
    if slides[0].role != "cover" or slides[-1].role != "summary":
        raise ValueError("deck must start with cover and end with summary")


def compile_deck(blueprint: DeckBlueprint) -> CompiledDeck:
    """将蓝图编译为带有 block 声明的编译结构。

    Args:
        blueprint: Director 生成的课件蓝图

    Returns:
        CompiledDeck: 包含所有 block 声明的编译结构
    """
    manifest = load_ppt_manifest()
    compositions = manifest["compositions"]

    compiled_chapters: list[CompiledChapter] = []
    for chapter in blueprint.chapters:
        compiled_slides: list[CompiledSlide] = []
        for slide in chapter.slides:
            composition = compositions.get(slide.composition_id)
            if not composition:
                raise ValueError(f"unknown composition {slide.composition_id}")
            if slide.role not in composition["allowed_roles"]:
                raise ValueError(f"role {slide.role} not allowed by composition {slide.composition_id}")
            layout = composition["layout"]
            blocks = [
                CompiledBlock(
                    block_id=block["block_id"],
                    slot=block["slot"],
                    type=block["type"],
                    instruction=block["instruction"],
                    budget=BlockBudget.model_validate(block["budget"]),
                )
                for block in composition["blocks"]
            ]
            compiled_slides.append(
                CompiledSlide(
                    slide_id=slide.slide_id,
                    index=slide.index,
                    role=slide.role,
                    title=slide.title,
                    subtitle=slide.subtitle,
                    teaching_intent=slide.teaching_intent,
                    unique_value=slide.unique_value,
                    layout=layout,
                    blocks=blocks,
                )
            )
        compiled_chapters.append(
            CompiledChapter(
                chapter_id=chapter.chapter_id,
                title=chapter.title,
                objective=chapter.objective,
                slides=compiled_slides,
            )
        )

    return CompiledDeck(
        template_id=blueprint.template_id,
        theme_id=blueprint.theme_id,
        title=blueprint.title,
        audience=blueprint.audience,
        chapters=compiled_chapters,
    )


def _layout_slot_keys(layout: LayoutId) -> list[str]:
    manifest = load_ppt_manifest()
    return list(manifest["layouts"][layout]["slots"])


def _block_type_name(block: SlideBlock) -> str:
    return getattr(block, "type")


def _validate_block_budget(block: SlideBlock, budget: BlockBudget) -> None:
    """验证 block 内容是否符合预算约束。"""
    block_type = _block_type_name(block)

    if block_type == "Text":
        if budget.max_chars is not None and len(block.content) > budget.max_chars:
            raise ValueError(f"Text block exceeds max_chars: {len(block.content)} > {budget.max_chars}")

    elif block_type == "Callout":
        if budget.max_chars is not None and len(block.content) > budget.max_chars:
            raise ValueError(f"Callout block exceeds max_chars: {len(block.content)} > {budget.max_chars}")

    elif block_type == "KeyPoint":
        if budget.max_chars is not None and len(block.content) > budget.max_chars:
            raise ValueError(f"KeyPoint block exceeds max_chars: {len(block.content)} > {budget.max_chars}")

    elif block_type == "Diagram":
        node_count = len(block.nodes)
        if budget.min_items is not None and node_count < budget.min_items:
            raise ValueError(f"Diagram below min_items: {node_count} < {budget.min_items}")
        if budget.max_items is not None and node_count > budget.max_items:
            raise ValueError(f"Diagram exceeds max_items: {node_count} > {budget.max_items}")

    elif block_type == "FlowChart":
        step_count = len(block.steps)
        if budget.min_items is not None and step_count < budget.min_items:
            raise ValueError(f"FlowChart below min_items: {step_count} < {budget.min_items}")
        if budget.max_items is not None and step_count > budget.max_items:
            raise ValueError(f"FlowChart exceeds max_items: {step_count} > {budget.max_items}")

    elif block_type == "Table":
        if budget.min_columns is not None and len(block.columns) < budget.min_columns:
            raise ValueError(f"Table below min_columns: {len(block.columns)} < {budget.min_columns}")
        if budget.max_columns is not None and len(block.columns) > budget.max_columns:
            raise ValueError(f"Table exceeds max_columns: {len(block.columns)} > {budget.max_columns}")
        if budget.min_rows is not None and len(block.rows) < budget.min_rows:
            raise ValueError(f"Table below min_rows: {len(block.rows)} < {budget.min_rows}")
        if budget.max_rows is not None and len(block.rows) > budget.max_rows:
            raise ValueError(f"Table exceeds max_rows: {len(block.rows)} > {budget.max_rows}")

    elif block_type == "CardList":
        card_count = len(block.cards)
        if budget.min_items is not None and card_count < budget.min_items:
            raise ValueError(f"CardList below min_items: {card_count} < {budget.min_items}")
        if budget.max_items is not None and card_count > budget.max_items:
            raise ValueError(f"CardList exceeds max_items: {card_count} > {budget.max_items}")

    elif block_type == "Formula":
        if budget.max_chars is not None and len(block.formula) > budget.max_chars:
            raise ValueError(f"Formula exceeds max_chars: {len(block.formula)} > {budget.max_chars}")

    elif block_type == "CodeSnippet":
        code_lines = [line for line in block.code.splitlines() if line.strip()]
        if budget.max_lines is not None and len(code_lines) > budget.max_lines:
            raise ValueError(f"CodeSnippet exceeds max_lines: {len(code_lines)} > {budget.max_lines}")


def assemble_document(compiled: CompiledDeck, drafts: list[ChapterDraft]) -> PptDocument:
    """将编译结构与章节草稿组装为最终文档。

    Args:
        compiled: 编译后的课件结构
        drafts: 各章节的内容草稿

    Returns:
        PptDocument: 最终的课件文档
    """
    draft_map = {draft.chapter_id: draft for draft in drafts}
    if len(draft_map) != len(drafts):
        raise ValueError("duplicate chapter drafts are not allowed")
    if set(draft_map) != {chapter.chapter_id for chapter in compiled.chapters}:
        raise ValueError("chapter drafts must match compiled chapters exactly")

    slides: list[PptSlide] = []
    for chapter in compiled.chapters:
        draft = draft_map.get(chapter.chapter_id)
        if draft is None:
            raise ValueError(f"missing chapter draft for {chapter.chapter_id}")
        draft_slide_map = {slide.slide_id: slide for slide in draft.slides}
        if len(draft_slide_map) != len(draft.slides):
            raise ValueError(f"duplicate slide drafts in chapter {chapter.chapter_id}")
        if set(draft_slide_map) != {slide.slide_id for slide in chapter.slides}:
            raise ValueError(f"chapter {chapter.chapter_id} slide IDs do not match compiled contract")
        for compiled_slide in chapter.slides:
            draft_slide = draft_slide_map[compiled_slide.slide_id]
            block_map = {block.block_id: block for block in draft_slide.blocks}
            if len(block_map) != len(draft_slide.blocks):
                raise ValueError(f"duplicate block IDs in slide {compiled_slide.slide_id}")
            expected_ids = [block.block_id for block in compiled_slide.blocks]
            if set(block_map) != set(expected_ids):
                raise ValueError(f"slide {compiled_slide.slide_id} block IDs do not match compiled contract")
            slots = {slot: [] for slot in _layout_slot_keys(compiled_slide.layout)}
            for expected in compiled_slide.blocks:
                block = block_map[expected.block_id]
                if _block_type_name(block) != expected.type:
                    raise ValueError(f"block {expected.block_id} expected type {expected.type}, got {_block_type_name(block)}")
                _validate_block_budget(block, expected.budget)
                slots[expected.slot].append(block)
            if any(not blocks for blocks in slots.values()):
                raise ValueError(f"slide {compiled_slide.slide_id} contains an empty slot")
            slides.append(
                PptSlide(
                    id=compiled_slide.slide_id,
                    index=compiled_slide.index,
                    role=compiled_slide.role,
                    title=compiled_slide.title,
                    subtitle=compiled_slide.subtitle,
                    layout=compiled_slide.layout,
                    slots=slots,
                    takeaway=draft_slide.takeaway,
                    speaker_notes=draft_slide.speaker_notes,
                )
            )

    return PptDocument(
        template_id=compiled.template_id,
        theme_id=compiled.theme_id,
        title=compiled.title,
        audience=compiled.audience,
        slides=slides,
    )