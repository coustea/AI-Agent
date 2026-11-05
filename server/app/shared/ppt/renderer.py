"""PPTX 渲染与交互式预览发布器（零内嵌 HTML 字符串）。

负责：
1. 将 ``deck.pptx`` 的每一页通过 Pillow 渲染为 ``thumbnails/slide_01.png .. slide_NN.png`` (1600×900)。
2. 拼接带编号标签的缩略图网格 ``thumbnails/grid.png``，供 ``view_image`` 视觉模型审查。
3. 从 ``server/skills/pptx/templates/viewer.html`` 读取物理播放器模板并注入幻灯片数据，生成 ``slides.html``。
"""

from __future__ import annotations

import base64
import html
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

from app.shared.tools.skills import get_skill_loader

EMU_PER_INCH = 914_400
SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.500
CANVAS_W = 1600
CANVAS_H = 900

_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def _load_font(px_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=max(10, int(px_size)))
            except Exception:
                continue
    return ImageFont.load_default()


def _rgb_tuple(color_obj: Any, default: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        rgb = color_obj.rgb
        if rgb is not None:
            return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception:
        pass
    return default


def _wrap_text_lines(text: str, font: Any, max_w_px: int, draw: ImageDraw.ImageDraw) -> list[str]:
    lines: list[str] = []
    for raw_para in text.splitlines() or [text]:
        para = raw_para.strip()
        if not para:
            continue
        current = ""
        for ch in para:
            candidate = current + ch
            bbox = draw.textbbox((0, 0), candidate, font=font)
            w = bbox[2] - bbox[0]
            if w > max_w_px and current:
                lines.append(current)
                current = ch
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def render_pptx_thumbnails(pptx_path: Path, output_dir: Path) -> list[Path]:
    """将 deck.pptx 的每一页渲染为高清 PNG 缩略图 (thumbnails/slide_01.png ...)。"""
    thumbs_dir = output_dir / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    prs = Presentation(str(pptx_path))
    scale_x = CANVAS_W / SLIDE_W_IN
    scale_y = CANVAS_H / SLIDE_H_IN
    out_paths: list[Path] = []

    for idx, slide in enumerate(prs.slides, start=1):
        bg_rgb = (248, 250, 252)
        try:
            if slide.background and slide.background.fill:
                bg_rgb = _rgb_tuple(slide.background.fill.fore_color, bg_rgb)
        except Exception:
            pass

        img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg_rgb)
        draw = ImageDraw.Draw(img)

        for shape in slide.shapes:
            left_in = float(getattr(shape, "left", 0) or 0) / EMU_PER_INCH
            top_in = float(getattr(shape, "top", 0) or 0) / EMU_PER_INCH
            w_in = float(getattr(shape, "width", 0) or 0) / EMU_PER_INCH
            h_in = float(getattr(shape, "height", 0) or 0) / EMU_PER_INCH

            x1 = int(left_in * scale_x)
            y1 = int(top_in * scale_y)
            x2 = int((left_in + w_in) * scale_x)
            y2 = int((top_in + h_in) * scale_y)
            if x2 <= x1 or y2 <= y1:
                continue

            fill_rgb: tuple[int, int, int] | None = None
            try:
                if hasattr(shape, "fill") and shape.fill.type is not None:
                    fill_rgb = _rgb_tuple(shape.fill.fore_color, (255, 255, 255))
            except Exception:
                fill_rgb = None

            line_rgb: tuple[int, int, int] | None = None
            try:
                if hasattr(shape, "line") and shape.line and shape.line.fill.type is not None:
                    line_rgb = _rgb_tuple(shape.line.color, (203, 213, 225))
            except Exception:
                line_rgb = None

            if fill_rgb is not None or line_rgb is not None:
                radius = 14 if min(x2 - x1, y2 - y1) > 40 else 4
                draw.rounded_rectangle(
                    (x1, y1, x2, y2),
                    radius=radius,
                    fill=fill_rgb,
                    outline=line_rgb,
                    width=2 if line_rgb else 0,
                )

            if getattr(shape, "has_text_frame", False):
                tf = shape.text_frame
                pad_x = int(0.18 * scale_x) if fill_rgb is not None else int(0.04 * scale_x)
                pad_y = int(0.14 * scale_y) if fill_rgb is not None else int(0.02 * scale_y)
                cursor_y = y1 + pad_y
                max_text_w = max(40, (x2 - x1) - pad_x * 2)

                for p_idx, para in enumerate(tf.paragraphs):
                    p_text = (para.text or "").strip()
                    if not p_text:
                        continue
                    pt_size = 14.0
                    if para.font and para.font.size:
                        pt_size = float(para.font.size.pt)
                    elif para.runs and para.runs[0].font and para.runs[0].font.size:
                        pt_size = float(para.runs[0].font.size.pt)

                    default_fg = (248, 250, 252) if sum(bg_rgb) < 300 else (15, 23, 42)
                    if fill_rgb is not None:
                        default_fg = (248, 250, 252) if sum(fill_rgb) < 300 else (15, 23, 42)
                    fg_rgb = default_fg
                    if para.font and para.font.color:
                        fg_rgb = _rgb_tuple(para.font.color, default_fg)
                    elif para.runs and para.runs[0].font and para.runs[0].font.color:
                        fg_rgb = _rgb_tuple(para.runs[0].font.color, default_fg)

                    px_font_size = max(13, int(pt_size * (CANVAS_H / 540.0)))
                    font = _load_font(px_font_size)
                    wrapped = _wrap_text_lines(p_text, font, max_text_w, draw)
                    line_step = int(px_font_size * 1.38)
                    for line_str in wrapped:
                        if cursor_y + px_font_size > y2 + 8:
                            break
                        draw.text((x1 + pad_x, cursor_y), line_str, font=font, fill=fg_rgb)
                        cursor_y += line_step
                    cursor_y += 6 if p_idx == 0 else 3

        slide_png = thumbs_dir / f"slide_{idx:02d}.png"
        img.save(slide_png, format="PNG")
        out_paths.append(slide_png)

    return out_paths


