"""PPT 智能体 — 内部多智能体流水线输出结构化 JSON。

单文件实现，与 VideoAgent 结构对齐。内部流水线：
  1. MaterialAgent — 素材提取
  2. OutlineAgent — 大纲规划（含前端模板合约）
  3. SlideAgent — 并发写页
  4. PayloadBuilder — 确定性载荷构建
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any, Annotated, Literal, Union, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import assigned_outline_ids, outline_coverage_summary
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 类型字面量
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# 前端最终载荷模型
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# 内部流水线模型
# ═══════════════════════════════════════════════════════════════════════════════

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
    teaching_plan: dict[str, Any] | None = None
    upstream_handoffs: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[ResourceAgentId, MaterialArtifact] = Field(default_factory=dict)
    source_type: Literal["resource", "node"] = "resource"
    node_context: NodeMaterialContext | None = None
    assignment_instruction: str = ""


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


# ═══════════════════════════════════════════════════════════════════════════════
# 前端模板能力清单
# ═══════════════════════════════════════════════════════════════════════════════

PPT_TEMPLATE_MANIFEST = {
    "themes": {
        "theme-logic-blue": {
            "best_for": ["engineering", "workflow", "code", "system"],
        },
        "theme-mac-light": {
            "best_for": ["product", "tool", "case", "practice"],
        },
        "theme-notion-light": {
            "best_for": ["theory", "concept", "review", "formula"],
        },
    },
    "layouts": {
        "FocusTitle": {
            "slots": {
                "main": ["Heading", "Text", "Callout", "BigNumber"],
            },
            "best_for": ["cover", "summary"],
        },
        "SplitScreen": {
            "slots": {
                "left": ["Heading", "Text", "Callout", "Formula", "Code"],
                "right": ["Heading", "Text", "Callout", "Formula", "Code", "Terminal"],
            },
            "best_for": ["concept", "example", "comparison", "pitfall", "code_demo"],
        },
        "BentoGrid": {
            "slots": {
                "main": ["Heading", "Text", "Callout", "BigNumber"],
            },
            "best_for": ["agenda", "comparison", "practice", "summary"],
        },
        "LayerStack": {
            "slots": {
                "main": ["Heading", "Text", "Callout", "Timeline"],
            },
            "best_for": ["mechanism", "workflow", "process"],
        },
    },
    "blocks": {
        "Heading": ["text"],
        "Text": ["text"],
        "Callout": ["text", "tone"],
        "Code": ["language", "code"],
        "BigNumber": ["value", "label"],
        "Formula": ["latex"],
        "Timeline": ["items"],
        "Terminal": ["command", "output"],
    },
}


def _get_layout_slots(layout: LayoutType) -> dict[str, list[BlockType]]:
    """Return the slots dict for the given layout from the manifest."""
    layouts = PPT_TEMPLATE_MANIFEST["layouts"]
    if layout not in layouts:
        raise ValueError(f"Layout '{layout}' is not in the manifest")
    return layouts[layout]["slots"]  # type: ignore[no-any-return]


def _get_block_required_fields(block_type: BlockType) -> list[str]:
    """Return the required fields list for the given block type from the manifest."""
    blocks = PPT_TEMPLATE_MANIFEST["blocks"]
    if block_type not in blocks:
        raise ValueError(f"Block type '{block_type}' is not in the manifest")
    return blocks[block_type]  # type: ignore[no-any-return]


def _validate_contract_against_manifest(contract: SlideContract) -> None:
    """Validate that a SlideContract conforms to the manifest."""
    layouts = PPT_TEMPLATE_MANIFEST["layouts"]

    if contract.layout not in layouts:
        raise ValueError(f"Layout '{contract.layout}' is not in the manifest")

    layout_slots = layouts[contract.layout]["slots"]

    for block in contract.blocks:
        if block.slot not in layout_slots:
            raise ValueError(
                f"Slot '{block.slot}' is not defined in layout "
                f"'{contract.layout}' (slide '{contract.slide_id}', "
                f"block '{block.block_id}')"
            )

        allowed_types = layout_slots[block.slot]
        if block.type not in allowed_types:
            raise ValueError(
                f"Block type '{block.type}' is not allowed in slot "
                f"'{block.slot}' of layout '{contract.layout}' "
                f"(slide '{contract.slide_id}', block '{block.block_id}')"
            )

        manifest_fields = _get_block_required_fields(block.type)
        if block.required_fields != manifest_fields:
            raise ValueError(
                f"Block '{block.block_id}' (type '{block.type}') has "
                f"required_fields {block.required_fields}, but manifest "
                f"requires {manifest_fields}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Draft 校验
# ═══════════════════════════════════════════════════════════════════════════════

def _is_empty_required_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def _validate_draft_against_contract(draft: SlideDraft, contract: SlideContract) -> None:
    """校验 SlideDraft 严格匹配 SlideContract：不缺块、不多块、不缺字段。"""
    if draft.slide_id != contract.slide_id:
        raise ValueError(
            f"SlideDraft slide_id mismatch: expected {contract.slide_id}, got {draft.slide_id}"
        )
    if draft.index != contract.index:
        raise ValueError(
            f"SlideDraft index mismatch for slide {contract.slide_id}: "
            f"expected {contract.index}, got {draft.index}"
        )

    contract_block_ids = {b.block_id for b in contract.blocks}
    draft_block_ids = {b.block_id for b in draft.blocks}

    missing = contract_block_ids - draft_block_ids
    if missing:
        raise ValueError(
            f"SlideDraft for slide {contract.slide_id} missing blocks: {missing}"
        )

    extra = draft_block_ids - contract_block_ids
    if extra:
        raise ValueError(
            f"SlideDraft for slide {contract.slide_id} has undeclared blocks: {extra}"
        )

    contracts_by_id = {b.block_id: b for b in contract.blocks}
    for block in draft.blocks:
        block_contract = contracts_by_id[block.block_id]
        if block.type != block_contract.type:
            raise ValueError(
                f"Block {block.block_id} has type {block.type}, expected {block_contract.type}"
            )
        for field_name in block_contract.required_fields:
            if field_name not in block.data:
                raise ValueError(
                    f"Block {block.block_id} missing required field '{field_name}'"
                )
            if _is_empty_required_value(block.data[field_name]):
                raise ValueError(
                    f"Block {block.block_id} has empty required field '{field_name}'"
                )
        if block.type == "Timeline":
            items = block.data.get("items", [])
            if not isinstance(items, list) or len(items) == 0:
                raise ValueError(
                    f"Block {block.block_id} Timeline.items must be a non-empty list"
                )
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"Block {block.block_id} Timeline.items[{i}] must be an object"
                    )
                if not item.get("title"):
                    raise ValueError(
                        f"Block {block.block_id} Timeline.items[{i}] missing 'title'"
                    )
        if block.type == "Terminal":
            if not block.data.get("output"):
                raise ValueError(
                    f"Block {block.block_id} Terminal must have non-empty 'output'"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 素材捆绑构建
# ═══════════════════════════════════════════════════════════════════════════════

_SOURCE_LIMITS: dict[ResourceAgentId, int] = {
    "content": 6000,
    "mindmap": 4000,
    "quiz": 3000,
    "code": 5000,
    "reading": 4000,
}


def _bounded_content(content: str, limit: int) -> str:
    """截断内容到指定字符数上限。"""
    if len(content) <= limit:
        return content
    return content[:limit]


def _extract_artifacts(results: dict[str, AgentResult]) -> dict[ResourceAgentId, MaterialArtifact]:
    """从 AgentResult 字典提取 MaterialArtifact。"""
    artifacts: dict[ResourceAgentId, MaterialArtifact] = {}

    for agent_id, limit in _SOURCE_LIMITS.items():
        result = results.get(agent_id)
        if result is None:
            continue
        if not result.success:
            artifacts[agent_id] = MaterialArtifact(
                agent_id=agent_id,
                title=result.title or "",
                summary=result.summary or "",
                content="",
                metadata={"error": result.error, **result.metadata},
                success=False,
            )
            continue
        content = result.content or ""
        artifacts[agent_id] = MaterialArtifact(
            agent_id=agent_id,
            title=result.title or "",
            summary=result.summary or "",
            content=_bounded_content(content, limit),
            metadata=result.metadata,
            success=True,
        )

    return artifacts


def _extract_artifacts_from_handoffs(handoffs: dict[str, Any]) -> dict[ResourceAgentId, MaterialArtifact]:
    """从 DownstreamContext 字典提取 MaterialArtifact。"""
    from app.resource.schemas import DownstreamContext

    artifacts: dict[ResourceAgentId, MaterialArtifact] = {}
    for agent_id in _SOURCE_LIMITS:
        handoff = handoffs.get(agent_id)
        if handoff is None:
            continue
        if isinstance(handoff, DownstreamContext):
            artifacts[agent_id] = MaterialArtifact(
                agent_id=agent_id,
                title=handoff.title or "",
                summary=handoff.one_sentence_summary or "",
                content=json.dumps(handoff.model_dump(mode="json"), ensure_ascii=False),
                metadata={"source": "handoff"},
                success=True,
            )
        elif isinstance(handoff, dict):
            artifacts[agent_id] = MaterialArtifact(
                agent_id=agent_id,
                title=handoff.get("title", ""),
                summary=handoff.get("one_sentence_summary", ""),
                content=json.dumps(handoff, ensure_ascii=False),
                metadata={"source": "handoff"},
                success=True,
            )
    return artifacts


def build_resource_material(input_data: ResourceInput) -> MaterialBundle:
    """从 ResourceInput 构建 MaterialBundle（多智能体场景）。"""
    artifacts = _extract_artifacts_from_handoffs(input_data.upstream_handoffs)

    # Build assignment instruction for PPT aggregation agent
    assignment_instruction = ""
    if input_data.teaching_plan and input_data.teaching_plan.agent_assignments:
        for a in input_data.teaching_plan.agent_assignments:
            if a.agent_id == "ppt":
                parts: list[str] = []
                if a.focus_instruction:
                    parts.append(f"聚焦指令：{a.focus_instruction}")
                if a.style_constraint:
                    parts.append(f"风格约束：{a.style_constraint}")
                if a.boundary_notes:
                    parts.append("边界提醒：" + "；".join(a.boundary_notes))
                if a.key_points_emphasis:
                    parts.append("重点强调：" + "；".join(a.key_points_emphasis))
                assignment_instruction = "\n".join(parts)
                break

    return MaterialBundle(
        learning_need=input_data.learning_need,
        learning_scenario=input_data.learning_scenario,
        profile=input_data.profile,
        teaching_plan=input_data.teaching_plan.model_dump(mode="json") if input_data.teaching_plan else None,
        upstream_handoffs={
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        },
        artifacts=artifacts,
        source_type="resource",
        node_context=None,
        assignment_instruction=assignment_instruction,
    )


def build_node_material(input_data: NodeInput) -> MaterialBundle:
    """从 NodeInput 构建 MaterialBundle（路径节点场景）。"""
    node_context = NodeMaterialContext(
        path_title=input_data.path_title,
        path_goal=input_data.path_goal,
        node_title=input_data.node_title,
        node_key=input_data.node_key,
        difficulty=input_data.difficulty,
        knowledge_points=input_data.knowledge_points,
        weak_knowledge_points=input_data.weak_knowledge_points,
        generation_focus=input_data.generation_focus,
        tutorial_title=input_data.tutorial_title,
        tutorial_summary=input_data.tutorial_summary,
        tutorial_markdown=input_data.tutorial_markdown,
    )

    return MaterialBundle(
        learning_need=input_data.node_title,
        learning_scenario="path_learning",
        profile=input_data.profile,
        teaching_plan=None,
        upstream_handoffs={},
        artifacts={},
        source_type="node",
        node_context=node_context,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 内部智能体
# ═══════════════════════════════════════════════════════════════════════════════

class MaterialAgent:
    """素材提取 Agent — 从 MaterialBundle 提取 PPT 可用的教学素材。"""

    async def run(self, bundle: MaterialBundle) -> MaterialDigest:
        """从资源系统结果提取 PPT 素材摘要。"""
        llm = get_llm()
        prompt_template = prompts.get("resource").get("ppt_material")

        bundle_json = bundle.model_dump_json(indent=2)
        full_input = f"{prompt_template}\n\n{bundle_json}" if prompt_template else bundle_json

        result = await llm.ainvoke_json(
            MaterialDigest,
            full_input,
            temperature=INFERENCE_TEMPERATURE,
            max_tokens=3500,
            function_name="ppt_material",
            function_description="Extract PPT-useful teaching material from resource system outputs",
        )

        if not isinstance(result, MaterialDigest):
            result = MaterialDigest.model_validate(result)

        logger.info(
            "MaterialAgent 完成: topic=%s core_concepts=%d examples=%d",
            result.topic, len(result.core_concepts), len(result.examples),
        )
        return result


class OutlineAgent:
    """大纲规划 Agent — 生成 PPT 页面结构及每页的前端模板合约。"""

    async def run(
        self,
        digest: MaterialDigest,
        constraints: DeckConstraints,
    ) -> DeckOutline:
        """生成 DeckOutline（含每页的 SlideContract）。"""
        llm = get_llm()
        prompt_template = prompts.get("resource").get("ppt_outline")

        input_data = {
            "material_digest": digest.model_dump(mode="json"),
            "deck_constraints": constraints.model_dump(mode="json"),
            "template_manifest": PPT_TEMPLATE_MANIFEST,
        }
        input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
        full_input = f"{prompt_template}\n\n{input_json}" if prompt_template else input_json

        result = await llm.ainvoke_json(
            DeckOutline,
            full_input,
            temperature=INFERENCE_TEMPERATURE,
            max_tokens=6000,
            function_name="ppt_outline",
            function_description="Generate PPT deck outline with exact frontend template contracts per slide",
        )

        if not isinstance(result, DeckOutline):
            result = DeckOutline.model_validate(result)

        if len(result.slides) != constraints.page_count:
            raise ValueError(
                f"DeckOutline page_count mismatch: expected {constraints.page_count}, "
                f"got {len(result.slides)}"
            )

        # Validate every slide contract against the frontend manifest
        for contract in result.slides:
            _validate_contract_against_manifest(contract)

        logger.info(
            "OutlineAgent 完成: topic=%s slides=%d theme=%s",
            result.topic, len(result.slides), result.theme,
        )
        return result


class SlideAgent:
    """单页生成 Agent — 根据一份 SlideContract 生成一页 PPT 内容。"""

    async def run(
        self,
        contract: SlideContract,
        digest: MaterialDigest,
        outline: DeckOutline,
    ) -> SlideDraft:
        """根据 SlideContract 填充一页幻灯片内容。"""
        llm = get_llm()
        prompt_template = prompts.get("resource").get("ppt_slide")

        input_data = {
            "slide_contract": contract.model_dump(mode="json"),
            "material_digest": digest.model_dump(mode="json"),
            "deck_outline": {
                "topic": outline.topic,
                "title": outline.title,
                "narrative": outline.narrative,
            },
        }
        input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
        full_input = f"{prompt_template}\n\n{input_json}" if prompt_template else input_json

        result = await llm.ainvoke_json(
            SlideDraft,
            full_input,
            temperature=INFERENCE_TEMPERATURE,
            max_tokens=2500,
            function_name="ppt_slide",
            function_description="Generate one slide's content matching its SlideContract",
        )

        if not isinstance(result, SlideDraft):
            result = SlideDraft.model_validate(result)

        # Validate draft against its contract
        _validate_draft_against_contract(result, contract)

        logger.info(
            "SlideAgent 完成: slide_id=%s role=%s blocks=%d",
            contract.slide_id, contract.role, len(result.blocks),
        )
        return result




# ═══════════════════════════════════════════════════════════════════════════════
# 载荷构建器
# ═══════════════════════════════════════════════════════════════════════════════

class PayloadBuilder:
    """确定性构建器 — 将 DeckOutline + list[SlideDraft] 转换为 PptPayload。"""

    def build(self, outline: DeckOutline, drafts: list[SlideDraft]) -> PptPayload:
        """构建最终 PptPayload，校验 draft 与 contract 严格匹配。"""
        draft_by_id = {d.slide_id: d for d in drafts}

        for contract in outline.slides:
            if contract.slide_id not in draft_by_id:
                raise ValueError(
                    f"Missing draft for slide {contract.slide_id} (index {contract.index})"
                )

        slides: list[PptSlide] = []
        for contract in outline.slides:
            draft = draft_by_id[contract.slide_id]
            ppt_slide = self._build_slide(contract, draft)
            slides.append(ppt_slide)

        return PptPayload(
            template_id=outline.theme,
            topic=outline.title,
            author="学枢智导 AI",
            date=str(date.today()),
            slides=slides,
        )

    def _build_slide(self, contract: SlideContract, draft: SlideDraft) -> PptSlide:
        """将一份 SlideContract + SlideDraft 转换为 PptSlide。"""
        _validate_draft_against_contract(draft, contract)
        slots: dict[str, list] = {}
        contract_block_slots = {b.block_id: b.slot for b in contract.blocks}

        for rendered in draft.blocks:
            slot = contract_block_slots.get(rendered.block_id)
            if slot is None:
                raise ValueError(
                    f"Block {rendered.block_id} in draft has no matching slot in contract"
                )
            if slot not in slots:
                slots[slot] = []
            block = self._rendered_to_block(rendered)
            slots[slot].append(block)

        for slot_name, slot_blocks in slots.items():
            if not slot_blocks:
                raise ValueError(
                    f"Slot '{slot_name}' in slide {contract.slide_id} is empty"
                )

        metadata: dict[str, Any] = {}
        if draft.speaker_notes:
            metadata["speaker_notes"] = draft.speaker_notes
        if draft.source_refs:
            metadata["source_refs"] = draft.source_refs

        return PptSlide(
            id=contract.slide_id,
            layout=contract.layout,
            slots=slots,
            metadata=metadata,
        )

    def _required(self, rendered: RenderedBlock, field_name: str) -> Any:
        value = rendered.data.get(field_name)
        if value is None:
            raise ValueError(
                f"Block {rendered.block_id} missing required field '{field_name}'"
            )
        if isinstance(value, str) and not value.strip():
            raise ValueError(
                f"Block {rendered.block_id} has empty required field '{field_name}'"
            )
        if isinstance(value, list) and not value:
            raise ValueError(
                f"Block {rendered.block_id} has empty required field '{field_name}'"
            )
        return value

    def _rendered_to_block(self, rendered: RenderedBlock) -> Any:
        """将 RenderedBlock 转换为具体的前端 Block 模型。"""
        data = rendered.data
        block_id = rendered.block_id

        match rendered.type:
            case "Heading":
                return BlockHeading(
                    id=block_id,
                    type="Heading",
                    level=int(data.get("level", 1)),
                    content=str(self._required(rendered, "text")),
                )
            case "Text":
                return BlockText(
                    id=block_id,
                    type="Text",
                    content=str(self._required(rendered, "text")),
                    format=data.get("format"),
                )
            case "Callout":
                return BlockCallout(
                    id=block_id,
                    type="Callout",
                    intent=str(self._required(rendered, "tone")),
                    icon=data.get("icon", "\U0001f4a1"),
                    content=str(self._required(rendered, "text")),
                )
            case "Code":
                return BlockCode(
                    id=block_id,
                    type="Code",
                    language=str(self._required(rendered, "language")),
                    code=str(self._required(rendered, "code")),
                )
            case "BigNumber":
                return BlockBigNumber(
                    id=block_id,
                    type="BigNumber",
                    number=str(self._required(rendered, "value")),
                    unit=data.get("unit"),
                    label=str(self._required(rendered, "label")),
                )
            case "Formula":
                return BlockFormula(
                    id=block_id,
                    type="Formula",
                    formula=str(self._required(rendered, "latex")),
                )
            case "Timeline":
                steps = []
                for item in data.get("items", []):
                    steps.append(TimelineStep(
                        time=item.get("time", ""),
                        title=item.get("title", ""),
                        description=item.get("description"),
                    ))
                return BlockTimeline(
                    id=block_id,
                    type="Timeline",
                    steps=steps,
                )
            case "Terminal":
                return BlockTerminal(
                    id=block_id,
                    type="Terminal",
                    command=str(data.get("command", "")),
                    output=str(self._required(rendered, "output")),
                )
            case _:
                raise ValueError(f"Unsupported block type: {rendered.type}")


class SlideWriteState(TypedDict):
    contract: SlideContract
    digest: MaterialDigest
    outline: DeckOutline


def _add_drafts(left: list[SlideDraft] | None, right: list[SlideDraft] | None) -> list[SlideDraft]:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right


class PptGraphState(TypedDict, total=False):
    # Inputs
    bundle: MaterialBundle
    constraints: DeckConstraints
    title_prefix: str

    # Intermediate artifacts
    digest: MaterialDigest
    outline: DeckOutline
    drafts: Annotated[list[SlideDraft], _add_drafts]

    # Final outputs
    payload: PptPayload
    error: str


# ═══════════════════════════════════════════════════════════════════════════════
# PptAgent — 注册到 AGENT_REGISTRY 的入口
# ═══════════════════════════════════════════════════════════════════════════════

@register_agent
class PptAgent(BaseResourceAgent):
    """PPT 生成 Agent — 内部多智能体流水线输出结构化 JSON。"""

    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self._slide_semaphore = asyncio.Semaphore(4)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：从 ResourceInput 构建素材 → 内部流水线。"""
        config = input_data.agent_config or {}
        material_bundle_data = config.get("material_bundle")
        if material_bundle_data and isinstance(material_bundle_data, dict):
            bundle = MaterialBundle.model_validate(material_bundle_data)
        else:
            bundle = build_resource_material(input_data)

        result = await self._run_pipeline(
            bundle=bundle,
            config=config,
            title_prefix=input_data.learning_need[:32],
        )
        if result.success:
            coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
            result.metadata["teaching_plan_outline_ids"] = coverage["teaching_plan_outline_ids"]
            result.metadata["covered_source_outline_ids"] = coverage["covered_source_outline_ids"]
            result.metadata["missing_source_outline_ids"] = coverage["missing_source_outline_ids"]
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点场景：从 NodeInput 构建素材 → 内部流水线。"""
        bundle = build_node_material(input_data)
        config = input_data.agent_config or {}
        # 路径节点场景用 node_title 作为标题前缀
        result = await self._run_pipeline(
            bundle=bundle,
            config=config,
            title_prefix=input_data.node_title,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    def _build_graph(self) -> Any:
        if not hasattr(self, "_cached_graph"):
            workflow = StateGraph(PptGraphState)

            workflow.add_node("extract_material", self._material_node)
            workflow.add_node("plan_outline", self._outline_node)
            workflow.add_node("write_slide", self._write_slide_node)
            workflow.add_node("build_payload", self._payload_node)

            workflow.add_edge(START, "extract_material")
            workflow.add_edge("extract_material", "plan_outline")
            workflow.add_conditional_edges("plan_outline", self._route_slides, ["write_slide"])
            workflow.add_edge("write_slide", "build_payload")
            workflow.add_edge("build_payload", END)

            self._cached_graph = workflow.compile()
        return self._cached_graph

    async def _material_node(self, state: PptGraphState) -> dict[str, Any]:
        await self.emit_start("正在提取教学素材", progress=20)
        material_agent = MaterialAgent()
        digest = await material_agent.run(state["bundle"])
        return {"digest": digest}

    async def _outline_node(self, state: PptGraphState) -> dict[str, Any]:
        await self.emit_start("正在规划 PPT 结构", progress=35)
        outline_agent = OutlineAgent()
        outline = await outline_agent.run(state["digest"], state["constraints"])
        return {"outline": outline}

    def _route_slides(self, state: PptGraphState) -> list[Send]:
        outline: DeckOutline = state["outline"]
        digest: MaterialDigest = state["digest"]
        return [
            Send("write_slide", {
                "contract": slide,
                "digest": digest,
                "outline": outline,
            })
            for slide in outline.slides
        ]

    async def _write_slide_node(self, state: SlideWriteState) -> dict[str, Any]:
        async with self._slide_semaphore:
            slide_agent = SlideAgent()
            draft = await slide_agent.run(state["contract"], state["digest"], state["outline"])
            return {"drafts": [draft]}

    async def _payload_node(self, state: PptGraphState) -> dict[str, Any]:
        await self.emit_start("正在构建最终载荷", progress=85)
        payload_builder = PayloadBuilder()
        sorted_drafts = sorted(state.get("drafts") or [], key=lambda d: d.index)
        payload = payload_builder.build(state["outline"], sorted_drafts)
        return {"payload": payload}

    async def _run_pipeline(
        self,
        *,
        bundle: MaterialBundle,
        config: dict,
        title_prefix: str,
    ) -> AgentResult:
        """内部多智能体流水线：素材提取 → 大纲规划 → 并发写页 → 载荷构建。"""
        page_count = int(config.get("page_count") or config.get("slide_count") or 6)
        difficulty = config.get("difficulty") or "intermediate"

        # Map difficulty to DeckConstraints difficulty
        constraint_difficulty = difficulty
        if constraint_difficulty == "intermediate":
            constraint_difficulty = "normal"
        elif constraint_difficulty == "beginner":
            constraint_difficulty = "easy"
        elif constraint_difficulty == "advanced":
            constraint_difficulty = "hard"

        constraints = DeckConstraints(
            page_count=page_count,
            difficulty=constraint_difficulty,
        )

        logger.info(
            "PptAgent 启动内部流水线: page_count=%d difficulty=%s bundle_artifacts=%d source_type=%s",
            page_count, difficulty, len(bundle.artifacts), bundle.source_type,
        )

        try:
            graph = self._build_graph()
            initial_state = PptGraphState(
                bundle=bundle,
                constraints=constraints,
                title_prefix=title_prefix,
                drafts=[],
            )
            final_state = await graph.ainvoke(initial_state)
            payload = final_state.get("payload")
            if not payload:
                raise ValueError("PPT generation graph failed to build final payload")

        except Exception as exc:
            logger.error("PptAgent 生成异常: %s", exc, exc_info=True)
            return AgentResult(
                success=False,
                error=str(exc),
                title=f"{title_prefix} - PPT",
                summary=f"PPT 生成异常: {exc}",
                metadata={
                    "engine": "ppt_json",
                    "agent_id": "ppt",
                    "delivery_mode": "preview",
                    "schema_version": "ppt/v2",
                    "difficulty": difficulty,
                    "internal_pipeline": "material/outline/slides/payload",
                },
            )

        # Page count validation
        actual_count = len(payload.slides)
        logger.info(
            "PptAgent 流水线完成: template_id=%s slides=%d layouts=%s",
            payload.template_id, actual_count,
            [s.layout for s in payload.slides[:3]],
        )

        if actual_count != page_count:
            error = f"PPT 页数与预期不符：期望 {page_count} 页，实际 {actual_count} 页"
            logger.warning(error)
            return AgentResult(
                success=False,
                error=error,
                title=f"{title_prefix} - PPT",
                summary=error,
                metrics={"page_count": actual_count, "expected_page_count": page_count},
                metadata={
                    "engine": "ppt_json",
                    "agent_id": "ppt",
                    "delivery_mode": "preview",
                    "schema_version": "ppt/v2",
                    "template_id": payload.template_id,
                    "page_count": actual_count,
                    "expected_page_count": page_count,
                    "difficulty": difficulty,
                    "internal_pipeline": "material/outline/slides/payload",
                },
            )

        content = payload.model_dump_json(indent=2)
        source_handoff_agent_ids = sorted(bundle.upstream_handoffs.keys()) if bundle.upstream_handoffs else []
        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - PPT",
            summary=f"生成 {actual_count} 页在线预览 PPT",
            metrics={"page_count": actual_count},
            metadata={
                "engine": "ppt_json",
                "agent_id": "ppt",
                "delivery_mode": "preview",
                "schema_version": "ppt/v2",
                "template_id": payload.template_id,
                "page_count": actual_count,
                "difficulty": difficulty,
                "source_handoff_agent_ids": source_handoff_agent_ids,
                "internal_pipeline": "material/outline/slides/payload",
            },
        )
