"""
PPT 模板渲染器。

基于 .pptx 模板文件生成演示文稿，在模板幻灯片上添加文本内容。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from app.infra.logging import get_logger
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

PPT_OUTPUT_DIR = WORKPLACE_DIR / "ppt"
TEMPLATE_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "template"


def _safe_filename(name: str) -> str:
    """清理文件名，移除不安全字符。"""
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")[:80]


def _find_template_dir(template_id: str) -> Path:
    """查找模板目录。"""
    template_dir = WORKPLACE_DIR / "templates" / template_id
    if template_dir.exists():
        return template_dir

    for subdir in TEMPLATE_BASE_DIR.iterdir():
        if subdir.is_dir():
            config_path = subdir / f"{template_id}.config.json"
            if config_path.exists():
                return subdir

    raise FileNotFoundError(f"未找到模板目录: {template_id}")


def _load_template_config(template_dir: Path, template_id: str) -> dict:
    """加载模板配置文件。"""
    config_path = template_dir / "template.config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    config_path = template_dir / f"{template_id}.config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

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


def _render_slide_content(slide, slide_data: dict, slide_idx: int) -> None:
    """在幻灯片上渲染内容。"""
    title = slide_data.get("title", "")
    slots = slide_data.get("slots", {})
    page_role = slide_data.get("page_role", "")

    # 根据页面类型布局内容
    if page_role == "cover":
        # 封面页：标题居中大字
        _add_text_box(slide, 1, 2.5, 11.3, 1.2, title, font_size=44, bold=True,
                      color="2E4057", align=PP_ALIGN.CENTER)
        if slots.get("subtitle"):
            _add_text_box(slide, 1, 3.8, 11.3, 0.6, slots["subtitle"], font_size=24,
                          color="666666", align=PP_ALIGN.CENTER)
        if slots.get("presenter"):
            _add_text_box(slide, 1, 4.5, 11.3, 0.5, slots["presenter"], font_size=18,
                          color="888888", align=PP_ALIGN.CENTER)

    elif page_role == "table_of_contents":
        # 目录页
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        top = 1.5
        for i in range(1, 5):
            item_title = slots.get(f"item{i}_title", "")
            item_desc = slots.get(f"item{i}_desc", "")
            if item_title:
                text = f"{i}. {item_title}"
                if item_desc:
                    text += f"：{item_desc}"
                _add_text_box(slide, 1, top, 11, 0.6, text, font_size=20, color="333333")
                top += 0.8

    elif page_role == "three_columns":
        # 三栏布局
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        col_width = 3.8
        for i in range(1, 4):
            item_title = slots.get(f"item{i}_title", "")
            item_body = slots.get(f"item{i}_body", "")
            left = 0.5 + (i - 1) * 4.2
            if item_title:
                _add_text_box(slide, left, 1.5, col_width, 0.5, item_title,
                              font_size=20, bold=True, color="2E4057")
            if item_body:
                _add_text_box(slide, left, 2.1, col_width, 3.5, item_body,
                              font_size=16, color="333333")

    elif page_role == "four_cards":
        # 四卡片布局
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        for i in range(1, 5):
            item_title = slots.get(f"item{i}_title", "")
            item_body = slots.get(f"item{i}_body", "")
            row = (i - 1) // 2
            col = (i - 1) % 2
            left = 0.5 + col * 6.4
            top = 1.5 + row * 2.8
            if item_title:
                _add_text_box(slide, left, top, 5.8, 0.5, item_title,
                              font_size=18, bold=True, color="2E4057")
            if item_body:
                _add_text_box(slide, left, top + 0.6, 5.8, 1.8, item_body,
                              font_size=14, color="333333")

    elif page_role == "three_steps":
        # 三步骤布局
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        for i in range(1, 4):
            step_title = slots.get(f"step{i}_title", "")
            step_body = slots.get(f"step{i}_body", "")
            left = 0.5 + (i - 1) * 4.2
            if step_title:
                _add_text_box(slide, left, 1.5, 3.8, 0.5, f"步骤{i}：{step_title}",
                              font_size=18, bold=True, color="2E4057")
            if step_body:
                _add_text_box(slide, left, 2.2, 3.8, 3, step_body,
                              font_size=14, color="333333")

    elif page_role == "three_bullets":
        # 三要点布局
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        top = 1.8
        for i in range(1, 4):
            item_body = slots.get(f"item{i}_body", "")
            if item_body:
                _add_text_box(slide, 1, top, 11, 1, f"• {item_body}",
                              font_size=18, color="333333")
                top += 1.2

    elif page_role == "two_cards":
        # 双卡片布局
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        for i in range(1, 3):
            item_title = slots.get(f"item{i}_title", "")
            item_body = slots.get(f"item{i}_body", "")
            left = 0.5 + (i - 1) * 6.4
            if item_title:
                _add_text_box(slide, left, 1.5, 5.8, 0.5, item_title,
                              font_size=20, bold=True, color="2E4057")
            if item_body:
                _add_text_box(slide, left, 2.2, 5.8, 3.5, item_body,
                              font_size=16, color="333333")

    else:
        # 默认单栏布局
        _add_text_box(slide, 0.5, 0.3, 12, 0.8, title, font_size=32, bold=True, color="2E4057")
        body = slots.get("body", "")
        if body:
            _add_text_box(slide, 0.8, 1.5, 11.5, 5, body, font_size=18, color="333333")


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
    template_id: str = "cn_ink_education",
    style: str = "modern_minimal",
) -> dict[str, Any]:
    """将结构化 JSON 计划渲染为 PPT 文件并返回结果。"""
    if not str(ppt_plan_json or "").strip():
        return {"error": "缺少必填参数 ppt_plan_json"}

    presentation_title, slides = _parse_ppt_plan_json(ppt_plan_json)
    if not slides:
        return {"error": "未检测到有效的幻灯片内容（需要 slides 列表）"}

    # 查找模板目录和配置
    try:
        template_dir = _find_template_dir(template_id)
        config = _load_template_config(template_dir, template_id)
        template_path = _find_template_file(template_dir, config)

        prs = Presentation(str(template_path))
        logger.info("[render_ppt_plan_to_file] 使用模板: %s", template_path)
    except FileNotFoundError as e:
        logger.warning("[render_ppt_plan_to_file] 模板不存在，创建空白演示文稿: %s", e)
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        config = {"slide_definitions": []}

    slide_titles: list[str] = []

    # 收集模板幻灯片布局
    template_layouts = []
    for slide in prs.slides:
        template_layouts.append(slide.slide_layout)

    # 清空所有幻灯片，只保留布局
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].rId
        prs.part.drop_rel(rId)
        del prs.slides._sldIdLst[0]

    for slide_data in slides:
        slide_title = slide_data["title"]
        slide_titles.append(slide_title)
        note_text = slide_data.get("note", "").strip()
        page_role = slide_data.get("page_role", "")

        # 获取模板幻灯片索引
        template_idx = _get_slide_index_for_role(config, page_role)

        # 使用对应的布局
        if template_idx < len(template_layouts):
            slide_layout = template_layouts[template_idx]
        else:
            try:
                slide_layout = template_layouts[6] if len(template_layouts) > 6 else template_layouts[0]
            except IndexError:
                slide_layout = template_layouts[0]

        slide = prs.slides.add_slide(slide_layout)

        # 渲染内容
        _render_slide_content(slide, slide_data, len(slide_titles))

        # 添加讲者备注
        if note_text:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = note_text

    # 保存文件
    PPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(topic) + ".pptx"
    filepath = PPT_OUTPUT_DIR / filename
    prs.save(str(filepath))

    result = {
        "file_path": str(filepath),
        "slide_count": len(slide_titles),
        "slide_titles": slide_titles,
        "template_id": template_id,
        "input_mode": "ppt_plan_json",
    }
    logger.info("[render_ppt_plan_to_file] saved: path=%s slides=%d", filepath, len(slide_titles))
    return result
