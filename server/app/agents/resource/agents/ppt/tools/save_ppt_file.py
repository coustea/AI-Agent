"""Enhanced PPT generation tool with rich content support.

Supported Markdown extensions:
  - ## Title        → slide title
  - - bullet        → bullet points
  - 1. numbered     → numbered steps (rendered as step cards)
  - > callout       → highlighted callout box
  - | table |       → data table
  - [note] ... [/note] → speaker notes (not visible on slide)
"""

import json
import re
import time
from pathlib import Path
from dataclasses import dataclass, field

from langchain.tools import tool
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

from app.utils.paths import WORKPLACE_DIR

# ---------------------------------------------------------------------------
# Markdown parsing regexes
# ---------------------------------------------------------------------------
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_SLIDE_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[\t ]*-[\t ]+(.+)$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^[\t ]*(\d+)\.\s+(.+)$", re.MULTILINE)
_CALLOUT_RE = re.compile(r"^>\s*(.+)$", re.MULTILINE)
_NOTE_OPEN_RE = re.compile(r"^\[note\]\s*$", re.MULTILINE)
_NOTE_CLOSE_RE = re.compile(r"^\[/note\]\s*$", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\|?[\s\-:|]+\|?$")

# ---------------------------------------------------------------------------
# Parsed Slide Content
# ---------------------------------------------------------------------------

@dataclass
class SlideContent:
    """Parsed content for a single slide."""
    title: str = ""
    bullets: list[str] = field(default_factory=list)
    numbered_steps: list[str] = field(default_factory=list)
    callouts: list[str] = field(default_factory=list)
    table_rows: list[list[str]] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Color Themes (derived from ppt-visual skill)
# ---------------------------------------------------------------------------
THEMES: dict[str, dict] = {
    "corporate_blue": {
        "primary": RGBColor(0x1E, 0x3A, 0x5F),
        "secondary": RGBColor(0x34, 0x98, 0xDB),
        "accent": RGBColor(0xE7, 0x4C, 0x3C),
        "background": RGBColor(0xF5, 0xF7, 0xFA),
        "text": RGBColor(0x2C, 0x3E, 0x50),
        "title_font": "Arial",
        "body_font": "Arial",
    },
    "modern_minimal": {
        "primary": RGBColor(0x1A, 0x1A, 0x1A),
        "secondary": RGBColor(0x66, 0x66, 0x66),
        "accent": RGBColor(0xFF, 0x6B, 0x6B),
        "background": RGBColor(0xFF, 0xFF, 0xFF),
        "text": RGBColor(0x33, 0x33, 0x33),
        "title_font": "Arial",
        "body_font": "Arial",
    },
    "creative_bold": {
        "primary": RGBColor(0x6C, 0x5C, 0xE7),
        "secondary": RGBColor(0x00, 0xCE, 0xC9),
        "accent": RGBColor(0xFD, 0xCB, 0x6E),
        "background": RGBColor(0x2D, 0x34, 0x36),
        "text": RGBColor(0xFF, 0xFF, 0xFF),
        "title_font": "Arial",
        "body_font": "Arial",
    },
    "nature_green": {
        "primary": RGBColor(0x27, 0xAE, 0x60),
        "secondary": RGBColor(0x2E, 0xCC, 0x71),
        "accent": RGBColor(0xF3, 0x9C, 0x12),
        "background": RGBColor(0xFD, 0xFE, 0xFE),
        "text": RGBColor(0x2C, 0x3E, 0x50),
        "title_font": "Arial",
        "body_font": "Arial",
    },
}

_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_SUMMARY_KEYWORDS = {"总结", "归纳", "回顾", "摘要", "summary", "q&a", "延伸", "问答", "思考"}
_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)


def _safe_filename(topic: str) -> str:
    safe = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    return safe or "untitled"


def _split_sections(outline_markdown: str) -> list[tuple[str, str]]:
    matches = list(_SLIDE_RE.finditer(outline_markdown))
    if not matches:
        return [("内容概览", outline_markdown.strip())]
    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(outline_markdown)
        sections.append((match.group(1).strip(), outline_markdown[start:end].strip()))
    return sections


