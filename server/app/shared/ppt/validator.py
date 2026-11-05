"""OOXML (.pptx) 确定性几何与排版审计器。

无需打开图形界面，直接解析 python-pptx 生成的 OOXML 对象树，检测：
1. 越界检查 (Out-of-Bounds): 形状超出 13.333" × 7.5" 画布边界
2. 文本框重叠检查 (Text-Bearing AABB Collision): 两个含文字的形状发生非包含式重叠
3. 文本溢出估算 (Text Capacity Overflow): 形状高度不足以容纳其内部文字行数
4. 最小字号检查 (Font Size Legibility): 字体小于 10pt
5. 空白页检查 (Slide Content Density): 页面文字过少或无结构化形状
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from pptx import Presentation

EMU_PER_INCH = 914_400
SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.500


def _to_inches(emu: int | float | None) -> float:
    if emu is None:
        return 0.0
    return float(emu) / EMU_PER_INCH


def _rect_intersection_area(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return (ix2 - ix1) * (iy2 - iy1)


def _contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
    tol: float = 0.06,
) -> bool:
    return (
        outer[0] - tol <= inner[0]
        and outer[1] - tol <= inner[1]
        and outer[2] + tol >= inner[2]
        and outer[3] + tol >= inner[3]
    )


def audit_single_slide(slide: Any, slide_index: int) -> list[str]:
    """对单页 Slide 执行确定性几何与排版审计，返回问题列表（空列表表示通过）。"""
    errors: list[str] = []
    tag = f"Slide s{slide_index:02d}"

    text_boxes: list[tuple[str, tuple[float, float, float, float]]] = []
    total_chars = 0
    shape_count = 0

    for idx, shape in enumerate(slide.shapes):
        shape_count += 1
        left = _to_inches(getattr(shape, "left", 0))
        top = _to_inches(getattr(shape, "top", 0))
        width = _to_inches(getattr(shape, "width", 0))
        height = _to_inches(getattr(shape, "height", 0))
        right = left + width
        bottom = top + height
        s_name = getattr(shape, "name", f"shape_{idx}")

        # 1. 画布越界检查
        if left < -0.10 or top < -0.10 or right > SLIDE_W_IN + 0.12 or bottom > SLIDE_H_IN + 0.12:
            errors.append(
                f"{tag}: Shape '{s_name}' out of 13.33x7.5 canvas bounds "
                f"(left={left:.2f}\", top={top:.2f}\", right={right:.2f}\", bottom={bottom:.2f}\")"
            )

        if not getattr(shape, "has_text_frame", False):
            continue

        tf = shape.text_frame
        text = (tf.text or "").strip()
        if not text:
            continue

        total_chars += len(text)
        box_rect = (left, top, right, bottom)
        text_boxes.append((f"{s_name}({text[:14]!r})", box_rect))

        # 2. 字号与行数溢出估算
        max_font_pt = 14.0
        for para in tf.paragraphs:
            p_size = para.font.size.pt if para.font and para.font.size else None
            if p_size is not None:
                max_font_pt = max(max_font_pt, float(p_size))
                if p_size < 9.5:
                    errors.append(
                        f"{tag}: Font size {p_size:.1f}pt in '{s_name}' is too small (< 10pt)"
                    )
            for run in para.runs:
                r_size = run.font.size.pt if run.font and run.font.size else None
                if r_size is not None:
                    max_font_pt = max(max_font_pt, float(r_size))
                    if r_size < 9.5:
                        errors.append(
                            f"{tag}: Run font size {r_size:.1f}pt in '{s_name}' is too small (< 10pt)"
                        )

        # 估算文本框可容纳行数与实际所需行数
        usable_w_pt = max(36.0, (width - 0.25) * 72.0)
        chars_per_line = max(4.0, usable_w_pt / (max_font_pt * 0.92))
        est_lines = 0
        for raw_line in text.splitlines() or [text]:
            est_lines += max(1, math.ceil(len(raw_line.strip()) / chars_per_line))
        line_h_in = (max_font_pt * 1.38) / 72.0
        required_h_in = est_lines * line_h_in
        if height > 0.45 and required_h_in > height * 1.45 and est_lines >= 4:
            errors.append(
                f"{tag}: Text overflow risk in '{s_name}' ({text[:18]!r}): "
                f"estimated {est_lines} lines (~{required_h_in:.2f}\") inside height={height:.2f}\""
            )

    # 3. 含文字形状之间的重叠碰撞检查
    for i in range(len(text_boxes)):
        name_a, rect_a = text_boxes[i]
        area_a = max(0.01, (rect_a[2] - rect_a[0]) * (rect_a[3] - rect_a[1]))
        for j in range(i + 1, len(text_boxes)):
            name_b, rect_b = text_boxes[j]
            area_b = max(0.01, (rect_b[2] - rect_b[0]) * (rect_b[3] - rect_b[1]))
            # 若其中一个是背景大容器完全包住另一个小徽章，允许
            if _contains(rect_a, rect_b) or _contains(rect_b, rect_a):
                continue
            inter = _rect_intersection_area(rect_a, rect_b)
            min_area = min(area_a, area_b)
            if inter / min_area > 0.18:
                errors.append(
                    f"{tag}: Overlapping text shapes {name_a} and {name_b} "
                    f"(overlap={inter / min_area:.0%})"
                )

    if shape_count < 2 or total_chars < 12:
        errors.append(
            f"{tag}: Slide content too sparse (shapes={shape_count}, chars={total_chars})"
        )

    return errors


def audit_pptx(pptx_path: Path, *, expected_slides: int | None = None) -> dict[str, Any]:
    """对整个 deck.pptx 执行 OOXML 确定性审计。"""
    if not pptx_path.is_file():
        return {
            "passed": False,
            "slide_count": 0,
            "errors": [f"PPTX file not found: {pptx_path}"],
        }

    prs = Presentation(str(pptx_path))
    slide_count = len(prs.slides)
    errors: list[str] = []

    if expected_slides is not None and slide_count != expected_slides:
        errors.append(f"Expected {expected_slides} slides, but deck.pptx has {slide_count} slides")
    if slide_count < 4:
        errors.append(f"Presentation has too few slides ({slide_count} < 4)")

    for idx, slide in enumerate(prs.slides, start=1):
        errors.extend(audit_single_slide(slide, idx))

    return {
        "passed": len(errors) == 0,
        "slide_count": slide_count,
        "errors": errors,
    }


__all__ = ["audit_pptx", "audit_single_slide"]
