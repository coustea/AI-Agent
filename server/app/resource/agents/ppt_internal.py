"""PPT 内部智能体 — MaterialAgent / OutlineAgent / SlideAgent。

仅供 PptAgent 内部使用，不注册到 AGENT_REGISTRY。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.ppt_manifest import (
    PPT_TEMPLATE_MANIFEST,
    validate_contract_against_manifest,
)
from app.resource.agents.ppt_models import (
    DeckConstraints,
    DeckOutline,
    MaterialBundle,
    MaterialDigest,
    SlideContract,
    SlideDraft,
)

logger = get_logger(__name__)


class MaterialAgent:
    """素材提取 — 从 MaterialBundle 提取 PPT 可用的教学素材。"""

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
    """大纲规划 — 生成 PPT 页面结构及每页的前端模板合约。"""

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
            validate_contract_against_manifest(contract)

        logger.info(
            "OutlineAgent 完成: topic=%s slides=%d theme=%s",
            result.topic, len(result.slides), result.theme,
        )
        return result


class SlideAgent:
    """单页生成 — 根据一份 SlideContract 生成一页 PPT 内容。"""

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


async def write_slides_concurrently(
    slide_agent: SlideAgent,
    outline: DeckOutline,
    digest: MaterialDigest,
    concurrency: int = 4,
) -> list[SlideDraft]:
    """并发生成所有幻灯片内容，保持顺序。"""
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_with_semaphore(contract: SlideContract) -> SlideDraft:
        async with semaphore:
            return await slide_agent.run(contract, digest, outline)

    tasks = [_run_with_semaphore(contract) for contract in outline.slides]
    drafts = await asyncio.gather(*tasks)

    # Sort by index to preserve order
    return sorted(drafts, key=lambda d: d.index)
