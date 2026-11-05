# `python-pptx` Cookbook & `ppt_helpers` Reference

Every slide file `slides/sXX.py` must expose a single entry function:

```python
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from ppt_helpers import (
    apply_slide_background,
    add_header_banner,
    add_card,
    add_text_box,
    add_badge,
    add_takeaway_bar,
    add_code_panel,
    add_arrow_right,
     set_speaker_notes,
)


def build_slide(prs, theme: dict) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    apply_slide_background(slide, theme["bg_light"])

    # 1. Header zone (y = 0.48" .. 1.55")
    add_header_banner(
        slide,
        theme,
        badge_text="CHAPTER 01 · 核心原理",
        title="为什么需要注意力机制：突破序列瓶颈",
        subtitle="对比 RNN 顺序依赖与 Self-Attention 全局并行关联",
    )

    # 2. Content zone (y = 1.75" .. 6.15")
    # Example: 3-column layout
    col_w = 3.78
    gap = 0.34
    start_x = 0.65
    items = [
        ("01", "长距离依赖衰减", "RNN 隐状态在长序列传递中梯度消失，难以保留首尾词元关联。"),
        ("02", "无法并行计算", "时间步 t 必须等待 t-1 完成，GPU 矩阵并发能力无法释放。"),
        ("03", "全局直接建模", "Attention 通过 Q·K^T 一次性计算任意两位置相关性，路径长度为 O(1)。"),
    ]
    for idx, (num, heading, body) in enumerate(items):
        x = start_x + idx * (col_w + gap)
        add_card(
            slide,
            theme,
            left=x,
            top=1.85,
            width=col_w,
            height=4.15,
            title=heading,
            body=body,
            badge=num,
            accent_bar="top",
        )

    # 3. Bottom takeaway bar (y = 6.32" .. 6.90")
    add_takeaway_bar(
        slide,
        theme,
        label="核心结论",
        text="Self-Attention 将任意两个 Token 的交互距离缩短为常数 O(1)，同时解锁训练阶段的序列并行。",
        slide_number=3,
        total_slides=8,
    )

    # 4. Speaker notes
    set_speaker_notes(
        slide,
        "本页重点讲解传统循环神经网络的两大痛点，以及自注意力机制如何通过矩阵内积实现全局一步直达。",
    )
```

## Built-in `ppt_helpers.py` Functions Available in Workspace

When `init_deck_plan` initializes the workspace, it automatically generates `ppt_helpers.py` with these battle-tested helpers:

1. `apply_slide_background(slide, hex_color: str)`
   - Fills the slide background with `hex_color` (e.g. `theme["bg_light"]` or `theme["bg_dark"]`).
2. `add_header_banner(slide, theme: dict, *, badge_text: str, title: str, subtitle: str = "", dark: bool = False)`
   - Draws the top-left pill badge, main slide title (`25pt` Bold), and optional subtitle (`13pt`) inside `y = 0.45" .. 1.65"`.
3. `add_card(slide, theme: dict, *, left: float, top: float, width: float, height: float, title: str, body: str | list[str], badge: str = "", accent_bar: str = "left", dark: bool = False, fill_hex: str | None = None, accent_hex: str | None = None)`
   - Draws a rounded rectangle card with subtle border, optional accent bar (`"left"`, `"top"`, or `"none"`), optional number/tag badge, bold card title (`16pt`), and wrapped body text or bullet list (`13.5pt`).
   - All coordinates (`left`, `top`, `width`, `height`) are in **inches** (`float`).
4. `add_code_panel(slide, theme: dict, *, left: float, top: float, width: float, height: float, title: str, code: str)`
   - Draws a dark terminal-style card (`#0F172A`) with a header bar and monospace (`Consolas`, `12.5pt`) code/formula text.
5. `add_takeaway_bar(slide, theme: dict, *, label: str, text: str, slide_number: int = 0, total_slides: int = 0, dark: bool = False)`
   - Draws the bottom takeaway banner at `y = 6.32"`, `h = 0.56"`, plus optional slide counter `03 / 08`.
6. `add_arrow_right(slide, theme: dict, *, left: float, top: float, width: float = 0.36, height: float = 0.36, color_hex: str | None = None)`
   - Draws a right arrow connector between process cards.
7. `add_text_box(slide, *, left: float, top: float, width: float, height: float, text: str, font_size: float = 14, bold: bool = False, color_hex: str = "#1E293B", align: str = "left", font_name: str = "PingFang SC")`
   - Adds a non-overlapping text box with `word_wrap = True` and clean margins.
8. `set_speaker_notes(slide, notes_text: str)`
   - Writes speaker notes into `slide.notes_slide.notes_text_frame`.

## Common Pitfalls to Avoid

- **Never forget `word_wrap = True`** when creating custom text frames.
- **Never exceed `x + width > 12.75` or `y + height > 7.05`**.
- **Never put more than 4 lines of text inside a small card (`height < 1.8"`)** — keep card copy concise and structured!
- **Never use `RGBColor` with `#` prefix** — `ppt_helpers.rgb("#1E293B")` handles `#` stripping automatically.
