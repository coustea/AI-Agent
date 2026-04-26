"""Single-template catalog for PPT generation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_TEMPLATE_ID = "python_ppt_template"

_DEFAULT_SLIDE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "page_role": "cover",
        "slide_number": 1,
        "summary": "Cover page",
        "reusable": False,
        "slots": [{"name": "title"}, {"name": "subtitle"}, {"name": "presenter"}],
    },
    {
        "page_role": "table_of_contents",
        "slide_number": 2,
        "summary": "Table of contents",
        "reusable": False,
        "slots": [
            {"name": "title"},
            {"name": "item1_title"},
            {"name": "item1_desc"},
            {"name": "item2_title"},
            {"name": "item2_desc"},
            {"name": "item3_title"},
            {"name": "item3_desc"},
            {"name": "item4_title"},
            {"name": "item4_desc"},
        ],
    },
    {
        "page_role": "slide_03",
        "slide_number": 3,
        "summary": "Content page 03",
        "reusable": True,
        "slots": [{"name": "title"}, {"name": "slot_1"}, {"name": "slot_2"}, {"name": "slot_3"}],
    },
    {
        "page_role": "slide_04",
        "slide_number": 4,
        "summary": "Content page 04",
        "reusable": True,
        "slots": [
            {"name": "title"},
            {"name": "slot_1"},
            {"name": "slot_2"},
            {"name": "slot_3"},
            {"name": "slot_4"},
            {"name": "slot_5"},
            {"name": "slot_6"},
            {"name": "slot_7"},
            {"name": "slot_8"},
        ],
    },
    {
        "page_role": "slide_05",
        "slide_number": 5,
        "summary": "Content page 05",
        "reusable": True,
        "slots": [
            {"name": "title"},
            {"name": "slot_1"},
            {"name": "slot_2"},
            {"name": "slot_3"},
            {"name": "slot_4"},
            {"name": "slot_5"},
        ],
    },
    {
        "page_role": "slide_06",
        "slide_number": 6,
        "summary": "Content page 06",
        "reusable": True,
        "slots": [
            {"name": "title"},
            {"name": "slot_1"},
            {"name": "slot_2"},
            {"name": "slot_3"},
            {"name": "slot_4"},
            {"name": "slot_5"},
            {"name": "slot_6"},
            {"name": "slot_7"},
            {"name": "slot_8"},
        ],
    },
]


def _build_config(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "render_options": {
            "preserve_template_shapes": True,
            "enable_icons": False,
            "enable_image_placeholders": False,
            "enable_dynamic_gradient": False,
            "replace_template_text_frames": True,
        },
        "slide_definitions": deepcopy(_DEFAULT_SLIDE_DEFINITIONS),
    }


BUILTIN_TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    "python_ppt_template": {
        "id": "python_ppt_template",
        "name": "Python PPT Template",
        "description": "Use only the user-provided Python.pptx template.",
        "style": "python_ppt_template",
        "tags": ["python", "fixed-template"],
        "config": _build_config("Python PPT Template", "Single fixed template."),
    }
}


def list_builtin_templates() -> list[dict[str, Any]]:
    return [dict(item) for item in BUILTIN_TEMPLATE_CATALOG.values()]


def get_builtin_template_spec(template_id: str) -> dict[str, Any] | None:
    _ = template_id
    return BUILTIN_TEMPLATE_CATALOG.get(DEFAULT_TEMPLATE_ID)


def _normalize_slide_defs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            role = str(item.get("page_role", "")).strip()
            if role:
                result.append(dict(item))
    return result


def _merge_slot_defs(preferred: Any, existing: Any) -> list[dict[str, Any]]:
    preferred_list = preferred if isinstance(preferred, list) else []
    existing_list = existing if isinstance(existing, list) else []
    names: set[str] = set()
    merged: list[dict[str, Any]] = []
    for entry in preferred_list + existing_list:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name or name in names:
            continue
        names.add(name)
        merged.append({"name": name})
    return merged


def merge_template_config(template_id: str, config: dict[str, Any] | None) -> dict[str, Any]:
    _ = template_id
    spec = BUILTIN_TEMPLATE_CATALOG[DEFAULT_TEMPLATE_ID]
    base_config = spec.get("config")
    if not isinstance(base_config, dict):
        base_config = _build_config(DEFAULT_TEMPLATE_ID, "Single fixed template.")
    existing = dict(config) if isinstance(config, dict) else {}

    merged = dict(base_config)
    merged.update(existing)

    base_render_options = dict(base_config.get("render_options", {}))
    current_render_options = existing.get("render_options", {})
    if not isinstance(current_render_options, dict):
        current_render_options = {}
    merged["render_options"] = {**base_render_options, **current_render_options}

    base_defs = _normalize_slide_defs(base_config.get("slide_definitions", []))
    existing_defs = _normalize_slide_defs(existing.get("slide_definitions", []))
    existing_map = {item.get("page_role"): item for item in existing_defs}

    merged_defs: list[dict[str, Any]] = []
    for base_def in base_defs:
        role = str(base_def.get("page_role", "")).strip()
        chosen = dict(base_def)
        if role in existing_map:
            current = existing_map[role]
            chosen.update(current)
            chosen["slots"] = _merge_slot_defs(base_def.get("slots", []), current.get("slots", []))
        else:
            chosen["slots"] = _merge_slot_defs(base_def.get("slots", []), [])
        merged_defs.append(chosen)

    known_roles = {str(item.get("page_role", "")).strip() for item in merged_defs}
    for current in existing_defs:
        role = str(current.get("page_role", "")).strip()
        if role and role not in known_roles:
            extra = dict(current)
            extra["slots"] = _merge_slot_defs(current.get("slots", []), [])
            merged_defs.append(extra)

    merged["slide_definitions"] = merged_defs
    return merged


def recommend_template_id(user_profile: dict[str, Any] | None, style: str) -> str:
    _ = (user_profile, style)
    return DEFAULT_TEMPLATE_ID