def build_thumbnail_grid(slide_pngs: list[Path], grid_path: Path) -> Path:
    """将所有幻灯片 PNG 拼接为带编号标签的联系表 (thumbnails/grid.png)。"""
    grid_path.parent.mkdir(parents=True, exist_ok=True)
    if not slide_pngs:
        empty = Image.new("RGB", (640, 360), (15, 23, 42))
        empty.save(grid_path, format="PNG")
        return grid_path

    cols = 3 if len(slide_pngs) >= 5 else 2
    rows = math.ceil(len(slide_pngs) / cols)
    cell_w, cell_h = 520, 292
    label_h = 28
    pad = 18

    total_w = pad + cols * (cell_w + pad)
    total_h = pad + rows * (cell_h + label_h + pad)
    sheet = Image.new("RGB", (total_w, total_h), (15, 23, 42))
    draw = ImageDraw.Draw(sheet)
    label_font = _load_font(16)

    for idx, png_path in enumerate(slide_pngs):
        r = idx // cols
        c = idx % cols
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)

        draw.text((x + 4, y + 2), f"s{idx + 1:02d} ({png_path.name})", font=label_font, fill=(226, 232, 240))
        with Image.open(png_path) as thumb:
            resized = thumb.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            sheet.paste(resized, (x, y + label_h))
        draw.rectangle(
            (x, y + label_h, x + cell_w, y + label_h + cell_h),
            outline=(71, 85, 105),
            width=2,
        )

    sheet.save(grid_path, format="PNG")
    return grid_path


def publish_viewer_html(
    pptx_path: Path,
    slide_pngs: list[Path],
    output_dir: Path,
    *,
    title: str,
) -> Path:
    """从 skills/pptx/templates/viewer.html 读取物理模板，注入幻灯片数据并生成 slides.html。"""
    prs = Presentation(str(pptx_path))
    slides_payload: list[dict[str, Any]] = []

    for idx, slide in enumerate(prs.slides, start=1):
        notes = ""
        try:
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = (slide.notes_slide.notes_text_frame.text or "").strip()
        except Exception:
            notes = ""

        data_uri = ""
        if idx - 1 < len(slide_pngs) and slide_pngs[idx - 1].is_file():
            raw_b64 = base64.b64encode(slide_pngs[idx - 1].read_bytes()).decode("ascii")
            data_uri = f"data:image/png;base64,{raw_b64}"

        slides_payload.append(
            {
                "index": idx,
                "image": data_uri,
                "notes": notes,
            }
        )

    slides_json = json.dumps(slides_payload, ensure_ascii=False)
    escaped_title = html.escape(title)

    loader = get_skill_loader()
    slides_html_path = output_dir / "slides.html"
    loader.copy_template(
        "pptx",
        "viewer.html",
        slides_html_path,
        replacements={
            "__DECK_TITLE__": escaped_title,
            "__SLIDES_JSON__": slides_json,
        },
    )
    (output_dir / "index.html").write_text(
        slides_html_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return slides_html_path


__all__ = [
    "build_thumbnail_grid",
    "publish_viewer_html",
    "render_pptx_thumbnails",
]