def _parse_section_body(body: str) -> SlideContent:
    """Parse a section body into structured SlideContent."""
    content = SlideContent()

    # Extract speaker notes [note]...[/note]
    note_ranges: list[tuple[int, int]] = []
    for m in _NOTE_OPEN_RE.finditer(body):
        start = m.end()
        close = _NOTE_CLOSE_RE.search(body, start)
        if close:
            note_ranges.append((m.start(), close.end()))
            content.notes += body[start:close.start()].strip() + "\n"
    # Remove notes from body
    for start, end in reversed(note_ranges):
        body = body[:start] + body[end:]

    # Extract callouts (> text)
    content.callouts = [m.group(1).strip() for m in _CALLOUT_RE.finditer(body)]

    # Extract table rows
    lines = body.splitlines()
    table_lines: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not _TABLE_SEP_RE.match(stripped):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                table_lines.append(cells)
                in_table = True
        else:
            if in_table:
                break
    content.table_rows = table_lines

    # Extract numbered steps
    content.numbered_steps = [m.group(2).strip() for m in _NUMBERED_RE.finditer(body)]

    # Extract bullets
    content.bullets = [m.group(1).strip() for m in _BULLET_RE.finditer(body)]

    return content


def _classify_slide(title: str, content: SlideContent) -> str:
    title_lower = title.lower()
    if any(kw in title_lower for kw in _SUMMARY_KEYWORDS):
        return "summary"
    has_content = content.bullets or content.table_rows or content.numbered_steps or content.callouts
    if not has_content:
        return "section"
    return "content"


def _lighten(color: RGBColor, factor: float) -> RGBColor:
    r = int(color[0] + (255 - color[0]) * factor)
    g = int(color[1] + (255 - color[1]) * factor)
    b = int(color[2] + (255 - color[2]) * factor)
    return RGBColor(min(r, 255), min(g, 255), min(b, 255))


def _darken(color: RGBColor, factor: float) -> RGBColor:
    r = int(color[0] * (1 - factor))
    g = int(color[1] * (1 - factor))
    b = int(color[2] * (1 - factor))
    return RGBColor(max(r, 0), max(g, 0), max(b, 0))


def _no_border(shape) -> None:
    shape.line.fill.background()


def _set_bg_solid(slide, color: RGBColor) -> None:
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = color


def _set_bg_gradient(slide, color1: RGBColor, color2: RGBColor) -> None:
    bg = slide.background.fill
    bg.gradient()
    bg.gradient_stops[0].color.rgb = color1
    bg.gradient_stops[0].position = 0.0
    bg.gradient_stops[1].color.rgb = color2
    bg.gradient_stops[1].position = 1.0


def _add_speaker_notes(slide, notes: str) -> None:
    """Add speaker notes to a slide."""
    if not notes.strip():
        return
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = notes.strip()


# ---------------------------------------------------------------------------
# Reusable slide frame (left stripe + title + divider)
# ---------------------------------------------------------------------------

def _add_slide_frame(slide, title: str, theme: dict) -> None:
    """Add the common chrome: background, left stripe, title bar, divider."""
    _set_bg_solid(slide, theme["background"])

    # Left accent stripe
    stripe = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), _SLIDE_H
    )
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = theme["secondary"]
    _no_border(stripe)

    # Title
    title_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.5), Inches(11.5), Inches(1.0))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = theme["primary"]
    p.font.name = theme["title_font"]

    # Divider line
    div = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(1.55), Inches(11.5), Pt(2)
    )
    div.fill.solid()
    div.fill.fore_color.rgb = theme["secondary"]
    _no_border(div)


# ---------------------------------------------------------------------------
# Content element builders (for use inside content slides)
# ---------------------------------------------------------------------------

def _add_bullet_block(slide, bullets: list[str], theme: dict,
                      left: float = 1.2, top: float = 2.0,
                      width: float = 11.0, height: float = 4.8) -> float:
    """Add bullet text block. Returns the Y position after the block."""
    body_box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = body_box.text_frame
    tf.word_wrap = True

    font_size = Pt(22) if len(bullets) <= 3 else Pt(18)

    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {bullet}"
        p.font.size = font_size
        p.font.color.rgb = theme["text"]
        p.font.name = theme["body_font"]
        p.space_after = Pt(10)

    return top + min(len(bullets) * 0.6, height)


