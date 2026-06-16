"""PPT 内部与最终输出模型 — 所有 Pydantic schema 集中定义。

包含:
  - 类型字面量 (ThemeType, LayoutType, BlockType, ResourceAgentId, SlideRole)
  - 前端最终载荷模型 (BaseBlock, Block*, SlideBlock, PptSlide, PptPayload)
  - 内部流水线模型 (MaterialArtifact, MaterialBundle, MaterialDigest,
    DeckConstraints, BlockContract, SlideContract, DeckOutline,
    RenderedBlock, SlideDraft)
  - 路径节点素材上下文 (NodeMaterialContext)
"""

from __future__ import annotations

from typing import Any, Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── 类型字面量 ──────────────────────────────────────────────────────────────

ThemeType = Literal["theme-mac-light", "theme-notion-light", "theme-logic-blue"]
LayoutType = Literal["FocusTitle", "SplitScreen", "BentoGrid", "LayerStack"]
BlockType = Literal[
    "Heading", "Text", "Callout", "Code", "BigNumber", "Formula", "Timeline", "Terminal"
]
ResourceAgentId = Literal["content", "mindmap", "quiz", "code", "reading"]
SlideRole = Literal[
    "cover", "agenda", "concept", "mechanism", "example", "comparison",
    "workflow", "pitfall", "code_demo", "practice", "summary",
]


# ── 前端最终载荷模型 ────────────────────────────────────────────────────────

class BaseBlock(BaseModel):
    id: str
    type: str


class BlockHeading(BaseBlock):
    type: Literal["Heading"]
    level: int
    content: str


class BlockText(BaseBlock):
    type: Literal["Text"]
    content: str
    format: str | None = None


class BlockCallout(BaseBlock):
    type: Literal["Callout"]
    intent: str
    icon: str
    content: str


class BlockCode(BaseBlock):
    type: Literal["Code"]
    language: str
    code: str
    highlightLines: list[int] | None = None


class BlockBigNumber(BaseBlock):
    type: Literal["BigNumber"]
    number: str
    unit: str | None = None
    label: str


class BlockFormula(BaseBlock):
    type: Literal["Formula"]
    formula: str


class TimelineStep(BaseModel):
    time: str
    title: str
    description: str | None = None


class BlockTimeline(BaseBlock):
    type: Literal["Timeline"]
    steps: list[TimelineStep]


class BlockTerminal(BaseBlock):
    type: Literal["Terminal"]
    command: str | None = None
    output: str


SlideBlock = Annotated[
    Union[
        BlockHeading, BlockText, BlockCallout, BlockCode,
        BlockBigNumber, BlockFormula, BlockTimeline, BlockTerminal,
    ],
    Field(discriminator="type"),
]


class PptSlide(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    layout: LayoutType
    layoutConfig: dict[str, Any] | None = Field(default=None)
    slots: dict[str, list[SlideBlock]]
    metadata: dict[str, Any] = Field(default_factory=dict)


class PptPayload(BaseModel):
    """PPT 结构化输出，新协议要求使用扁平根对象。"""

    model_config = ConfigDict(extra="forbid")

    template_id: ThemeType = Field(description="PPT主题风格，必须根据内容风格选择")
    topic: str = Field(description="PPT主题/标题")
    author: str | None = Field(default=None, description="作者")
    date: str | None = Field(default=None, description="日期")
    slides: list[PptSlide] = Field(min_length=3, description="PPT页面列表，至少3页(cover+agenda+正文)")

    @field_validator("slides")
    @classmethod
    def validate_slide_layout_order(cls, slides: list[PptSlide]) -> list[PptSlide]:
        if len(slides) < 3:
            raise ValueError("PPT 至少需要 3 页")
        return slides


# ── 内部流水线模型 ──────────────────────────────────────────────────────────

class MaterialArtifact(BaseModel):
    agent_id: ResourceAgentId
    title: str = ""
    summary: str = ""
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    success: bool = True


class NodeMaterialContext(BaseModel):
    """路径节点素材上下文 — 供 PPT 内部流水线调整大纲策略。"""
    path_title: str = ""
    path_goal: str = ""
    node_title: str = ""
    node_key: str = ""
    difficulty: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    generation_focus: list[str] = Field(default_factory=list)
    tutorial_title: str = ""
    tutorial_summary: str | None = None
    tutorial_markdown: str = ""


class MaterialBundle(BaseModel):
    learning_need: str
    learning_scenario: str = ""
    profile: dict[str, Any] = Field(default_factory=dict)
    blueprint: dict[str, Any] | None = None
    instruction: dict[str, Any] | None = None
    artifacts: dict[ResourceAgentId, MaterialArtifact] = Field(default_factory=dict)
    source_type: Literal["resource", "node"] = "resource"
    node_context: NodeMaterialContext | None = None


class MaterialDigest(BaseModel):
    topic: str
    audience: str
    learning_goal: str
    core_concepts: list[str] = Field(default_factory=list)
    structure_points: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    comparisons: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    practice_prompts: list[str] = Field(default_factory=list)
    code_cases: list[str] = Field(default_factory=list)
    source_map: dict[str, list[ResourceAgentId]] = Field(default_factory=dict)


class DeckConstraints(BaseModel):
    page_count: int = Field(ge=3, le=20)
    difficulty: Literal["easy", "normal", "hard"] = "normal"
    theme: ThemeType | None = None


class BlockContract(BaseModel):
    block_id: str
    slot: str
    type: BlockType
    required_fields: list[str]
    content_hint: str
    min_length: int = 0


class SlideContract(BaseModel):
    slide_id: str
    index: int = Field(ge=1)
    role: SlideRole
    title: str
    learning_objective: str
    source_agents: list[ResourceAgentId] = Field(default_factory=list)
    layout: LayoutType
    blocks: list[BlockContract]


class DeckOutline(BaseModel):
    topic: str
    title: str
    subtitle: str | None = None
    theme: ThemeType
    audience_level: Literal["beginner", "intermediate", "advanced"]
    narrative: str
    slides: list[SlideContract]

    @field_validator("slides")
    @classmethod
    def validate_slides(cls, slides: list[SlideContract]) -> list[SlideContract]:
        if not slides:
            raise ValueError("DeckOutline must have at least one slide")
        if slides[0].role != "cover":
            raise ValueError("First slide must have role 'cover'")
        if slides[0].layout != "FocusTitle":
            raise ValueError("First slide must use FocusTitle layout")
        indexes = [s.index for s in slides]
        expected = list(range(1, len(slides) + 1))
        if indexes != expected:
            raise ValueError(f"Slide indexes must be contiguous from 1, got {indexes}")
        for slide in slides:
            if not slide.blocks:
                raise ValueError(f"Slide {slide.slide_id} has no blocks")
        return slides


class RenderedBlock(BaseModel):
    block_id: str
    type: BlockType
    data: dict[str, Any]


class SlideDraft(BaseModel):
    slide_id: str
    index: int
    title: str
    blocks: list[RenderedBlock]
    speaker_notes: str
    source_refs: list[ResourceAgentId] = Field(default_factory=list)
