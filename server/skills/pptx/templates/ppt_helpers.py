"""python-pptx 原子绘图与排版辅助库 — 供 slides/sXX.py 自由组合调用。"""

from __future__ import annotations

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


def rgb(hex_str: str) -> RGBColor:
    """将 '#2563EB' 或 '2563EB' 转为 RGBColor。"""
    clean = (hex_str or "#0F172A").strip().lstrip("#")
    if len(clean) != 6:
        clean = "0F172A"
    return RGBColor(int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def apply_slide_background(slide, hex_color: str) -> None:
    """设置整页幻灯片纯色背景。"""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = rgb(hex_color)


def set_speaker_notes(slide, notes_text: str) -> None:
    """写入演讲者备注。"""
    if not notes_text:
        return
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = str(notes_text).strip()


def add_text_box(
    slide,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: float = 14.0,
    bold: bool = False,
    color_hex: str = "#0F172A",
    align: str = "left",
    font_name: str = "PingFang SC",
) -> object:
    """添加自动换行的无边框文本框。"""
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.name = font_name
    p.font.color.rgb = rgb(color_hex)
    if align == "center":
        p.alignment = PP_ALIGN.CENTER
    elif align == "right":
        p.alignment = PP_ALIGN.RIGHT
    else:
        p.alignment = PP_ALIGN.LEFT
    return box


def add_badge(
    slide,
    theme: dict,
    *,
    left: float,
    top: float,
    width: float = 2.6,
    height: float = 0.34,
    text: str = "CHAPTER 01",
    fill_hex: str | None = None,
    text_hex: str | None = None,
) -> object:
    """添加胶囊标签徽章。"""
    pill = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    pill.fill.solid()
    pill.fill.fore_color.rgb = rgb(fill_hex or theme.get("accent_soft", "#DBEAFE"))
    pill.line.fill.background()
    tf = pill.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = str(text)
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.name = theme.get("font_heading", "PingFang SC")
    p.font.color.rgb = rgb(text_hex or theme.get("accent_primary", "#2563EB"))
    return pill


def add_header_banner(
    slide,
    theme: dict,
    *,
    badge_text: str,
    title: str,
    subtitle: str = "",
    dark: bool = False,
) -> None:
    """绘制顶部章节胶囊、主标题与副标题区域 (y = 0.45" .. 1.68")。"""
    badge_fill = theme.get("surface_dark_card", "#1E293B") if dark else theme.get("accent_soft", "#DBEAFE")
    badge_fg = theme.get("accent_secondary", "#38BDF8") if dark else theme.get("accent_primary", "#2563EB")
    title_fg = theme.get("text_on_dark", "#F8FAFC") if dark else theme.get("text_primary", "#0F172A")
    sub_fg = "#94A3B8" if dark else theme.get("text_muted", "#475569")

    badge_w = max(2.2, min(4.2, 0.22 * len(badge_text) + 0.8))
    add_badge(
        slide,
        theme,
        left=0.65,
        top=0.45,
        width=badge_w,
        height=0.33,
        text=badge_text,
        fill_hex=badge_fill,
        text_hex=badge_fg,
    )
    add_text_box(
        slide,
        left=0.65,
        top=0.84,
        width=12.0,
        height=0.52,
        text=title,
        font_size=24,
        bold=True,
        color_hex=title_fg,
        font_name=theme.get("font_heading", "PingFang SC"),
    )
    if subtitle:
        add_text_box(
            slide,
            left=0.65,
            top=1.36,
            width=12.0,
            height=0.34,
            text=subtitle,
            font_size=13,
            bold=False,
            color_hex=sub_fg,
            font_name=theme.get("font_body", "PingFang SC"),
        )


def add_card(
    slide,
    theme: dict,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    body: str | list[str],
    badge: str = "",
    accent_bar: str = "left",
    dark: bool = False,
    fill_hex: str | None = None,
    accent_hex: str | None = None,
) -> object:
    """绘制带左/顶强调色条、可选编号徽章、标题与正文的卡片（单容器内排版，零重叠风险）。"""
    card_fill = fill_hex or (
        theme.get("surface_dark_card", "#1E293B") if dark else theme.get("surface_card", "#FFFFFF")
    )
    border_col = "#334155" if dark else theme.get("border_subtle", "#CBD5E1")
    title_col = theme.get("text_on_dark", "#F8FAFC") if dark else theme.get("text_primary", "#0F172A")
    body_col = "#CBD5E1" if dark else theme.get("text_muted", "#475569")
    acc_col = accent_hex or theme.get("accent_primary", "#2563EB")

    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    card.fill.solid()
    card.fill.fore_color.rgb = rgb(card_fill)
    card.line.color.rgb = rgb(border_col)
    card.line.width = Pt(1.0)

    if accent_bar == "left":
        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(left + 0.02),
            Inches(top + 0.14),
            Inches(0.07),
            Inches(max(0.3, height - 0.28)),
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = rgb(acc_col)
        bar.line.fill.background()
    elif accent_bar == "top":
        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(left + 0.16),
            Inches(top + 0.02),
            Inches(max(0.5, width - 0.32)),
            Inches(0.07),
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = rgb(acc_col)
        bar.line.fill.background()

    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.22 if accent_bar == "left" else 0.18)
    tf.margin_right = Inches(0.18)
    tf.margin_top = Inches(0.18 if accent_bar == "top" else 0.15)
    tf.margin_bottom = Inches(0.14)

    header_line = f"[{badge}]  {title}" if badge else title
    p0 = tf.paragraphs[0]
    p0.text = str(header_line)
    p0.font.size = Pt(16)
    p0.font.bold = True
    p0.font.name = theme.get("font_heading", "PingFang SC")
    p0.font.color.rgb = rgb(title_col)
    p0.space_after = Pt(6)

    lines = [body] if isinstance(body, str) else list(body)
    for item in lines:
        clean_item = str(item).strip()
        if not clean_item:
            continue
        p = tf.add_paragraph()
        p.text = f"• {clean_item}" if len(lines) > 1 and not clean_item.startswith("•") else clean_item
        p.font.size = Pt(13.5)
        p.font.bold = False
        p.font.name = theme.get("font_body", "PingFang SC")
        p.font.color.rgb = rgb(body_col)
        p.space_after = Pt(4)

    return card


