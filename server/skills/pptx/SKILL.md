---
name: pptx
description: "Author professional, agency-grade 16:9 PowerPoint (.pptx) teaching decks using python-pptx via a Plan-and-Execute workflow, deterministic OOXML geometry audit, and visual thumbnail inspection."
version: "2.0.0"
---

# PPTX Authoring Skill (`python-pptx`)

Use this skill whenever planning, authoring, or reviewing PowerPoint (`.pptx`) presentations.

## 1. Core Design Philosophy

Never generate generic "title + 5 bullet points on white background" slides. Every deck must look like an intentional, agency-designed teaching deck:

1. **60-30-10 Color Rule**:
   - **60% Dominant**: Slide background (`bg_light` for content slides, `bg_dark` for Cover / Section Divider / Summary).
   - **30% Secondary**: Structured cards, containers, panels, and comparison columns (`surface_card`, `border_subtle`).
   - **10% Accent**: One high-contrast focal color (`accent_primary`) reserved for key badges, metric callouts, active flow nodes, and primary takeaways.
2. **Dark/Light Sandwich Structure**:
   - **Cover (`s01`)** and **Summary (`sNN`)** use dark/bold theme backgrounds (`bg_dark`) with high-contrast light typography (`text_on_dark`) to frame the lesson.
   - **Content slides (`s02..sN-1`)** use clean, readable light canvas (`bg_light`) with structured cards (`surface_card`).
3. **Recurring Visual Motif**:
   - Every slide shares a consistent visual anchor: e.g., a top-left chapter pill badge (`CHAPTER 01 · 核心机制`), a left accent bar on cards (`0.08"` wide rectangle filled with `accent_primary`), and a bottom footer bar with slide number.
4. **No Consecutive Identical Layouts**:
   - Never use the same layout archetype (`layout`) on two consecutive slides (`slides[i].layout != slides[i-1].layout`).
   - Rotate across diverse visual layouts:
     - `hero_cover` — Dark cover with badge, bold title, subtitle, and 3 key takeaway pills
     - `roadmap_grid` — 3–4 chapter cards showing learning trajectory and core questions
     - `split_concept` — Left core thesis card + Right 2–3 stacked evidence cards
     - `three_columns` — 3 equal-width cards with top accent bars, number badges, headers, and details
     - `process_flow` — Horizontal step-by-step pipeline with connector arrows (`RIGHT_ARROW` / chevrons) and bottom detail callout
     - `comparison_matrix` — Two-column side-by-side comparison (`A vs B` or `误区 vs 正解`) with distinct header bands
     - `bento_quad` — 2×2 grid of structured cards for multi-faceted analysis
     - `code_or_formula_spotlight` — Dark code/formula panel on the left + annotated step breakdown on the right
     - `summary_takeaways` — Dark closing slide with numbered takeaway cards and self-check questions
5. **Every Content Slide Needs a Visual Anchor**:
   - Pure text paragraphs are forbidden. Every slide must organize information into geometric shapes (`ROUNDED_RECTANGLE`, `RECTANGLE`, `OVAL` number badges, `RIGHT_ARROW` connectors, table grids, or native charts).

---

## 2. Canvas & Geometry Contract (16:9 Widescreen)

- **Slide Dimensions**: `13.333` inches wide × `7.5` inches high (`Inches(13.333)`, `Inches(7.5)`).
- **Safe Margins**:
  - Left / Right margin: `>= 0.6"` (`x >= 0.6"`, `x + w <= 12.733"`)
  - Top margin: `>= 0.5"` (`y >= 0.5"`)
  - Bottom margin: `>= 0.45"` (`y + h <= 7.05"`)
- **Header Zone (`y = 0.50" .. 1.65"`)**:
  - Chapter / Kind Pill Badge at `(0.65", 0.48", w=2.4", h=0.34")`
  - Slide Title at `(0.65", 0.88", w=12.0", h=0.65")`, font size `24pt–28pt` Bold
- **Content Zone (`y = 1.75" .. 6.20"`)**:
  - All cards, diagrams, columns, and flows live inside `x in [0.65", 12.68"]`, `y in [1.75", 6.15"]`.
