"""PPT 载荷构建器 — 从 DeckOutline + SlideDraft 构建最终 PptPayload。

纯确定性逻辑，不调用 LLM。校验 draft 严格匹配 contract，
然后转换为前端可渲染的 PptPayload。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.resource.agents.ppt_internal import _validate_draft_against_contract
from app.resource.agents.ppt_models import (
    BlockCallout,
    BlockBigNumber,
    BlockCode,
    BlockFormula,
    BlockHeading,
    BlockTerminal,
    BlockText,
    BlockTimeline,
    DeckOutline,
    PptPayload,
    PptSlide,
    RenderedBlock,
    SlideContract,
    SlideDraft,
    TimelineStep,
)


class PayloadBuilder:
    """确定性构建器：DeckOutline + list[SlideDraft] → PptPayload。"""

    def build(self, outline: DeckOutline, drafts: list[SlideDraft]) -> PptPayload:
        """构建最终 PptPayload，校验 draft 与 contract 严格匹配。"""
        # Build a lookup from slide_id to draft
        draft_by_id = {d.slide_id: d for d in drafts}

        # Verify every contract has a matching draft
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

        # Verify no slot is empty
        for slot_name, slot_blocks in slots.items():
            if not slot_blocks:
                raise ValueError(
                    f"Slot '{slot_name}' in slide {contract.slide_id} is empty"
                )

        # Build metadata with speaker_notes and source_refs
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
