"""Slide Contract Skeleton — Copy via copy_skill_template and edit to author bespoke slide visuals.

Rules for SlideSubagent:
1. Keep the signature `def build_slide(prs, theme: dict) -> None:` which adds exactly 1 slide (`prs.slides.add_slide(prs.slide_layouts[6])`).
2. DO NOT make every slide look the same! Compose bespoke layouts tailored to the slide's content:
   - Hero Cover / Executive Summary: dark background (`theme["bg_dark"]`), oversized title, metric callouts (`add_metric_stat`), or pillar cards.
   - Process / Architecture Flow: multi-stage pipeline cards connected by `add_arrow_right` or custom `MSO_SHAPE` blocks.
   - Code / Formula Spotlight: asymmetric split with `add_code_panel` on one side and step-by-step annotations (`add_card`) on the other.
   - Comparison / Trade-off Matrix: side-by-side contrast columns (`accent_primary` vs `accent_secondary`) or 2x2 Bento grid.
   - Deep-Dive Concept: hero metric stat + layered architecture blocks.
3. All shapes must stay within the 13.333" x 7.500" canvas (margins >= 0.35") with zero overlapping sibling bounding boxes.
4. Always call `set_speaker_notes(slide, ...)` with rich teaching narration.
"""

from __future__ import annotations

from ppt_helpers import (
    add_arrow_right,
    add_badge,
    add_card,
    add_code_panel,
    add_header_banner,
    add_metric_stat,
    add_takeaway_bar,
    add_text_box,
    apply_slide_background,
    set_speaker_notes,
)


def build_slide(prs, theme: dict) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_background(slide, theme["bg_light"])

    add_header_banner(
        slide,
        theme,
        badge_text="__SLIDE_BADGE__",
        title="__SLIDE_TITLE__",
        subtitle="__SLIDE_SUBTITLE__",
    )

    # BESPOKE_SLIDE_BODY: Replace with custom cards, flow arrows, metric stats, or code panels
    add_card(
        slide,
        theme,
        left=0.65,
        top=1.85,
        width=12.03,
        height=4.20,
        title="__SLIDE_TITLE__",
        body="__SLIDE_CLAIM__",
        badge="01",
        accent_bar="left",
    )

    add_takeaway_bar(
        slide,
        theme,
        label="核心结论",
        text="__SLIDE_TAKEAWAY__",
        slide_number=__SLIDE_INDEX__,
        total_slides=__TOTAL_SLIDES__,
    )
    set_speaker_notes(slide, "__SLIDE_NOTES__")