- **Bottom Takeaway / Bridge Bar (`y = 6.30" .. 6.95"`)**:
  - A full-width subtle banner at `(0.65", 6.32", w=12.03", h=0.58")` summarizing the one-sentence takeaway or logical bridge to the next slide.
- **Zero Unintentional Overlap**:
  - Sibling cards and text boxes must have `>= 0.18"` gap between them.
  - When placing text on top of a background card shape, either:
    1. Write text directly into the shape's `text_frame`, **or**
    2. Use the helper `add_card(...)` / `add_textbox(...)` and keep text strictly inside its parent card bounds.
- **Typography Scale**:
  - Cover Title: `36pt–44pt` Bold
  - Slide Title: `24pt–28pt` Bold
  - Card Title / Section Heading: `16pt–18pt` Bold
  - Card Body / Evidence: `13pt–15pt` Regular (never `< 12pt`)
  - Badge / Footer Caption: `11pt–12pt` Bold
  - Font family: `"PingFang SC"` or `"Microsoft YaHei"` for Chinese/mixed text, `"Consolas"` for code blocks.

---

## 3. Contract Skeletons & Bespoke Slide Authoring (`templates/`)

This skill provides physical contract files in `templates/`:
- `templates/ppt_helpers.py` — Atomic `python-pptx` drawing primitives (`rgb`, `apply_slide_background`, `add_text_box`, `add_badge`, `add_header_banner`, `add_card`, `add_metric_stat`, `add_code_panel`, `add_arrow_right`, `add_takeaway_bar`, `set_speaker_notes`).
- `templates/build_deck.py` — Deck compiler that imports `slides/s01.py .. slides/sNN.py` and builds `deck.pptx`.
- `templates/slide_skeleton.py` — Minimal `build_slide(prs, theme)` contract skeleton.
- `templates/viewer.html` — Interactive HTML slide player with `mentorly-ppt` `postMessage` support and `.pptx` download button.

### Plan-and-Execute Workflow

1. **Step 1 — Load Skill & Plan (`DESIGN_PLAN.json` + `theme_tokens.py`)**:
   - Analyze the teaching topic, learner profile, and upstream materials.
   - Design a 7–10 slide deck with a clear narrative arc (`s01` cover → `s02` roadmap → `s03..sN-1` core teaching slides → `sNN` summary).
   - Ensure no two consecutive slides share the same visual composition.
   - Call `init_deck_plan` to initialize `DESIGN_PLAN.json`, `theme_tokens.py`, and copy `ppt_helpers.py` and `build_deck.py` from `templates/` into the workspace.
2. **Step 2 — Author Bespoke Slide Modules (`slides/s01.py` .. `slides/sNN.py`)**:
   - Each `SlideSubagent` copies `templates/slide_skeleton.py` to `slides/sXX.py` via `copy_skill_template(skill="pptx", template="slide_skeleton.py", destination="slides/sXX.py", replacements=...)`.
   - Then `SlideSubagent` uses `edit` / `write` to author bespoke `python-pptx` code tailored to that slide's teaching objective (custom multi-stage diagrams, metric stat callouts, code + annotation splits, comparison matrices, or Bento grids).
   - Every slide is immediately verified in isolation (`test_slide`) via deterministic OOXML geometry audit (`audit_single_slide`) to catch syntax errors, out-of-bounds shapes, text overflow, or overlapping sibling boxes.
3. **Step 3 — Build, Audit & Visual Review (`build_and_audit_deck`)**:
   - Run `build_and_audit_deck` to execute `build_deck.py`, producing `deck.pptx`, running the full-deck OOXML geometry audit, rendering `thumbnails/slide_01.png .. slide_NN.png` + `thumbnails/grid.png`, and publishing `slides.html` from `templates/viewer.html`.
   - Call `view_image` on `thumbnails/grid.png` to visually inspect the entire presentation grid for visual balance, contrast, and text legibility.
   - If any slide fails the OOXML audit or visual check, fix that specific `slides/sXX.py` and re-run `build_and_audit_deck`.

For `python-pptx` code recipes and `ppt_helpers` API details, load reference `python_pptx_cookbook.md` via `load_skill(name="pptx", reference="python_pptx_cookbook.md")`.
