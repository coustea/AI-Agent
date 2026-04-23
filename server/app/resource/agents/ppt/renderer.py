"""
PPT 模板渲染器。

基于 .pptx 模板文件生成演示文稿，复制模板幻灯片并填充内容。
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from io import BytesIO
from urllib.parse import unquote, urlparse
from pathlib import Path
from typing import Any

import httpx
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from app.infra.logging import get_logger
from app.resource.agents.ppt.template_catalog import DEFAULT_TEMPLATE_ID, get_builtin_template_spec, merge_template_config
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

PPT_OUTPUT_DIR = WORKPLACE_DIR / "ppt"
PPT_TEMPLATE_DIR = WORKPLACE_DIR / "templates"
TEMPLATE_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "template"
STYLE_PALETTES: dict[str, dict[str, str]] = {
    "modern_minimal": {
        "title": "1E293B",
        "body": "334155",
        "accent": "3B82F6",
        "accent_alt": "2563EB",
        "soft": "DBEAFE",
        "card": "F8FAFC",
        "gradient_from": "EFF6FF",
        "gradient_to": "DBEAFE",
    },
    "creative_bold": {
        "title": "5B21B6",
        "body": "3F3F46",
        "accent": "EC4899",
        "accent_alt": "A855F7",
        "soft": "FCE7F3",
        "card": "FDF2F8",
        "gradient_from": "FDF4FF",
        "gradient_to": "FCE7F3",
    },
    "corporate_blue": {
        "title": "1E40AF",
        "body": "1F2937",
        "accent": "0EA5E9",
        "accent_alt": "1D4ED8",
        "soft": "E0F2FE",
        "card": "F0F9FF",
        "gradient_from": "EEF2FF",
        "gradient_to": "E0F2FE",
    },
    "nature_green": {
        "title": "166534",
        "body": "1F2937",
        "accent": "16A34A",
        "accent_alt": "0F766E",
        "soft": "DCFCE7",
        "card": "F0FDF4",
        "gradient_from": "ECFDF5",
        "gradient_to": "DCFCE7",
    },
    "wps_business_blue": {
        "title": "1E3A8A",
        "body": "334155",
        "accent": "1D4ED8",
        "accent_alt": "0EA5E9",
        "soft": "DBEAFE",
        "card": "F8FAFC",
        "gradient_from": "EFF6FF",
        "gradient_to": "DBEAFE",
        "theme": "wps",
    },
    "wps_minimal_gray": {
        "title": "0F172A",
        "body": "334155",
        "accent": "475569",
        "accent_alt": "64748B",
        "soft": "E2E8F0",
        "card": "F8FAFC",
        "gradient_from": "F8FAFC",
        "gradient_to": "E2E8F0",
        "theme": "wps",
    },
    "wps_fresh_green": {
        "title": "14532D",
        "body": "1F2937",
        "accent": "16A34A",
        "accent_alt": "0D9488",
        "soft": "DCFCE7",
        "card": "F7FEE7",
        "gradient_from": "ECFDF5",
        "gradient_to": "DCFCE7",
        "theme": "wps",
    },
}

ROLE_ICON_MAP: dict[str, str] = {
    "cover": "✦",
    "table_of_contents": "☰",
    "three_columns": "◫",
    "four_cards": "❖",
    "three_steps": "➜",
    "three_bullets": "•",
    "two_cards": "⇄",
    "single_text": "✎",
}
KEYWORD_ICON_MAP: list[tuple[str, str]] = [
    ("代码", "⌘"),
    ("编程", "⌘"),
    ("算法", "∑"),
    ("流程", "↺"),
    ("步骤", "➜"),
    ("应用", "⚙"),
    ("实战", "⚒"),
    ("总结", "✓"),
]


def _safe_filename(name: str) -> str:
    """清理文件名，移除不安全字符。"""
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")[:80]


def _resolve_style_palette(style: str) -> dict[str, str]:
    style_key = str(style or "").strip().lower()
    return STYLE_PALETTES.get(style_key, STYLE_PALETTES["modern_minimal"])


def _download_binary(url: str, save_path: Path, timeout: float = 30.0) -> None:
    """下载二进制文件到本地。"""
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        save_path.write_bytes(response.content)


def _download_json(url: str, timeout: float = 30.0) -> dict[str, Any]:
    """下载 JSON 配置。"""
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("模板配置下载成功，但内容不是 JSON 对象")
    return payload


def _download_image_bytes(url: str, timeout: float = 20.0) -> bytes:
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _apply_gradient_fill(shape, color_from: str, color_to: str) -> None:
    fill = shape.fill
    try:
        fill.gradient()
        stops = list(fill.gradient_stops)
        if len(stops) >= 2:
            stops[0].color.rgb = RGBColor.from_string(color_from)
            stops[0].position = 0.0
            stops[-1].color.rgb = RGBColor.from_string(color_to)
            stops[-1].position = 1.0
        else:
            fill.solid()
            fill.fore_color.rgb = RGBColor.from_string(color_from)
    except Exception:
        fill.solid()
        fill.fore_color.rgb = RGBColor.from_string(color_from)


def _template_has_required_files(template_dir: Path, template_id: str) -> bool:
    """检查模板目录是否可用。"""
    if not template_dir.exists():
        return False
    has_pptx = any(path.suffix.lower() == ".pptx" for path in template_dir.iterdir() if path.is_file())
    has_config = (template_dir / "template.config.json").exists() or (template_dir / f"{template_id}.config.json").exists()
    return has_pptx and has_config


def _build_default_template_config(template_id: str, template_file: str) -> dict[str, Any]:
    """生成最小可用模板配置。"""
    return merge_template_config(
        template_id,
        {
            "name": template_id,
            "description": "在线导入模板（自动生成默认配置）",
            "template_file": template_file,
            "render_options": {
                "preserve_template_shapes": False,
                "enable_icons": True,
                "enable_image_placeholders": True,
                "enable_dynamic_gradient": True,
            },
        },
    )


def ensure_template_available(
    *,
    template_id: str,
    template_source_url: str = "",
    template_config_url: str = "",
) -> Path | None:
    """确保模板在本地可用；若缺失则按 URL 下载并生成配置。"""
    normalized_id = str(template_id or "").strip()
    if normalized_id in {"auto", "cn_ink_education"}:
        normalized_id = DEFAULT_TEMPLATE_ID
    if not normalized_id:
        raise ValueError("template_id 不能为空")

    template_dir = PPT_TEMPLATE_DIR / normalized_id
    if _template_has_required_files(template_dir, normalized_id):
        return template_dir

    catalog_spec = get_builtin_template_spec(normalized_id)
    source_url = str(template_source_url or "").strip() or str((catalog_spec or {}).get("source_url", "")).strip()
    resolved_config_url = (
        str(template_config_url or "").strip()
        or str((catalog_spec or {}).get("config_url", "")).strip()
    )
    if not source_url:
        return None

    template_dir.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(source_url)
    file_name = unquote(Path(parsed.path).name)
    if not file_name.lower().endswith(".pptx"):
        file_name = f"{normalized_id}.pptx"
    template_file_path = template_dir / _safe_filename(file_name)
    if template_file_path.suffix.lower() != ".pptx":
        template_file_path = template_file_path.with_suffix(".pptx")

    _download_binary(source_url, template_file_path)
    content = template_file_path.read_bytes()[:2]
    if content != b"PK":
        raise ValueError("模板下载完成，但文件不是合法的 PPTX（ZIP）格式")

    config_path = template_dir / f"{normalized_id}.config.json"
    if resolved_config_url:
        config_data = _download_json(resolved_config_url)
    elif isinstance((catalog_spec or {}).get("config"), dict):
        config_data = dict((catalog_spec or {}).get("config", {}))
    else:
        config_data = _build_default_template_config(normalized_id, template_file_path.name)
    config_data.setdefault("template_file", template_file_path.name)
    config_path.write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return template_dir


def _find_template_dir(template_id: str) -> Path:
    """查找模板目录。"""
    normalized_id = str(template_id or "").strip()
    if normalized_id in {"auto", "cn_ink_education"}:
        normalized_id = DEFAULT_TEMPLATE_ID
    template_dir = PPT_TEMPLATE_DIR / normalized_id
    if template_dir.exists():
        return template_dir

    if TEMPLATE_BASE_DIR.exists():
        for subdir in TEMPLATE_BASE_DIR.iterdir():
            if subdir.is_dir():
                config_path = subdir / f"{normalized_id}.config.json"
                if config_path.exists():
                    return subdir

    raise FileNotFoundError(f"未找到模板目录: {normalized_id}")


def _load_template_config(template_dir: Path, template_id: str) -> dict:
    """加载模板配置文件。"""
    config_path = template_dir / "template.config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return merge_template_config(template_id, json.load(f))

    config_path = template_dir / f"{template_id}.config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return merge_template_config(template_id, json.load(f))

    raise FileNotFoundError(f"未找到模板配置文件: {template_dir}")


def _find_template_file(template_dir: Path, config: dict) -> Path:
    """查找模板文件。"""
    template_file = config.get("template_file")
    if template_file:
        template_path = template_dir / template_file
        if template_path.exists():
            return template_path

    for f in template_dir.iterdir():
        if f.suffix == ".pptx":
            return f

    raise FileNotFoundError(f"未找到模板文件: {template_dir}")


def _get_slide_index_for_role(config: dict, page_role: str) -> int:
    """根据 page_role 获取模板幻灯片索引。"""
    slide_defs = config.get("slide_definitions", [])

    for slide_def in slide_defs:
        if slide_def.get("page_role") == page_role:
            return slide_def.get("slide_number", 1) - 1

    for slide_def in slide_defs:
        if slide_def.get("reusable", False):
            return slide_def.get("slide_number", 1) - 1

    return 0


def _copy_slide(prs: Presentation, slide_idx: int, preserve_template_shapes: bool) -> Any:
    """复制模板中的幻灯片，并保留视觉元素。"""
    if slide_idx >= len(prs.slides):
        # 使用空白布局
        try:
            slide_layout = prs.slide_layouts[6]
        except IndexError:
            slide_layout = prs.slide_layouts[0]
        return prs.slides.add_slide(slide_layout)

    template_slide = prs.slides[slide_idx]
    new_slide = prs.slides.add_slide(template_slide.slide_layout)
    if not preserve_template_shapes:
        return new_slide

    # 先清空新页默认占位符，再复制模板页全部形状 XML（背景图形/图片/装饰也会保留）
    sp_tree = new_slide.shapes._spTree
    for element in list(sp_tree)[2:]:
        sp_tree.remove(element)
    for element in list(template_slide.shapes._spTree)[2:]:
        sp_tree.insert_element_before(deepcopy(element), "p:extLst")

    # 复制模板页关系（图片等资源依赖）
    for rel in template_slide.part.rels.values():
        if "notesSlide" in rel.reltype:
            continue
        try:
            if rel.is_external:
                new_slide.part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
            else:
                new_slide.part.rels.get_or_add(rel.reltype, rel._target)
        except Exception:
            continue
    return new_slide


def _clear_text_frames(slide) -> None:
    """清除幻灯片中的文本内容（保留图形元素与版式）。"""
    for shape in slide.shapes:
        if shape.has_text_frame:
            shape.text_frame.clear()


def _add_text_box(slide, left: float, top: float, width: float, height: float,
                  text: str, font_size: int = 18, bold: bool = False,
                  color: str = "333333", align: PP_ALIGN = PP_ALIGN.LEFT) -> None:
    """在幻灯片上添加文本框。"""
    text_box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    text_frame = text_box.text_frame
    text_frame.word_wrap = True

    p = text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = RGBColor.from_string(color)
    p.alignment = align


def _add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    fill_color: str,
    gradient_to: str = "",
    line_color: str = "",
) -> None:
    card = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    if gradient_to:
        _apply_gradient_fill(card, fill_color, gradient_to)
    else:
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor.from_string(fill_color)
    if line_color:
        card.line.color.rgb = RGBColor.from_string(line_color)
        card.line.width = Pt(1.2)
    else:
        card.line.fill.background()


def _resolve_icon_symbol(page_role: str, title: str) -> str:
    title_text = str(title or "")
    for keyword, symbol in KEYWORD_ICON_MAP:
        if keyword in title_text:
            return symbol
    return ROLE_ICON_MAP.get(page_role, "✦")


def _add_title_icon(slide, icon_symbol: str, palette: dict[str, str]) -> None:
    badge = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.OVAL,
        Inches(0.45),
        Inches(0.28),
        Inches(0.4),
        Inches(0.4),
    )
    _apply_gradient_fill(badge, palette["accent"], palette["accent_alt"])
    badge.line.fill.background()
    _add_text_box(
        slide,
        0.45,
        0.285,
        0.4,
        0.35,
        icon_symbol,
        font_size=14,
        bold=True,
        color="FFFFFF",
        align=PP_ALIGN.CENTER,
    )


def _extract_image_url(slide_data: dict[str, Any]) -> str:
    slots = slide_data.get("slots", {})
    if not isinstance(slots, dict):
        slots = {}
    candidates = [
        slide_data.get("image_url"),
        slots.get("image_url"),
        slots.get("image"),
        slots.get("illustration_url"),
        slots.get("pic_url"),
    ]
    for value in candidates:
        url = str(value or "").strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
    return ""


def _add_image_or_placeholder(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    slide_data: dict[str, Any],
    palette: dict[str, str],
) -> None:
    image_url = _extract_image_url(slide_data)
    if image_url:
        try:
            image_bytes = _download_image_bytes(image_url)
            slide.shapes.add_picture(
                BytesIO(image_bytes),
                Inches(left),
                Inches(top),
                width=Inches(width),
                height=Inches(height),
            )
            return
        except Exception:
            pass

    placeholder = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    _apply_gradient_fill(placeholder, palette["soft"], palette["gradient_to"])
    placeholder.line.color.rgb = RGBColor.from_string(palette["accent"])
    placeholder.line.width = Pt(1.2)
    _add_text_box(
        slide,
        left + 0.2,
        top + 0.1,
        width - 0.4,
        0.45,
        "🖼 配图占位",
        font_size=14,
        bold=True,
        color=palette["accent_alt"],
        align=PP_ALIGN.CENTER,
    )
    hint = ""
    slots = slide_data.get("slots", {})
    if isinstance(slots, dict):
        hint = str(slots.get("image_hint") or slots.get("image_desc") or "").strip()
    if hint:
        _add_text_box(
            slide,
            left + 0.25,
            top + 0.62,
            width - 0.5,
            height - 0.8,
            hint,
            font_size=12,
            color=palette["body"],
            align=PP_ALIGN.LEFT,
        )


def _slot_text(slots: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = slots.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _collect_slot_lines(slots: dict[str, Any], keys: list[str]) -> list[str]:
    lines: list[str] = []
    for key in keys:
        value = _slot_text(slots, key)
        if value:
            lines.append(value)
    return lines


def _add_straight_connector(
    slide,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    color: str,
    *,
    width: float = 1.8,
) -> None:
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(start_x),
        Inches(start_y),
        Inches(end_x),
        Inches(end_y),
    )
    connector.line.color.rgb = RGBColor.from_string(color)
    connector.line.width = Pt(width)


def _render_hero_image_split(
    slide,
    title: str,
    slots: dict[str, Any],
    palette: dict[str, str],
    *,
    enable_dynamic_gradient: bool,
    enable_image_placeholders: bool,
) -> None:
    _add_text_box(slide, 0.8, 0.35, 12.0, 0.65, title, font_size=30, bold=True, color=palette["title"])
    subtitle = _slot_text(slots, "subtitle", "overview")
    if subtitle:
        _add_text_box(slide, 0.8, 1.03, 12.0, 0.45, subtitle, font_size=15, color=palette["accent"])

    _add_card(
        slide,
        0.8,
        1.45,
        6.45,
        5.55,
        palette["soft"],
        gradient_to=palette["card"] if enable_dynamic_gradient else "",
        line_color=palette["accent"],
    )
    if enable_image_placeholders:
        _add_image_or_placeholder(slide, 1.06, 1.78, 5.95, 4.95, {"slots": slots}, palette)

    _add_card(
        slide,
        7.45,
        1.45,
        5.1,
        5.55,
        palette["card"],
        gradient_to=palette["gradient_from"] if enable_dynamic_gradient else "",
        line_color=palette["accent"],
    )
    _add_text_box(slide, 7.72, 1.78, 4.5, 0.45, "核心要点", font_size=18, bold=True, color=palette["title"])

    points = _collect_slot_lines(
        slots,
        ["point1", "point2", "point3", "point4", "item1_body", "item2_body", "item3_body", "item4_body"],
    )
    if not points:
        points = ["聚焦主题场景", "拆解关键概念", "强化实战策略", "沉淀可复用方法"]
    for idx, point in enumerate(points[:4]):
        top = 2.32 + idx * 1.08
        bullet = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(7.76),
            Inches(top + 0.1),
            Inches(0.24),
            Inches(0.24),
        )
        bullet.fill.solid()
        bullet.fill.fore_color.rgb = RGBColor.from_string(palette["accent"])
        bullet.line.fill.background()
        _add_text_box(slide, 8.05, top, 4.15, 0.62, point, font_size=14, color=palette["body"])


def _render_icon_process_row(
    slide,
    title: str,
    slots: dict[str, Any],
    palette: dict[str, str],
    *,
    enable_dynamic_gradient: bool,
) -> None:
    _add_text_box(slide, 0.8, 0.35, 12.0, 0.65, title, font_size=30, bold=True, color=palette["title"])
    subtitle = _slot_text(slots, "subtitle", "overview")
    if subtitle:
        _add_text_box(slide, 0.8, 1.03, 12.0, 0.45, subtitle, font_size=15, color=palette["accent"])

    card_top = 2.0
    card_width = 2.6
    gap = 0.45
    start_left = 0.92
    icon_tokens = ["A", "B", "C", "D"]
    for i in range(1, 5):
        left = start_left + (i - 1) * (card_width + gap)
        _add_card(
            slide,
            left,
            card_top,
            card_width,
            3.4,
            palette["soft"],
            gradient_to=palette["card"] if enable_dynamic_gradient else "",
            line_color=palette["accent"],
        )
        badge = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(left + 0.82),
            Inches(card_top + 0.32),
            Inches(0.95),
            Inches(0.95),
        )
        _apply_gradient_fill(badge, palette["accent"], palette["accent_alt"])
        badge.line.fill.background()
        _add_text_box(
            slide,
            left + 0.82,
            card_top + 0.52,
            0.95,
            0.42,
            icon_tokens[i - 1],
            font_size=18,
            bold=True,
            color="FFFFFF",
            align=PP_ALIGN.CENTER,
        )

        title_value = _slot_text(slots, f"item{i}_title")
        body_value = _slot_text(slots, f"item{i}_body")
        if i == 4:
            title_value = _slot_text(slots, "result_title", f"item{i}_title", default=title_value)
            body_value = _slot_text(slots, "result_body", f"item{i}_body", default=body_value)
        if not title_value:
            title_value = f"阶段 {i}"
        _add_text_box(
            slide,
            left + 0.18,
            card_top + 1.38,
            card_width - 0.36,
            0.5,
            title_value,
            font_size=16,
            bold=True,
            color=palette["title"],
            align=PP_ALIGN.CENTER,
        )
        if body_value:
            _add_text_box(
                slide,
                left + 0.18,
                card_top + 1.95,
                card_width - 0.36,
                1.25,
                body_value,
                font_size=13,
                color=palette["body"],
                align=PP_ALIGN.CENTER,
            )
        if i < 4:
            symbol = "+" if i < 3 else "="
            _add_text_box(
                slide,
                left + card_width + 0.1,
                card_top + 1.42,
                0.26,
                0.4,
                symbol,
                font_size=24,
                bold=True,
                color=palette["accent"],
                align=PP_ALIGN.CENTER,
            )


def _render_hex_cycle(
    slide,
    title: str,
    slots: dict[str, Any],
    palette: dict[str, str],
    *,
    enable_dynamic_gradient: bool,
) -> None:
    _add_text_box(slide, 0.8, 0.35, 12.0, 0.65, title, font_size=30, bold=True, color=palette["title"])
    center_left, center_top, center_w, center_h = 5.45, 2.35, 2.45, 2.25
    core = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.HEXAGON,
        Inches(center_left),
        Inches(center_top),
        Inches(center_w),
        Inches(center_h),
    )
    if enable_dynamic_gradient:
        _apply_gradient_fill(core, palette["accent"], palette["accent_alt"])
    else:
        core.fill.solid()
        core.fill.fore_color.rgb = RGBColor.from_string(palette["accent"])
    core.line.fill.background()
    _add_text_box(
        slide,
        center_left + 0.2,
        center_top + 0.45,
        center_w - 0.4,
        0.55,
        _slot_text(slots, "center_title", default="核心主题"),
        font_size=17,
        bold=True,
        color="FFFFFF",
        align=PP_ALIGN.CENTER,
    )
    center_body = _slot_text(slots, "center_body")
    if center_body:
        _add_text_box(
            slide,
            center_left + 0.22,
            center_top + 1.03,
            center_w - 0.44,
            0.72,
            center_body,
            font_size=12,
            color="FFFFFF",
            align=PP_ALIGN.CENTER,
        )

    node_defs = [
        ("left_top", 1.0, 1.65, center_left, center_top + 0.7, 3.6, 2.15),
        ("left_middle", 0.75, 3.02, center_left, center_top + center_h / 2, 3.35, 3.47),
        ("left_bottom", 1.0, 4.35, center_left, center_top + center_h - 0.7, 3.6, 4.85),
        ("right_top", 9.85, 1.65, center_left + center_w, center_top + 0.7, 9.85, 2.15),
        ("right_middle", 10.1, 3.02, center_left + center_w, center_top + center_h / 2, 9.85, 3.47),
        ("right_bottom", 9.85, 4.35, center_left + center_w, center_top + center_h - 0.7, 9.85, 4.85),
    ]
    for key, left, top, from_x, from_y, to_x, to_y in node_defs:
        _add_card(
            slide,
            left,
            top,
            2.45,
            0.98,
            palette["soft"],
            gradient_to=palette["card"] if enable_dynamic_gradient else "",
            line_color=palette["accent"],
        )
        label = _slot_text(slots, key, default=key.replace("_", " ").title())
        _add_text_box(slide, left + 0.14, top + 0.17, 2.15, 0.65, label, font_size=13, color=palette["body"], align=PP_ALIGN.CENTER)
        _add_straight_connector(slide, from_x, from_y, to_x, to_y, palette["accent"], width=1.4)


def _render_target_illustration(
    slide,
    title: str,
    slots: dict[str, Any],
    palette: dict[str, str],
    *,
    enable_dynamic_gradient: bool,
    enable_image_placeholders: bool,
) -> None:
    _add_text_box(slide, 0.8, 0.35, 12.0, 0.65, title, font_size=30, bold=True, color=palette["title"])
    _add_card(
        slide,
        0.8,
        1.45,
        5.55,
        5.5,
        palette["soft"],
        gradient_to=palette["card"] if enable_dynamic_gradient else "",
        line_color=palette["accent"],
    )
    kpi_title = _slot_text(slots, "kpi_title", default="关键指标")
    kpi_value = _slot_text(slots, "kpi_value", default="95%")
    _add_text_box(slide, 1.08, 1.75, 5.0, 0.52, kpi_title, font_size=18, bold=True, color=palette["title"])
    _add_text_box(slide, 1.08, 2.28, 5.0, 0.92, kpi_value, font_size=40, bold=True, color=palette["accent"])
    kpi_desc = _slot_text(slots, "kpi_desc")
    if kpi_desc:
        _add_text_box(slide, 1.08, 3.15, 4.95, 0.65, kpi_desc, font_size=13, color=palette["body"])

    points = _collect_slot_lines(slots, ["point1", "point2", "point3", "item1_body", "item2_body", "item3_body"])
    if not points:
        points = ["聚焦可量化目标", "用证据驱动决策", "形成闭环改进"]
    for idx, point in enumerate(points[:3]):
        y = 4.0 + idx * 0.9
        _add_text_box(slide, 1.18, y, 4.9, 0.56, f"• {point}", font_size=13, color=palette["body"])

    _add_card(
        slide,
        6.55,
        1.45,
        6.0,
        5.5,
        palette["card"],
        gradient_to=palette["gradient_from"] if enable_dynamic_gradient else "",
        line_color=palette["accent"],
    )
    target_specs = [(8.0, 2.05, 3.0, 3.0), (8.45, 2.5, 2.1, 2.1), (8.85, 2.9, 1.3, 1.3)]
    for left, top, width, height in target_specs:
        ring = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
        )
        ring.fill.background()
        ring.line.color.rgb = RGBColor.from_string(palette["accent"])
        ring.line.width = Pt(2)
    center_dot = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.OVAL,
        Inches(9.42),
        Inches(3.47),
        Inches(0.16),
        Inches(0.16),
    )
    center_dot.fill.solid()
    center_dot.fill.fore_color.rgb = RGBColor.from_string(palette["accent_alt"])
    center_dot.line.fill.background()

    arrow = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
        Inches(7.0),
        Inches(3.35),
        Inches(1.05),
        Inches(0.34),
    )
    if enable_dynamic_gradient:
        _apply_gradient_fill(arrow, palette["accent"], palette["accent_alt"])
    else:
        arrow.fill.solid()
        arrow.fill.fore_color.rgb = RGBColor.from_string(palette["accent"])
    arrow.line.fill.background()

    if enable_image_placeholders:
        _add_image_or_placeholder(slide, 10.22, 4.58, 2.08, 1.92, {"slots": slots}, palette)


def _render_road_timeline(
    slide,
    title: str,
    slots: dict[str, Any],
    palette: dict[str, str],
    *,
    enable_dynamic_gradient: bool,
) -> None:
    _add_text_box(slide, 0.8, 0.35, 12.0, 0.65, title, font_size=30, bold=True, color=palette["title"])
    y_points = [3.85, 2.75, 3.95, 2.9, 3.82]
    x_points = [1.35, 3.62, 5.89, 8.16, 10.43]

    for idx in range(4):
        _add_straight_connector(
            slide,
            x_points[idx] + 0.32,
            y_points[idx] + 0.32,
            x_points[idx + 1] + 0.32,
            y_points[idx + 1] + 0.32,
            palette["accent"],
            width=2.2,
        )

    for i in range(1, 6):
        x = x_points[i - 1]
        y = y_points[i - 1]
        node = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(x),
            Inches(y),
            Inches(0.65),
            Inches(0.65),
        )
        if enable_dynamic_gradient:
            _apply_gradient_fill(node, palette["accent"], palette["accent_alt"])
        else:
            node.fill.solid()
            node.fill.fore_color.rgb = RGBColor.from_string(palette["accent"])
        node.line.fill.background()
        _add_text_box(slide, x, y + 0.14, 0.65, 0.34, str(i), font_size=14, bold=True, color="FFFFFF", align=PP_ALIGN.CENTER)

        top = y - 1.47 if i % 2 == 1 else y + 0.75
        _add_card(
            slide,
            x - 0.78,
            top,
            2.2,
            1.25,
            palette["soft"],
            gradient_to=palette["card"] if enable_dynamic_gradient else "",
            line_color=palette["accent"],
        )
        item_title = _slot_text(slots, f"milestone{i}_title", default=f"里程碑 {i}")
        item_body = _slot_text(slots, f"milestone{i}_body")
        _add_text_box(slide, x - 0.64, top + 0.12, 1.92, 0.42, item_title, font_size=12, bold=True, color=palette["title"])
        if item_body:
            _add_text_box(slide, x - 0.64, top + 0.56, 1.92, 0.55, item_body, font_size=10, color=palette["body"])


def _render_concentric_focus(
    slide,
    title: str,
    slots: dict[str, Any],
    palette: dict[str, str],
) -> None:
    _add_text_box(slide, 0.8, 0.35, 12.0, 0.65, title, font_size=30, bold=True, color=palette["title"])
    ring_specs = [
        (3.4, 1.55, 5.55, 4.75, 2.4),
        (3.95, 2.0, 4.45, 3.85, 2.2),
        (4.45, 2.45, 3.45, 2.95, 2.0),
        (4.95, 2.9, 2.45, 2.05, 1.8),
    ]
    for left, top, width, height, line_width in ring_specs:
        ring = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.OVAL,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
        )
        ring.fill.background()
        ring.line.color.rgb = RGBColor.from_string(palette["accent"])
        ring.line.width = Pt(line_width)

    _add_text_box(
        slide,
        5.18,
        3.18,
        1.95,
        0.72,
        _slot_text(slots, "core_title", default="核心"),
        font_size=18,
        bold=True,
        color=palette["accent_alt"],
        align=PP_ALIGN.CENTER,
    )
    core_body = _slot_text(slots, "core_body")
    if core_body:
        _add_text_box(slide, 4.8, 3.78, 2.75, 0.48, core_body, font_size=11, color=palette["body"], align=PP_ALIGN.CENTER)

    ring_keys = ["ring1_title", "ring2_title", "ring3_title", "ring4_title"]
    ring_anchor_y = [2.05, 2.95, 3.85, 4.75]
    for idx, key in enumerate(ring_keys):
        label = _slot_text(slots, key, default=f"层级 {idx + 1}")
        box_left = 9.12
        box_top = 1.85 + idx * 1.06
        _add_card(slide, box_left, box_top, 3.15, 0.86, palette["soft"], line_color=palette["accent"])
        _add_text_box(slide, box_left + 0.18, box_top + 0.17, 2.8, 0.45, label, font_size=12, color=palette["body"])
        _add_straight_connector(slide, 8.95, ring_anchor_y[idx], box_left, box_top + 0.43, palette["accent"], width=1.2)

    note = _slot_text(slots, "note")
    if note:
        _add_text_box(slide, 0.9, 6.45, 11.95, 0.4, note, font_size=12, color=palette["accent"])


def _apply_visual_theme(
    slide,
    page_role: str,
    palette: dict[str, str],
    *,
    enable_dynamic_gradient: bool,
) -> None:
    """在模板缺少视觉元素时叠加轻量化装饰。"""
    accent = palette["accent"]
    soft = palette["soft"]
    card = palette["card"]

    canvas = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.0),
        Inches(0.0),
        Inches(13.333),
        Inches(7.5),
    )
    if enable_dynamic_gradient:
        _apply_gradient_fill(canvas, palette["gradient_from"], "FFFFFF")
    else:
        canvas.fill.solid()
        canvas.fill.fore_color.rgb = RGBColor.from_string("FFFFFF")
    canvas.line.fill.background()
    theme_name = str(palette.get("theme", "")).strip().lower()
    if page_role == "cover":
        ribbon = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            Inches(0.0),
            Inches(0.0),
            Inches(13.333),
            Inches(1.15),
        )
        if enable_dynamic_gradient:
            _apply_gradient_fill(ribbon, accent, palette["accent_alt"])
        else:
            ribbon.fill.solid()
            ribbon.fill.fore_color.rgb = RGBColor.from_string(accent)
        ribbon.line.fill.background()
        subtitle_bg = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(0.8),
            Inches(2.0),
            Inches(11.7),
            Inches(3.8),
        )
        if enable_dynamic_gradient:
            _apply_gradient_fill(subtitle_bg, soft, palette["card"])
        else:
            subtitle_bg.fill.solid()
            subtitle_bg.fill.fore_color.rgb = RGBColor.from_string(soft)
        subtitle_bg.fill.transparency = 0.15
        subtitle_bg.line.fill.background()
    else:
        if theme_name == "wps":
            side = slide.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RECTANGLE,
                Inches(0.0),
                Inches(0.25),
                Inches(0.18),
                Inches(7.25),
            )
            if enable_dynamic_gradient:
                _apply_gradient_fill(side, accent, palette["accent_alt"])
            else:
                side.fill.solid()
                side.fill.fore_color.rgb = RGBColor.from_string(accent)
            side.line.fill.background()
        top_bar = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            Inches(0.0),
            Inches(0.0),
            Inches(13.333),
            Inches(0.25),
        )
        if enable_dynamic_gradient:
            _apply_gradient_fill(top_bar, accent, palette["accent_alt"])
        else:
            top_bar.fill.solid()
            top_bar.fill.fore_color.rgb = RGBColor.from_string(accent)
        top_bar.line.fill.background()
        tag = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(0.35),
            Inches(0.28),
            Inches(2.0),
            Inches(0.32),
        )
        if enable_dynamic_gradient:
            _apply_gradient_fill(tag, soft, palette["card"])
        else:
            tag.fill.solid()
            tag.fill.fore_color.rgb = RGBColor.from_string(soft)
        tag.line.fill.background()
        content_bg = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(0.35),
            Inches(1.15),
            Inches(12.6),
            Inches(6.05),
        )
        if enable_dynamic_gradient:
            _apply_gradient_fill(content_bg, card, palette["gradient_from"])
        else:
            content_bg.fill.solid()
            content_bg.fill.fore_color.rgb = RGBColor.from_string(card)
        content_bg.line.fill.background()


def _render_slide_content(slide, slide_data: dict, style: str, render_options: dict[str, Any]) -> None:
    """在幻灯片上渲染内容。"""
    title = slide_data.get("title", "")
    slots = slide_data.get("slots", {})
    slots = slots if isinstance(slots, dict) else {}
    page_role = slide_data.get("page_role", "")
    enable_icons = bool(render_options.get("enable_icons", True))
    enable_image_placeholders = bool(render_options.get("enable_image_placeholders", True))
    enable_dynamic_gradient = bool(render_options.get("enable_dynamic_gradient", True))
    palette = _resolve_style_palette(style)
    title_color = palette["title"]
    body_color = palette["body"]
    muted_color = palette["accent"]
    subtle_color = palette["body"]
    accent = palette["accent"]
    _apply_visual_theme(
        slide,
        page_role,
        palette,
        enable_dynamic_gradient=enable_dynamic_gradient,
    )
    if enable_icons:
        _add_title_icon(slide, _resolve_icon_symbol(page_role, title), palette)

    # 根据页面类型布局内容
    if page_role == "cover":
        _add_text_box(slide, 0.9, 0.2, 11.7, 0.8, title, font_size=40, bold=True,
                      color=title_color, align=PP_ALIGN.CENTER)
        if slots.get("subtitle"):
            _add_text_box(slide, 1.2, 2.6, 10.9, 0.9, slots["subtitle"], font_size=26,
                          color=muted_color, align=PP_ALIGN.CENTER)
        if slots.get("presenter"):
            _add_text_box(slide, 1.2, 4.1, 10.9, 0.5, slots["presenter"], font_size=18,
                          color=subtle_color, align=PP_ALIGN.CENTER)
        if enable_image_placeholders:
            _add_image_or_placeholder(slide, 9.1, 2.45, 3.0, 2.2, slide_data, palette)

    elif page_role == "table_of_contents":
        _add_text_box(slide, 0.9, 0.36, 11.4, 0.6, title, font_size=30, bold=True, color=title_color)
        top = 1.45
        for i in range(1, 5):
            item_title = slots.get(f"item{i}_title", "")
            item_desc = slots.get(f"item{i}_desc", "")
            if item_title:
                _add_card(slide, 0.85, top - 0.08, 11.6, 1.0, palette["soft"])
                _add_text_box(slide, 1.05, top + 0.12, 0.7, 0.45, f"{i}", font_size=20, bold=True, color=title_color, align=PP_ALIGN.CENTER)
                text = f"{i}. {item_title}"
                if item_desc:
                    text += f"：{item_desc}"
                _add_text_box(slide, 1.7, top + 0.16, 10.4, 0.6, text, font_size=20, color=body_color)
                top += 1.2

    elif page_role == "hero_image_split":
        _render_hero_image_split(
            slide,
            title,
            slots,
            palette,
            enable_dynamic_gradient=enable_dynamic_gradient,
            enable_image_placeholders=enable_image_placeholders,
        )

    elif page_role == "icon_process_row":
        _render_icon_process_row(
            slide,
            title,
            slots,
            palette,
            enable_dynamic_gradient=enable_dynamic_gradient,
        )

    elif page_role == "hex_cycle":
        _render_hex_cycle(
            slide,
            title,
            slots,
            palette,
            enable_dynamic_gradient=enable_dynamic_gradient,
        )

    elif page_role == "target_illustration":
        _render_target_illustration(
            slide,
            title,
            slots,
            palette,
            enable_dynamic_gradient=enable_dynamic_gradient,
            enable_image_placeholders=enable_image_placeholders,
        )

    elif page_role == "road_timeline":
        _render_road_timeline(
            slide,
            title,
            slots,
            palette,
            enable_dynamic_gradient=enable_dynamic_gradient,
        )

    elif page_role == "concentric_focus":
        _render_concentric_focus(slide, title, slots, palette)

    elif page_role == "three_columns":
        _add_text_box(slide, 0.8, 0.35, 12, 0.7, title, font_size=30, bold=True, color=title_color)
        col_width = 3.9
        for i in range(1, 4):
            item_title = slots.get(f"item{i}_title", "")
            item_body = slots.get(f"item{i}_body", "")
            left = 0.65 + (i - 1) * 4.15
            _add_card(
                slide,
                left,
                1.35,
                col_width,
                4.95,
                palette["soft"],
                gradient_to=palette["card"] if enable_dynamic_gradient else "",
                line_color=palette["accent"],
            )
            if item_title:
                _add_text_box(slide, left + 0.2, 1.55, col_width - 0.4, 0.55, item_title, font_size=20, bold=True, color=title_color)
            if item_body:
                _add_text_box(slide, left + 0.2, 2.2, col_width - 0.4, 3.9, item_body, font_size=16, color=body_color)
        if enable_image_placeholders:
            _add_image_or_placeholder(slide, 8.85, 4.85, 3.5, 1.25, slide_data, palette)

    elif page_role == "four_cards":
        _add_text_box(slide, 0.8, 0.35, 12, 0.7, title, font_size=30, bold=True, color=title_color)
        for i in range(1, 5):
            item_title = slots.get(f"item{i}_title", "")
            item_body = slots.get(f"item{i}_body", "")
            row = (i - 1) // 2
            col = (i - 1) % 2
            left = 0.8 + col * 6.1
            top = 1.45 + row * 2.8
            _add_card(
                slide,
                left,
                top,
                5.7,
                2.45,
                palette["soft"],
                gradient_to=palette["card"] if enable_dynamic_gradient else "",
                line_color=palette["accent"],
            )
            if item_title:
                _add_text_box(slide, left + 0.2, top + 0.18, 5.3, 0.45, item_title, font_size=18, bold=True, color=title_color)
            if item_body:
                _add_text_box(slide, left + 0.2, top + 0.75, 5.3, 1.45, item_body, font_size=14, color=body_color)

    elif page_role == "three_steps":
        _add_text_box(slide, 0.8, 0.35, 12, 0.7, title, font_size=30, bold=True, color=title_color)
        for i in range(1, 4):
            step_title = slots.get(f"step{i}_title", "")
            step_body = slots.get(f"step{i}_body", "")
            left = 0.7 + (i - 1) * 4.15
            _add_card(
                slide,
                left,
                1.55,
                3.9,
                4.75,
                palette["soft"],
                gradient_to=palette["card"] if enable_dynamic_gradient else "",
                line_color=palette["accent"],
            )
            if step_title:
                _add_text_box(slide, left + 0.2, 1.72, 3.45, 0.45, f"步骤{i}：{step_title}", font_size=18, bold=True, color=title_color)
            if step_body:
                _add_text_box(slide, left + 0.2, 2.35, 3.45, 3.75, step_body, font_size=14, color=body_color)
            if i < 3:
                card_width = 3.9
                gap = 0.25
                arrow_width = gap - 0.04
                arrow_height = 0.34
                arrow_left = left + card_width + 0.02
                arrow_top = 1.55 + (4.75 - arrow_height) / 2
                connector = slide.shapes.add_shape(
                    MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
                    Inches(arrow_left),
                    Inches(arrow_top),
                    Inches(arrow_width),
                    Inches(arrow_height),
                )
                connector.fill.solid()
                connector.fill.fore_color.rgb = RGBColor.from_string(accent)
                connector.line.fill.background()

    elif page_role == "three_bullets":
        _add_text_box(slide, 0.8, 0.35, 12, 0.7, title, font_size=30, bold=True, color=title_color)
        top = 1.55
        for i in range(1, 4):
            item_body = slots.get(f"item{i}_body", "")
            if item_body:
                _add_card(
                    slide,
                    1.0,
                    top - 0.04,
                    11.2,
                    1.05,
                    palette["soft"],
                    gradient_to=palette["card"] if enable_dynamic_gradient else "",
                    line_color=palette["accent"],
                )
                _add_text_box(slide, 1.25, top + 0.2, 10.7, 0.7, f"• {item_body}", font_size=18, color=body_color)
                top += 1.35

    elif page_role == "two_cards":
        _add_text_box(slide, 0.8, 0.35, 12, 0.7, title, font_size=30, bold=True, color=title_color)
        for i in range(1, 3):
            item_title = slots.get(f"item{i}_title", "")
            item_body = slots.get(f"item{i}_body", "")
            left = 0.85 + (i - 1) * 6.15
            _add_card(
                slide,
                left,
                1.55,
                5.6,
                4.85,
                palette["soft"],
                gradient_to=palette["card"] if enable_dynamic_gradient else "",
                line_color=palette["accent"],
            )
            if item_title:
                _add_text_box(slide, left + 0.2, 1.78, 5.2, 0.55, item_title, font_size=20, bold=True, color=title_color)
            if item_body:
                _add_text_box(slide, left + 0.2, 2.5, 5.2, 3.7, item_body, font_size=16, color=body_color)
        if enable_image_placeholders:
            _add_image_or_placeholder(slide, 9.15, 4.75, 3.0, 1.45, slide_data, palette)

    else:
        # 默认单栏布局
        _add_text_box(slide, 0.8, 0.35, 12, 0.7, title, font_size=30, bold=True, color=title_color)
        _add_card(
            slide,
            0.9,
            1.45,
            11.7,
            4.9,
            palette["soft"],
            gradient_to=palette["card"] if enable_dynamic_gradient else "",
            line_color=palette["accent"],
        )
        body = slots.get("body", "")
        if body:
            _add_text_box(slide, 1.2, 1.9, 11.1, 4.1, body, font_size=18, color=body_color)
        if enable_image_placeholders:
            _add_image_or_placeholder(slide, 8.6, 3.9, 3.55, 2.0, slide_data, palette)


def _parse_ppt_plan_json(ppt_plan_json: str) -> tuple[str, list[dict[str, Any]]]:
    """将结构化 PPT JSON 计划转换为通用幻灯片列表。"""
    try:
        raw = json.loads(ppt_plan_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ppt_plan_json 不是合法 JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("ppt_plan_json 顶层必须为对象")

    presentation_title = str(raw.get("presentation_title", "")).strip() or "演示文稿"
    raw_slides = raw.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        raise ValueError("ppt_plan_json 缺少 slides 列表")

    slides: list[dict[str, Any]] = []
    for item in raw_slides:
        if not isinstance(item, dict):
            continue
        slots = item.get("slots", {})
        slots = slots if isinstance(slots, dict) else {}
        title = str(item.get("title") or slots.get("title") or "未命名页面").strip()
        page_role = str(item.get("page_role", "")).strip()
        slides.append(
            {
                "title": title,
                "slots": slots,
                "note": str(item.get("speaker_notes", "")).strip(),
                "page_role": page_role,
                "section": str(item.get("section", "")).strip(),
            }
        )

    return presentation_title, slides


def render_ppt_plan_to_file(
    *,
    topic: str,
    ppt_plan_json: str,
    template_id: str = DEFAULT_TEMPLATE_ID,
    template_source_url: str = "",
    template_config_url: str = "",
    style: str = "modern_minimal",
) -> dict[str, Any]:
    """将结构化 JSON 计划渲染为 PPT 文件并返回结果。"""
    if not str(ppt_plan_json or "").strip():
        return {"error": "缺少必填参数 ppt_plan_json"}
    resolved_template_id = str(template_id or "").strip()
    if resolved_template_id in {"auto", "cn_ink_education"}:
        resolved_template_id = DEFAULT_TEMPLATE_ID

    try:
        presentation_title, slides = _parse_ppt_plan_json(ppt_plan_json)
    except ValueError as exc:
        return {"error": str(exc)}
    if not slides:
        return {"error": "未检测到有效的幻灯片内容（需要 slides 列表）"}

    try:
        ensure_template_available(
            template_id=resolved_template_id,
            template_source_url=template_source_url,
            template_config_url=template_config_url,
        )
    except Exception as exc:
        logger.warning("[render_ppt_plan_to_file] 在线模板下载失败，回退本地渲染: %s", exc)

    # 查找模板目录和配置
    try:
        template_dir = _find_template_dir(resolved_template_id)
        config = _load_template_config(template_dir, resolved_template_id)
        template_path = _find_template_file(template_dir, config)

        prs = Presentation(str(template_path))
        logger.info("[render_ppt_plan_to_file] 使用模板: %s", template_path)
    except FileNotFoundError as e:
        logger.warning("[render_ppt_plan_to_file] 模板不存在，创建空白演示文稿: %s", e)
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        config = {"slide_definitions": []}

    initial_template_slide_count = len(prs.slides)
    render_options = config.get("render_options", {}) if isinstance(config, dict) else {}
    preserve_template_shapes = bool(render_options.get("preserve_template_shapes", False))
    slide_titles: list[str] = []

    # 为每个内容创建新幻灯片（基于模板布局）
    for slide_data in slides:
        slide_title = slide_data["title"]
        slide_titles.append(slide_title)
        note_text = slide_data.get("note", "").strip()
        page_role = slide_data.get("page_role", "")

        # 获取模板幻灯片索引
        template_idx = _get_slide_index_for_role(config, page_role)

        # 复制模板幻灯片
        slide = _copy_slide(prs, template_idx, preserve_template_shapes=preserve_template_shapes)
        _clear_text_frames(slide)

        # 渲染内容
        _render_slide_content(slide, slide_data, style, render_options)

        # 添加讲者备注
        if note_text:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = note_text

    # 删除原始模板幻灯片（从后往前删除）
    for idx in sorted(range(initial_template_slide_count), reverse=True):
        rId = prs.slides._sldIdLst[idx].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[idx]

    # 保存文件
    PPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename_stem = _safe_filename(topic) or _safe_filename(presentation_title) or "presentation"
    filename = f"{filename_stem}.pptx"
    filepath = PPT_OUTPUT_DIR / filename
    prs.save(str(filepath))

    result = {
        "file_path": str(filepath),
        "slide_count": len(slide_titles),
        "slide_titles": slide_titles,
        "template_id": resolved_template_id,
        "input_mode": "ppt_plan_json",
        "style": style,
    }
    logger.info("[render_ppt_plan_to_file] saved: path=%s slides=%d", filepath, len(slide_titles))
    return result
