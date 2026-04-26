"""内置在线 PPT 模板目录与推荐逻辑。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_TEMPLATE_ID = "bluegreen_3d_internet"

_DEFAULT_SLIDE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "page_role": "cover",
        "slide_number": 1,
        "summary": "封面页",
        "reusable": False,
        "slots": [{"name": "title"}, {"name": "subtitle"}, {"name": "presenter"}],
    },
    {
        "page_role": "table_of_contents",
        "slide_number": 2,
        "summary": "目录页",
        "reusable": False,
        "slots": [
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
        "page_role": "hero_image_split",
        "slide_number": 3,
        "summary": "图文分屏页（左图右文）",
        "reusable": True,
        "slots": [
            {"name": "subtitle"},
            {"name": "point1"},
            {"name": "point2"},
            {"name": "point3"},
            {"name": "point4"},
            {"name": "image_url"},
            {"name": "image_hint"},
        ],
    },
    {
        "page_role": "icon_process_row",
        "slide_number": 4,
        "summary": "图标流程横排页",
        "reusable": True,
        "slots": [
            {"name": "item1_title"},
            {"name": "item1_body"},
            {"name": "item2_title"},
            {"name": "item2_body"},
            {"name": "item3_title"},
            {"name": "item3_body"},
            {"name": "item4_title"},
            {"name": "item4_body"},
            {"name": "result_title"},
            {"name": "result_body"},
        ],
    },
    {
        "page_role": "hex_cycle",
        "slide_number": 5,
        "summary": "六边环形关系页",
        "reusable": True,
        "slots": [
            {"name": "center_title"},
            {"name": "center_body"},
            {"name": "left_top"},
            {"name": "left_middle"},
            {"name": "left_bottom"},
            {"name": "right_top"},
            {"name": "right_middle"},
            {"name": "right_bottom"},
        ],
    },
    {
        "page_role": "target_illustration",
        "slide_number": 6,
        "summary": "目标/KPI 插画页",
        "reusable": True,
        "slots": [
            {"name": "kpi_title"},
            {"name": "kpi_value"},
            {"name": "kpi_desc"},
            {"name": "point1"},
            {"name": "point2"},
            {"name": "point3"},
            {"name": "image_url"},
            {"name": "image_hint"},
        ],
    },
    {
        "page_role": "road_timeline",
        "slide_number": 7,
        "summary": "路线图时间轴页",
        "reusable": True,
        "slots": [
            {"name": "milestone1_title"},
            {"name": "milestone1_body"},
            {"name": "milestone2_title"},
            {"name": "milestone2_body"},
            {"name": "milestone3_title"},
            {"name": "milestone3_body"},
            {"name": "milestone4_title"},
            {"name": "milestone4_body"},
            {"name": "milestone5_title"},
            {"name": "milestone5_body"},
        ],
    },
    {
        "page_role": "concentric_focus",
        "slide_number": 8,
        "summary": "同心圆聚焦页",
        "reusable": True,
        "slots": [
            {"name": "core_title"},
            {"name": "core_body"},
            {"name": "ring1_title"},
            {"name": "ring2_title"},
            {"name": "ring3_title"},
            {"name": "ring4_title"},
            {"name": "note"},
        ],
    },
    {
        "page_role": "three_columns",
        "slide_number": 9,
        "summary": "三列信息页",
        "reusable": True,
        "slots": [
            {"name": "item1_title"},
            {"name": "item1_body"},
            {"name": "item2_title"},
            {"name": "item2_body"},
            {"name": "item3_title"},
            {"name": "item3_body"},
        ],
    },
    {
        "page_role": "four_cards",
        "slide_number": 10,
        "summary": "四卡片页",
        "reusable": True,
        "slots": [
            {"name": "item1_title"},
            {"name": "item1_body"},
            {"name": "item2_title"},
            {"name": "item2_body"},
            {"name": "item3_title"},
            {"name": "item3_body"},
            {"name": "item4_title"},
            {"name": "item4_body"},
        ],
    },
    {
        "page_role": "three_steps",
        "slide_number": 11,
        "summary": "三步骤页",
        "reusable": True,
        "slots": [
            {"name": "step1_title"},
            {"name": "step1_body"},
            {"name": "step2_title"},
            {"name": "step2_body"},
            {"name": "step3_title"},
            {"name": "step3_body"},
        ],
    },
    {
        "page_role": "three_bullets",
        "slide_number": 12,
        "summary": "三要点页",
        "reusable": True,
        "slots": [{"name": "item1_body"}, {"name": "item2_body"}, {"name": "item3_body"}],
    },
    {
        "page_role": "two_cards",
        "slide_number": 13,
        "summary": "双栏对比页",
        "reusable": True,
        "slots": [
            {"name": "item1_title"},
            {"name": "item1_body"},
            {"name": "item2_title"},
            {"name": "item2_body"},
        ],
    },
    {
        "page_role": "single_text",
        "slide_number": 14,
        "summary": "单栏正文页",
        "reusable": True,
        "slots": [{"name": "title"}, {"name": "body"}],
    },
]


def _build_config(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "render_options": {
            "preserve_template_shapes": True,
            "enable_icons": True,
            "enable_image_placeholders": True,
            "enable_dynamic_gradient": True,
        },
        "slide_definitions": deepcopy(_DEFAULT_SLIDE_DEFINITIONS),
    }


BUILTIN_TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    "bluegreen_3d_internet": {
        "id": "bluegreen_3d_internet",
        "name": "蓝绿色3D宣传科技互联网演示文稿（本地）",
        "description": "由用户提供的PPTX解析为JSON模板并直接复用版式。",
        "style": "modern_minimal",
        "tags": ["蓝绿色", "3D", "科技", "互联网", "本地模板"],
        "config": _build_config("蓝绿色3D宣传科技互联网演示文稿（本地）", "使用本地解析模板，优先保留原始版式。"),
    },
    "wps_business_blue": {
        "id": "wps_business_blue",
        "name": "WPS 商务蓝（类）",
        "description": "类 WPS 商务汇报风格，适合教学讲解与信息图展示。",
        "style": "wps_business_blue",
        "tags": ["商务", "汇报", "理工", "信息图"],
        "source_page": "https://github.com/singerla/pptx-automizer",
        "source_url": "https://raw.githubusercontent.com/singerla/pptx-automizer/main/__tests__/pptx-templates/RootTemplate.pptx",
        "config": _build_config("WPS 商务蓝（类）", "类 WPS 商务汇报风格，适合教学讲解与信息图展示。"),
    },
    "wps_minimal_gray": {
        "id": "wps_minimal_gray",
        "name": "WPS 简约灰（类）",
        "description": "类 WPS 留白简约风格，适合知识结构化整理。",
        "style": "wps_minimal_gray",
        "tags": ["简约", "留白", "课堂", "结构化"],
        "source_page": "https://github.com/singerla/pptx-automizer",
        "source_url": "https://raw.githubusercontent.com/singerla/pptx-automizer/main/__tests__/pptx-templates/RootTemplate.pptx",
        "config": _build_config("WPS 简约灰（类）", "类 WPS 留白简约风格，适合知识结构化整理。"),
    },
    "wps_fresh_green": {
        "id": "wps_fresh_green",
        "name": "WPS 清新绿（类）",
        "description": "类 WPS 清新教学风格，适合案例与图解内容。",
        "style": "wps_fresh_green",
        "tags": ["清新", "图解", "案例", "教学"],
        "source_page": "https://github.com/singerla/pptx-automizer",
        "source_url": "https://raw.githubusercontent.com/singerla/pptx-automizer/main/__tests__/pptx-templates/SlideWithShapes.pptx",
        "config": _build_config("WPS 清新绿（类）", "类 WPS 清新教学风格，适合案例与图解内容。"),
    },
    "edu_modern_blue": {
        "id": "edu_modern_blue",
        "name": "现代教学蓝",
        "description": "信息密度高，适合知识讲解与考试复盘。",
        "style": "corporate_blue",
        "tags": ["逻辑", "考试", "理工", "结构化"],
        "source_page": "https://github.com/bowenliang123/markdown-exporter",
        "source_url": "https://raw.githubusercontent.com/bowenliang123/markdown-exporter/main/md_exporter/assets/template/pptx_template.pptx",
        "config": _build_config("现代教学蓝", "信息密度高，适合知识讲解与考试复盘。"),
    },
    "edu_creative_shapes": {
        "id": "edu_creative_shapes",
        "name": "创意图形风",
        "description": "图形装饰更强，适合视觉化讲解与案例展示。",
        "style": "creative_bold",
        "tags": ["视觉", "案例", "创意", "展示"],
        "source_page": "https://github.com/singerla/pptx-automizer",
        "source_url": "https://raw.githubusercontent.com/singerla/pptx-automizer/main/__tests__/pptx-templates/SlideWithShapes.pptx",
        "config": _build_config("创意图形风", "图形装饰更强，适合视觉化讲解与案例展示。"),
    },
    "edu_clean_light": {
        "id": "edu_clean_light",
        "name": "简洁留白",
        "description": "留白充足，适合概念导入与基础讲解。",
        "style": "modern_minimal",
        "tags": ["入门", "轻量", "通用", "留白"],
        "source_page": "https://github.com/scanny/python-pptx",
        "source_url": "https://raw.githubusercontent.com/scanny/python-pptx/master/src/pptx/templates/default.pptx",
        "config": _build_config("简洁留白", "留白充足，适合概念导入与基础讲解。"),
    },
    "edu_nature_green": {
        "id": "edu_nature_green",
        "name": "自然绿色",
        "description": "舒缓配色，适合生物、环境、健康类主题。",
        "style": "nature_green",
        "tags": ["自然", "生物", "医学", "人文"],
        "source_page": "https://github.com/singerla/pptx-automizer",
        "source_url": "https://raw.githubusercontent.com/singerla/pptx-automizer/main/__tests__/pptx-templates/RootTemplate.pptx",
        "config": _build_config("自然绿色", "舒缓配色，适合生物、环境、健康类主题。"),
    },
}


def list_builtin_templates() -> list[dict[str, Any]]:
    return [dict(item) for item in BUILTIN_TEMPLATE_CATALOG.values()]


def get_builtin_template_spec(template_id: str) -> dict[str, Any] | None:
    return BUILTIN_TEMPLATE_CATALOG.get(str(template_id or "").strip())


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
    """
    合并模板配置，确保：
    1) 新增页面角色可用；
    2) render_options 有默认值；
    3) 保留已有模板配置的个性化字段。
    """
    template_key = str(template_id or "").strip()
    spec = get_builtin_template_spec(template_key) or {}
    base_config = spec.get("config")
    if not isinstance(base_config, dict):
        base_config = _build_config(template_key or DEFAULT_TEMPLATE_ID, "通用教育模板")
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
    profile = user_profile or {}
    interest = str(profile.get("interest_preference", "")).lower()
    cognitive = str(profile.get("cognitive_style", "")).lower()
    major = str(profile.get("major", "")).lower()
    merged = " ".join([interest, cognitive, major])

    if any(k in merged for k in ("图", "视觉", "创意", "设计", "艺术", "案例")):
        return "wps_fresh_green"
    if any(k in merged for k in ("生物", "环境", "医学", "健康", "自然")):
        return "wps_fresh_green"
    if any(k in merged for k in ("编程", "算法", "工程", "数学", "逻辑", "考试", "理工")):
        return "wps_business_blue"

    if style in {"creative_bold", "wps_fresh_green", "nature_green"}:
        return "wps_fresh_green"
    if style in {"corporate_blue", "wps_business_blue"}:
        return "wps_business_blue"
    return "wps_minimal_gray"