def add_metric_stat(
    slide,
    theme: dict,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    value: str,
    label: str,
    detail: str = "",
    dark: bool = False,
    accent_hex: str | None = None,
) -> object:
    """绘制大字号关键指标/数字高亮卡（适用于对比、复杂度、实验结果等）。"""
    card_fill = theme.get("surface_dark_card", "#1E293B") if dark else theme.get("surface_card", "#FFFFFF")
    border_col = "#334155" if dark else theme.get("border_subtle", "#CBD5E1")
    val_col = accent_hex or (theme.get("accent_secondary", "#38BDF8") if dark else theme.get("accent_primary", "#2563EB"))
    label_col = theme.get("text_on_dark", "#F8FAFC") if dark else theme.get("text_primary", "#0F172A")
    detail_col = "#94A3B8" if dark else theme.get("text_muted", "#475569")

    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    box.fill.solid()
    box.fill.fore_color.rgb = rgb(card_fill)
    box.line.color.rgb = rgb(border_col)
    box.line.width = Pt(1.0)

    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.22)
    tf.margin_right = Inches(0.18)

    p0 = tf.paragraphs[0]
    p0.text = str(value)
    p0.font.size = Pt(28)
    p0.font.bold = True
    p0.font.name = theme.get("font_heading", "PingFang SC")
    p0.font.color.rgb = rgb(val_col)
    p0.space_after = Pt(4)

    p1 = tf.add_paragraph()
    p1.text = str(label)
    p1.font.size = Pt(14)
    p1.font.bold = True
    p1.font.name = theme.get("font_heading", "PingFang SC")
    p1.font.color.rgb = rgb(label_col)

    if detail:
        p2 = tf.add_paragraph()
        p2.text = str(detail)
        p2.font.size = Pt(12)
        p2.font.name = theme.get("font_body", "PingFang SC")
        p2.font.color.rgb = rgb(detail_col)

    return box


def add_code_panel(
    slide,
    theme: dict,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    code: str,
) -> object:
    """绘制深色代码/公式面板。"""
    panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = rgb("#0F172A")
    panel.line.color.rgb = rgb("#334155")
    panel.line.width = Pt(1.2)

    tf = panel.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.22)
    tf.margin_right = Inches(0.20)
    tf.margin_top = Inches(0.18)
    tf.margin_bottom = Inches(0.16)

    p0 = tf.paragraphs[0]
    p0.text = f"▍ {title}"
    p0.font.size = Pt(13.5)
    p0.font.bold = True
    p0.font.name = theme.get("font_heading", "PingFang SC")
    p0.font.color.rgb = rgb("#38BDF8")
    p0.space_after = Pt(8)

    for line in str(code).splitlines()[:14]:
        p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(12.5)
        p.font.name = theme.get("font_mono", "Consolas")
        p.font.color.rgb = rgb("#E2E8F0")
        p.space_after = Pt(2)

    return panel


def add_arrow_right(
    slide,
    theme: dict,
    *,
    left: float,
    top: float,
    width: float = 0.34,
    height: float = 0.34,
    color_hex: str | None = None,
) -> object:
    """绘制水平流程箭头。"""
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = rgb(color_hex or theme.get("accent_primary", "#2563EB"))
    arrow.line.fill.background()
    return arrow


def add_takeaway_bar(
    slide,
    theme: dict,
    *,
    label: str = "核心结论",
    text: str,
    slide_number: int = 0,
    total_slides: int = 0,
    dark: bool = False,
) -> object:
    """绘制底部一句话结论横幅 (y = 6.32", h = 0.56")。"""
    bar_fill = "#1E293B" if dark else theme.get("accent_soft", "#DBEAFE")
    bar_border = "#334155" if dark else theme.get("border_subtle", "#CBD5E1")
    text_col = "#F8FAFC" if dark else theme.get("text_primary", "#0F172A")

    bar = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.65),
        Inches(6.32),
        Inches(12.03),
        Inches(0.56),
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = rgb(bar_fill)
    bar.line.color.rgb = rgb(bar_border)
    bar.line.width = Pt(1.0)

    tf = bar.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.20)
    tf.margin_right = Inches(0.20)

    page_suffix = f"    [{slide_number:02d} / {total_slides:02d}]" if slide_number and total_slides else ""
    p = tf.paragraphs[0]
    p.text = f"★ {label}：{text}{page_suffix}"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.name = theme.get("font_body", "PingFang SC")
    p.font.color.rgb = rgb(text_col)
    return bar
