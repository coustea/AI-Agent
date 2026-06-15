"""PPT 前端模板能力清单 — 后端只能输出此清单中声明的主题/布局/插槽/区块。

此清单是后端输出与前端渲染之间的契约，任何新增布局或区块必须先在此注册。
"""

from __future__ import annotations

from app.resource.agents.ppt_models import BlockType, LayoutType, SlideContract


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
        "Formula": ["latex", "description"],
        "Timeline": ["items"],
        "Terminal": ["commands"],
    },
}


def get_layout_slots(layout: LayoutType) -> dict[str, list[BlockType]]:
    """Return the slots dict for the given layout from the manifest.

    Raises:
        ValueError: If the layout is not in the manifest.
    """
    layouts = PPT_TEMPLATE_MANIFEST["layouts"]
    if layout not in layouts:
        raise ValueError(f"Layout '{layout}' is not in the manifest")
    return layouts[layout]["slots"]  # type: ignore[no-any-return]


def get_block_required_fields(block_type: BlockType) -> list[str]:
    """Return the required fields list for the given block type from the manifest.

    Raises:
        ValueError: If the block type is not in the manifest.
    """
    blocks = PPT_TEMPLATE_MANIFEST["blocks"]
    if block_type not in blocks:
        raise ValueError(f"Block type '{block_type}' is not in the manifest")
    return blocks[block_type]  # type: ignore[no-any-return]


def validate_contract_against_manifest(contract: SlideContract) -> None:
    """Validate that a SlideContract conforms to the manifest.

    Checks:
      - Layout exists in manifest
      - Every slot in the contract's blocks exists in the layout's slots
      - Every block type in the contract is allowed in its slot
      - Every BlockContract.required_fields matches the manifest's required
        fields for that block type

    Raises:
        ValueError: With a descriptive message on any violation.
    """
    layouts = PPT_TEMPLATE_MANIFEST["layouts"]

    # 1. Layout must exist
    if contract.layout not in layouts:
        raise ValueError(
            f"Layout '{contract.layout}' is not in the manifest"
        )

    layout_slots = layouts[contract.layout]["slots"]

    for block in contract.blocks:
        # 2. Slot must exist in layout
        if block.slot not in layout_slots:
            raise ValueError(
                f"Slot '{block.slot}' is not defined in layout "
                f"'{contract.layout}' (slide '{contract.slide_id}', "
                f"block '{block.block_id}')"
            )

        # 3. Block type must be allowed in that slot
        allowed_types = layout_slots[block.slot]
        if block.type not in allowed_types:
            raise ValueError(
                f"Block type '{block.type}' is not allowed in slot "
                f"'{block.slot}' of layout '{contract.layout}' "
                f"(slide '{contract.slide_id}', block '{block.block_id}')"
            )

        # 4. required_fields must match manifest
        manifest_fields = get_block_required_fields(block.type)
        if block.required_fields != manifest_fields:
            raise ValueError(
                f"Block '{block.block_id}' (type '{block.type}') has "
                f"required_fields {block.required_fields}, but manifest "
                f"requires {manifest_fields}"
            )