def _add_callout_box(slide, text: str, theme: dict,
                     left: float = 1.2, top: float = 2.0,
                     width: float = 11.0) -> float:
    """Add a highlighted callout box. Returns the Y position after the box."""
    box_h = 1.2
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(box_h)
    )
    box.fill.solid()
    box.fill.fore_color.rgb = _lighten(theme["accent"], 0.88)
    box.line.color.rgb = theme["accent"]
    box.line.width = Pt(2)

    tf = box.text_frame
    tf.word_wrap = True
    # Add left padding via indent
    p = tf.paragraphs[0]
    p.text = f"💡 {text}"
    p.font.size = Pt(16)
    p.font.color.rgb = _darken(theme["accent"], 0.2)
    p.font.name = theme["body_font"]
    p.font.italic = True
    p.alignment = PP_ALIGN.LEFT

    return top + box_h + 0.2


def _add_table(slide, rows: list[list[str]], theme: dict,
               left: float = 1.2, top: float = 2.0,
               width: float = 11.0) -> float:
    """Add a styled table. Returns Y position after the table."""
    if not rows:
        return top

    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)
    row_h = Inches(0.5)
    table_h = n_rows * 0.5

    table_shape = slide.shapes.add_table(
        n_rows, n_cols,
        Inches(left), Inches(top), Inches(width), Inches(table_h)
    )
    table = table_shape.table

    # Style the table
    for r_idx, row_data in enumerate(rows):
        for c_idx in range(n_cols):
            cell = table.cell(r_idx, c_idx)
            cell.text = row_data[c_idx] if c_idx < len(row_data) else ""

            # Style cell
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(14)
                paragraph.font.name = theme["body_font"]
                if r_idx == 0:
                    # Header row
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = _WHITE
                    paragraph.font.size = Pt(15)
                else:
                    paragraph.font.color.rgb = theme["text"]
                paragraph.alignment = PP_ALIGN.CENTER

            # Cell fill
            cell_fill = cell.fill
            cell_fill.solid()
            if r_idx == 0:
                cell_fill.fore_color.rgb = theme["primary"]
            elif r_idx % 2 == 0:
                cell_fill.fore_color.rgb = _lighten(theme["secondary"], 0.9)
            else:
                cell_fill.fore_color.rgb = _WHITE

    return top + table_h + 0.2


def _add_step_cards(slide, steps: list[str], theme: dict,
                    left: float = 1.2, top: float = 2.0) -> float:
    """Add numbered step cards laid out horizontally. Returns Y after cards."""
    n = len(steps)
    if n == 0:
        return top

    # Calculate card dimensions in inches
    gap_in = 0.4
    total_gap_in = gap_in * (n - 1)
    card_w_in = (11.0 - total_gap_in) / n
    card_h_in = 3.8

    for i, step_text in enumerate(steps):
        x = left + i * (card_w_in + 0.4)
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(top), Inches(card_w_in), Inches(card_h_in)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = _WHITE
        card.line.color.rgb = theme["secondary"]
        card.line.width = Pt(1.5)

        tf = card.text_frame
        tf.word_wrap = True

        # Step number circle (as bold number text)
        p_num = tf.paragraphs[0]
        p_num.text = f"Step {i + 1}"
        p_num.font.size = Pt(13)
        p_num.font.bold = True
        p_num.font.color.rgb = theme["secondary"]
        p_num.font.name = theme["body_font"]
        p_num.alignment = PP_ALIGN.LEFT
        p_num.space_after = Pt(6)

        # Step text
        p_text = tf.add_paragraph()
        p_text.text = step_text
        p_text.font.size = Pt(16)
        p_text.font.color.rgb = theme["text"]
        p_text.font.name = theme["body_font"]
        p_text.alignment = PP_ALIGN.LEFT
        p_text.space_before = Pt(4)

    return top + card_h_in + 0.3


