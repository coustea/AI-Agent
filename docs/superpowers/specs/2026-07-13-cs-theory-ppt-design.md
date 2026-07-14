# CS Theory PPT Layout & Typography Design Spec

## 1. Goal
Establish a structured, highly scannable, and visually dynamic presentation layout system specifically tailored for Computer Science theoretical knowledge (algorithms, data structures, architectures).

## 2. Core Layout Strategy (Hybrid Space & Focus)
- **Open Space (No Borders):** Core theoretical explanations, definitions, and high-level bullet points will reside in open whitespace without card enclosures to maintain breathing room and an academic feel.
- **Card Focus:** Deep dark cards for `Code Snippets` and `Terminal Outputs` (IDE vibe); Theme-tinted soft cards for `Theorems` and `Formulas`.
- **Layout Variance (Rhythm):** To prevent visual fatigue, consecutive slides MUST NOT use the exact same layout structure unless absolutely necessary. The presentation should alternate between distinct layouts.

## 3. Layout Archetypes
To support layout variance, we define multiple distinct layout archetypes:
1. **Code-Split (Left Text / Right Code):** Left side uses open space for definitions; right side uses a dark, glowing card for code.
2. **Canvas (Diagram Focus):** 80% whitespace for flowchart/architecture rendering. Minimal top/bottom text.
3. **Step-by-Step (Timeline/Algorithm Step):** Top horizontal card for current state/theorem, bottom open area for sequential logic flow.
4. **Hero/Statement:** Massive typography centered or left-aligned for core "AHA" moments or chapter transitions. No cards.

## 4. Typography (CS Specific)
- **Primary Text:** `Geist` or `Inter` (sans-serif) for high readability in open spaces.
- **CS Terminology:** `JetBrains Mono` for all technical terms (e.g., `O(N)`, `Mutex`). Terminology will be wrapped in soft-grey background spans for inline distinction.
- **Hierarchy:** 
  - Slide Titles: 48pt+ (bold, high contrast)
  - Body Text: 24pt-28pt (regular, medium contrast)
  - Annotations: 16pt-18pt (muted)
- **Line Height:** 1.4 for body text to allow comfortable reading.

## 5. Visual Accents
- **Glacier Teal:** The primary accent color for active elements and important theorem cards.
- **Doppelrand Pattern:** When cards are used, they will utilize a subtle double-border structure (inner card + faint outer halo) to create depth without heavy drop-shadows.

## 6. Implementation Target
These principles will be integrated into the PPT generation engine (`server/app/shared/ppt/html.py` and CSS templates) to automatically produce varied, hybrid-styled HTML presentations based on the semantic content of the slide.