def _add_three_column_cards(slide, items: list[str], theme: dict,
                            left: float = 1.2, top: float = 2.0) -> float:
    """Add three-column card layout. Returns Y after cards."""
    n = len(items)
    if n == 0:
        return top

    gap = 0.5
    card_w = (11.0 - gap * (n - 1)) / n
    card_h = 3.8

    for i, text in enumerate(items):
        x = left + i * (card_w + gap)
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(top), Inches(card_w), Inches(card_h)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = _lighten(theme["secondary"], 0.82)
        card.line.color.rgb = theme["secondary"]
        card.line.width = Pt(1)

        tf = card.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(18)
        p.font.color.rgb = theme["text"]
        p.font.name = theme["body_font"]
        p.alignment = PP_ALIGN.CENTER
        p.space_before = Pt(50)

    return top + card_h + 0.3


# ---------------------------------------------------------------------------
# Slide Builders
# ---------------------------------------------------------------------------

def _build_cover_slide(prs: Presentation, title: str, subtitle: str, theme: dict) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    _set_bg_solid(slide, theme["primary"])

    # Bottom accent bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(6.4), _SLIDE_W, Inches(1.1)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = theme["secondary"]
    _no_border(bar)

    # Accent line above bar
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(6.15), _SLIDE_W, Pt(4)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = theme["accent"]
    _no_border(line)

    # Title
    title_box = slide.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.9), Inches(2.8))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = _WHITE
    p.font.name = theme["title_font"]

    # Subtitle
    sub_box = slide.shapes.add_textbox(Inches(1.2), Inches(4.3), Inches(10.9), Inches(1.0))
    tf2 = sub_box.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(20)
    p2.font.color.rgb = _LIGHT_GRAY
    p2.font.name = theme["body_font"]


def _build_toc_slide(prs: Presentation, titles: list[str], theme: dict) -> None:
    """Build a table-of-contents slide with section list."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    _set_bg_solid(slide, theme["background"])

    # Left stripe
    stripe = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), _SLIDE_H
    )
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = theme["secondary"]
    _no_border(stripe)

    # Title
    title_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.5), Inches(11.5), Inches(1.0))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "目录"
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = theme["primary"]
    p.font.name = theme["title_font"]

    # Divider
    div = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(1.55), Inches(11.5), Pt(2)
    )
    div.fill.solid()
    div.fill.fore_color.rgb = theme["secondary"]
    _no_border(div)

    # Section list with numbering
    body_box = slide.shapes.add_textbox(Inches(1.5), Inches(2.0), Inches(10.0), Inches(5.0))
    tf2 = body_box.text_frame
    tf2.word_wrap = True

    for i, title in enumerate(titles):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        p.text = f"{i + 1}.   {title}"
        p.font.size = Pt(20)
        p.font.color.rgb = theme["text"]
        p.font.name = theme["body_font"]
        p.space_after = Pt(10)


def _build_section_slide(prs: Presentation, title: str, theme: dict) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg_solid(slide, theme["primary"])

    title_box = slide.shapes.add_textbox(Inches(2), Inches(2.5), Inches(9.3), Inches(2.5))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = _WHITE
    p.font.name = theme["title_font"]
    p.alignment = PP_ALIGN.CENTER

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(4.7), Inches(5.0), Inches(4.0), Pt(4)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = theme["accent"]
    _no_border(bar)


def _build_content_slide(prs: Presentation, title: str, content: SlideContent, theme: dict) -> None:
    """Build a content slide with rich layout based on available content."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_slide_frame(slide, title, theme)

    y = 1.9  # starting Y for content area

    # Priority: table > numbered steps > bullets with callouts > bullets
    if content.table_rows:
        y = _add_table(slide, content.table_rows, theme, top=y)
        if content.callouts:
            for co in content.callouts:
                y = _add_callout_box(slide, co, theme, top=y)

    elif content.numbered_steps:
        y = _add_step_cards(slide, content.numbered_steps, theme, top=y)
        if content.callouts:
            for co in content.callouts:
                y = _add_callout_box(slide, co, theme, top=y)

    elif content.bullets and len(content.bullets) == 3 and not content.callouts and not content.table_rows:
        # 3-bullet card layout
        y = _add_three_column_cards(slide, content.bullets, theme, top=y)

    else:
        # Standard layout: bullets + callouts
        if content.bullets:
            y = _add_bullet_block(slide, content.bullets, theme, top=y)
        if content.callouts:
            for co in content.callouts:
                y = _add_callout_box(slide, co, theme, top=y)

    # Speaker notes
    _add_speaker_notes(slide, content.notes)


def _build_summary_slide(prs: Presentation, title: str, content: SlideContent, theme: dict) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg_gradient(slide, theme["primary"], theme["secondary"])

    # Title
    title_box = slide.shapes.add_textbox(Inches(1.2), Inches(0.6), Inches(10.9), Inches(1.2))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(34)
    p.font.bold = True
    p.font.color.rgb = _WHITE
    p.font.name = theme["title_font"]

    # Content
    y = 2.0
    if content.bullets:
        body_box = slide.shapes.add_textbox(Inches(1.5), Inches(y), Inches(10.3), Inches(4.5))
        tf2 = body_box.text_frame
        tf2.word_wrap = True
        for i, bullet in enumerate(content.bullets):
            p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
            p.text = f"✓  {bullet}"
            p.font.size = Pt(20)
            p.font.color.rgb = _WHITE
            p.font.name = theme["body_font"]
            p.space_after = Pt(8)

    if content.callouts:
        for co in content.callouts:
            # Light callout on dark bg
            box = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(1.5), Inches(5.2), Inches(10.3), Inches(1.0)
            )
            box.fill.solid()
            box.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            box.line.fill.background()
            tf3 = box.text_frame
            tf3.word_wrap = True
            p3 = tf3.paragraphs[0]
            p3.text = f"💡 {co}"
            p3.font.size = Pt(15)
            p3.font.color.rgb = theme["primary"]
            p3.font.italic = True

    _add_speaker_notes(slide, content.notes)


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@tool("save_ppt_file")
def save_ppt_file(topic: str, outline_markdown: str, file_path: str | None = None, style: str = "corporate_blue") -> str:
    """将 Markdown 大纲保存为带视觉样式的 PPTX 文件。

    支持的 Markdown 扩展：
    - ## 标题 → 幻灯片标题
    - - 要点 → 项目符号
    - 1. 步骤 → 编号步骤卡片
    - > 文字 → 高亮提示框
    - | 表头 | 表头 | → 数据表格
    - [note] 讲者备注 [/note] → 讲者备注（不在幻灯片上显示）

    style 参数选择主题：corporate_blue（默认）, modern_minimal, creative_bold, nature_green。
    """
    theme = THEMES.get(style, THEMES["corporate_blue"])

    # Parse markdown
    title_match = _TITLE_RE.search(outline_markdown)
    presentation_title = title_match.group(1).strip() if title_match else topic
    sections = _split_sections(outline_markdown)

    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H

    # Parse all sections first (to build TOC and detect types)
    parsed: list[tuple[str, SlideContent, str]] = []
    section_titles: list[str] = []
    for title, body in sections:
        content = _parse_section_body(body)
        slide_type = _classify_slide(title, content)
        parsed.append((title, content, slide_type))
        if slide_type != "section":
            section_titles.append(title)

    # Cover slide
    _build_cover_slide(prs, presentation_title, f"{topic} · 教学演示文稿", theme)
    slide_titles = [presentation_title]

    # TOC slide (if we have enough sections)
    if len(section_titles) >= 3:
        _build_toc_slide(prs, section_titles, theme)
        slide_titles.append("目录")

    # Content slides
    for title, content, slide_type in parsed:
        if slide_type == "section":
            _build_section_slide(prs, title, theme)
        elif slide_type == "summary":
            _build_summary_slide(prs, title, content, theme)
        else:
            _build_content_slide(prs, title, content, theme)
        slide_titles.append(title)

    # Save
    if file_path:
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = WORKPLACE_DIR / "ppt"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{_safe_filename(topic)}_{int(time.time())}.pptx"

    prs.save(str(target))

    return json.dumps(
        {
            "file_path": str(target),
            "slide_count": len(prs.slides),
            "slide_titles": slide_titles,
        },
        ensure_ascii=False,
    )
