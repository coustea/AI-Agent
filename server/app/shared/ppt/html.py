from __future__ import annotations

import html
import os
import re
import tempfile
from pathlib import Path

from app.shared.ppt.models import PPTSlide
from app.shared.ppt.templates import ResolvedPPT, ResolvedPPTSlide


BASE_CSS = r"""
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--stage-bg, #eef1f5);
}

body {
  font-family:
    var(
      --font-family,
      "Noto Sans SC",
      "Microsoft YaHei",
      sans-serif
    );
  color: var(--text, #172033);
  user-select: none;
}

.deck-viewport {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

.deck-stage {
  position: absolute;
  left: 0;
  top: 0;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  transform-origin: 0 0;
  background: var(--slide-bg, #ffffff);
}

.slide {
  position: absolute;
  inset: 0;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  background: var(--slide-bg, #ffffff);
}

.slide.active,
.slide.visible {
  z-index: 1;
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
}

.slide-shell {
  position: relative;
  width: 100%;
  height: 100%;
  padding: 74px 104px 70px;
}

.slide-header {
  position: relative;
  z-index: 2;
}

.eyebrow {
  font-size: 18px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted, #667085);
}

.slide-title {
  max-width: 1500px;
  margin-top: 12px;
  font-size: 54px;
  line-height: 1.18;
  letter-spacing: -0.035em;
}

[data-title-size="compact"] .slide-title {
  font-size: 46px;
}

.slide-subtitle {
  max-width: 1200px;
  margin-top: 14px;
  font-size: 25px;
  line-height: 1.5;
  color: var(--muted, #667085);
}

.slide-content {
  position: relative;
  height: 760px;
  margin-top: 38px;
}

.slide-index {
  position: absolute;
  right: 104px;
  top: 82px;
  font-size: 18px;
  color: var(--muted, #667085);
}

.hero-statement {
  max-width: 1420px;
  font-size: 48px;
  line-height: 1.34;
  font-weight: 650;
  letter-spacing: -0.025em;
}

.question-text {
  max-width: 1500px;
  font-size: 58px;
  line-height: 1.28;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.point-list {
  display: grid;
  gap: 24px;
  max-width: 1540px;
  margin-top: 42px;
}

.point-row {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 38px;
  padding: 18px 0;
  border-bottom:
    1px solid
    var(--line, #d9dee8);
}

.point-label {
  font-size: 24px;
  font-weight: 700;
  color: var(--accent, #3157d5);
}

.point-detail {
  font-size: 25px;
  line-height: 1.55;
}

.process {
  display: grid;
  grid-template-columns:
    repeat(
      var(--count, 5),
      minmax(0, 1fr)
    );
  gap: 0;
  align-items: start;
  margin-top: 80px;
}

.process-step {
  position: relative;
  min-height: 250px;
  padding: 0 30px 0 42px;
  border-left:
    2px solid
    var(--line, #d9dee8);
}

.step-key {
  font-size: 18px;
  font-weight: 750;
  color: var(--accent, #3157d5);
}

.step-title {
  margin-top: 18px;
  font-size: 28px;
  line-height: 1.25;
}

.step-detail {
  margin-top: 18px;
  font-size: 21px;
  line-height: 1.55;
  color: var(--muted, #667085);
}

.comparison-table {
  width: 100%;
  margin-top: 34px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 20px;
}

.comparison-table th {
  padding: 18px 20px;
  text-align: left;
  border-bottom:
    2px solid
    var(--text, #172033);
  font-size: 21px;
}

.comparison-table td {
  padding: 19px 20px;
  vertical-align: top;
  border-bottom:
    1px solid
    var(--line, #d9dee8);
  line-height: 1.45;
}

.misconception-list {
  display: grid;
  gap: 28px;
  margin-top: 30px;
}

.misconception-row {
  display: grid;
  grid-template-columns:
    1fr 1.15fr 1.15fr;
  gap: 0;
  border-top:
    1px solid
    var(--line, #d9dee8);
}

.misconception-cell {
  padding: 22px 28px 22px 0;
  font-size: 21px;
  line-height: 1.5;
}

.misconception-cell
+ .misconception-cell {
  padding-left: 28px;
  border-left:
    1px solid
    var(--line, #d9dee8);
}

.cell-label {
  display: block;
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 750;
  letter-spacing: 0.08em;
  color: var(--accent, #3157d5);
}

.knowledge-map {
  position: relative;
  display: grid;
  grid-template-columns:
    330px 1fr;
  gap: 90px;
  align-items: center;
  height: 600px;
}

.map-center {
  font-size: 38px;
  line-height: 1.3;
  font-weight: 720;
}

.map-branches {
  display: grid;
  gap: 24px;
}

.map-branch {
  display: grid;
  grid-template-columns:
    230px 1fr;
  gap: 30px;
  align-items: center;
  padding: 16px 0;
  border-bottom:
    1px solid
    var(--line, #d9dee8);
}

.branch-label {
  font-size: 23px;
  font-weight: 700;
  color: var(--accent, #3157d5);
}

.branch-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 24px;
  font-size: 22px;
}

.takeaway {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding-top: 18px;
  border-top:
    1px solid
    var(--line, #d9dee8);
  font-size: 22px;
  font-weight: 650;
  color: var(--accent, #3157d5);
}

.cover-content,
.closing-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 700px;
}

.cover-meta {
  display: flex;
  gap: 36px;
  margin-top: 56px;
  font-size: 20px;
  color: var(--muted, #667085);
}

.keyword-line {
  margin-top: 24px;
  font-size: 20px;
  color: var(--muted, #667085);
}

.deck-controls {
  position: fixed;
  left: 50%;
  bottom: 22px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  transform: translate(-50%, 12px);
  border-radius: 999px;
  background: rgba(10, 15, 25, 0.82);
  color: #ffffff;
  opacity: 0;
  pointer-events: none;
  backdrop-filter: blur(12px);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

body.controls-visible .deck-controls,
.deck-controls:hover {
  opacity: 0.92;
  pointer-events: auto;
  transform: translate(-50%, 0);
}

.deck-controls button {
  width: 38px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  cursor: pointer;
}

.deck-counter {
  min-width: 64px;
  text-align: center;
  font: 600 13px sans-serif;
}

.deck-progress {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  height: 3px;
  background: rgba(0, 0, 0, 0.08);
  opacity: 0.38;
}

.deck-progress > span {
  display: block;
  width: 0;
  height: 100%;
  background: var(--accent, #3157d5);
  transition: width 0.3s ease;
}

.speaker-notes-panel {
  position: fixed;
  right: 18px;
  bottom: 72px;
  z-index: 1002;
  display: none;
  width: min(580px, 42vw);
  max-height: 36vh;
  overflow: auto;
  padding: 20px;
  border-radius: 12px;
  background: rgba(7, 11, 18, 0.94);
  color: #eef2f8;
  font: 16px/1.6 sans-serif;
}

.speaker-notes-panel.open {
  display: block;
}

[data-step] {
  opacity: 1;
}

@media print {
  html,
  body {
    width: 1920px;
    height: auto;
    overflow: visible;
  }

  .deck-viewport,
  .deck-stage {
    position: static;
    overflow: visible;
    transform: none !important;
  }

  .deck-stage {
    width: auto;
    height: auto;
  }

  .slide {
    position: relative;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    break-after: page;
  }

  .deck-controls,
  .deck-progress,
  .speaker-notes-panel {
    display: none !important;
  }
}

@media (
  prefers-reduced-motion: reduce
) {
  *,
  *::before,
  *::after {
    animation-duration:
      0.01ms !important;
    transition-duration:
      0.01ms !important;
  }
}
"""


CONTROLLER_JS = r"""
class SlidePresentation {
  constructor() {
    this.stage =
      document.getElementById(
        "deckStage"
      );

    this.slides = [
      ...document.querySelectorAll(
        ".slide"
      ),
    ];

    this.current = 0;
    this.controlsTimer = null;

    this.scale();
    this.bind();
    this.show(0);
    this.revealControls();

    window.addEventListener(
      "resize",
      () => this.scale()
    );
  }

  scale() {
    const factor = Math.min(
      window.innerWidth / 1920,
      window.innerHeight / 1080
    );

    const x =
      (
        window.innerWidth
        - 1920 * factor
      ) / 2;

    const y =
      (
        window.innerHeight
        - 1080 * factor
      ) / 2;

    this.stage.style.transform =
      `translate(${x}px, ${y}px) scale(${factor})`;
  }

  revealControls() {
    document.body.classList.add(
      "controls-visible"
    );

    if (this.controlsTimer) {
      clearTimeout(
        this.controlsTimer
      );
    }

    this.controlsTimer = setTimeout(
      () => {
        document.body.classList.remove(
          "controls-visible"
        );
      },
      1500
    );
  }

  show(index) {
    this.current = Math.max(
      0,
      Math.min(
        index,
        this.slides.length - 1
      )
    );

    this.slides.forEach(
      (slide, slideIndex) => {
        const active =
          slideIndex === this.current;

        slide.classList.toggle(
          "active",
          active
        );

        slide.classList.toggle(
          "visible",
          active
        );
      }
    );

    document.getElementById(
      "deckCounter"
    ).textContent =
      `${this.current + 1} / ${this.slides.length}`;

    const percentage =
      (
        (this.current + 1)
        / this.slides.length
      ) * 100;

    document.querySelector(
      "#deckProgress span"
    ).style.width =
      `${percentage}%`;

    const notesPanel =
      document.getElementById(
        "notesPanel"
      );

    notesPanel.textContent =
      this.slides[
        this.current
      ].dataset.notes
      || "暂无讲稿";

    this.revealControls();
  }

  bind() {
    document.addEventListener(
      "mousemove",
      () => this.revealControls()
    );

    document.addEventListener(
      "touchstart",
      () => this.revealControls(),
      {
        passive: true,
      }
    );

    document.getElementById(
      "prevSlide"
    ).addEventListener(
      "click",
      () => this.show(
        this.current - 1
      )
    );

    document.getElementById(
      "nextSlide"
    ).addEventListener(
      "click",
      () => this.show(
        this.current + 1
      )
    );

    document.getElementById(
      "notesToggle"
    ).addEventListener(
      "click",
      () => {
        document.getElementById(
          "notesPanel"
        ).classList.toggle(
          "open"
        );

        this.revealControls();
      }
    );

    document.getElementById(
      "downloadDeck"
    ).addEventListener(
      "click",
      () => this.download()
    );

    window.addEventListener(
      "keydown",
      event => {
        this.revealControls();

        if (
          [
            "ArrowRight",
            "PageDown",
            " ",
          ].includes(event.key)
        ) {
          event.preventDefault();

          this.show(
            this.current + 1
          );
        }

        if (
          [
            "ArrowLeft",
            "PageUp",
          ].includes(event.key)
        ) {
          event.preventDefault();

          this.show(
            this.current - 1
          );
        }

        if (
          event.key.toLowerCase()
          === "n"
        ) {
          document.getElementById(
            "notesPanel"
          ).classList.toggle(
            "open"
          );
        }
      }
    );
  }

  download() {
    const source =
      document.documentElement.outerHTML;

    const blob = new Blob(
      [source],
      {
        type: "text/html",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = url;
    link.download =
      `${document.title || "slides"}.html`;

    link.click();

    URL.revokeObjectURL(url);
  }
}

new SlidePresentation();
"""


_SAFE_FILE_ID = re.compile(
    r"^[A-Za-z0-9_-]+$"
)


def _escape(value: str) -> str:
    return html.escape(
        value,
        quote=True,
    )


def _render_takeaway(
    slide: PPTSlide,
) -> str:
    if not slide.takeaway:
        return ""

    return (
        '<p class="takeaway" data-step>'
        f"{_escape(slide.takeaway)}"
        "</p>"
    )


def _render_statement(
    slide: PPTSlide,
) -> str:
    if not slide.statement:
        return ""

    return (
        '<p class="hero-statement" data-step>'
        f"{_escape(slide.statement)}"
        "</p>"
    )


def _render_points(
    slide: PPTSlide,
) -> str:
    rows = "".join(
        (
            '<div class="point-row" data-step>'
            '<div class="point-label">'
            f"{_escape(point.label)}"
            "</div>"
            '<div class="point-detail">'
            f"{_escape(point.detail)}"
            "</div>"
            "</div>"
        )
        for point in slide.points
    )

    return (
        '<div class="point-list">'
        f"{rows}"
        "</div>"
    )


def _render_process(
    slide: PPTSlide,
) -> str:
    steps = "".join(
        (
            '<article class="process-step" data-step>'
            '<div class="step-key">'
            f"{_escape(step.key)}"
            "</div>"
            '<h3 class="step-title">'
            f"{_escape(step.title)}"
            "</h3>"
            '<p class="step-detail">'
            f"{_escape(step.detail)}"
            "</p>"
            "</article>"
        )
        for step in slide.steps
    )

    return (
        '<div class="process" '
        f'style="--count:{len(slide.steps)}">'
        f"{steps}"
        "</div>"
    )


def _render_table(
    slide: PPTSlide,
) -> str:
    headers = "".join(
        (
            "<th>"
            f"{_escape(value)}"
            "</th>"
        )
        for value in slide.table.headers
    )

    rows = "".join(
        (
            "<tr>"
            + "".join(
                (
                    "<td>"
                    f"{_escape(value)}"
                    "</td>"
                )
                for value in row
            )
            + "</tr>"
        )
        for row in slide.table.rows
    )

    return (
        '<table class="comparison-table">'
        "<thead>"
        f"<tr>{headers}</tr>"
        "</thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def _render_misconceptions(
    slide: PPTSlide,
) -> str:
    rows = "".join(
        (
            '<article class="misconception-row" data-step>'
            '<div class="misconception-cell">'
            '<span class="cell-label">误区</span>'
            f"{_escape(item.myth)}"
            "</div>"
            '<div class="misconception-cell">'
            '<span class="cell-label">为什么错</span>'
            f"{_escape(item.reason)}"
            "</div>"
            '<div class="misconception-cell">'
            '<span class="cell-label">正确理解</span>'
            f"{_escape(item.truth)}"
            "</div>"
            "</article>"
        )
        for item in slide.misconceptions
    )

    return (
        '<div class="misconception-list">'
        f"{rows}"
        "</div>"
    )


def _render_knowledge_map(
    slide: PPTSlide,
) -> str:
    branches = "".join(
        (
            '<div class="map-branch" data-step>'
            '<div class="branch-label">'
            f"{_escape(branch.label)}"
            "</div>"
            '<div class="branch-keywords">'
            + "".join(
                (
                    "<span>"
                    f"{_escape(keyword)}"
                    "</span>"
                )
                for keyword in branch.keywords
            )
            + "</div>"
            "</div>"
        )
        for branch in slide.branches
    )

    center_text = (
        slide.statement
        or slide.title
    )

    return (
        '<div class="knowledge-map">'
        '<div class="map-center">'
        f"{_escape(center_text)}"
        "</div>"
        '<div class="map-branches">'
        f"{branches}"
        "</div>"
        "</div>"
    )


def _render_cover(
    slide: PPTSlide,
) -> str:
    meta = slide.cover_meta

    meta_html = "".join(
        (
            "<span>"
            f"{_escape(value)}"
            "</span>"
        )
        for value in (
            meta.presenter,
            meta.organization,
            meta.date,
        )
        if value
    )

    keywords = " · ".join(
        meta.keywords
    )

    return (
        '<div class="cover-content">'
        '<p class="hero-statement" data-step>'
        f"{_escape(slide.statement)}"
        "</p>"
        '<div class="cover-meta">'
        f"{meta_html}"
        "</div>"
        '<p class="keyword-line">'
        f"{_escape(keywords)}"
        "</p>"
        "</div>"
    )


def render_slide_body(
    slide: PPTSlide,
) -> str:
    if slide.type == "cover":
        return _render_cover(slide)

    if slide.type in {
        "agenda",
        "mechanism_overview",
    }:
        body = _render_process(slide)

    elif slide.type in {
        "learning_goals",
        "definition",
        "knowledge_explain",
    }:
        body = (
            _render_statement(slide)
            + _render_points(slide)
        )

    elif slide.type == "hook_question":
        question = (
            slide.question
            or slide.statement
        )

        body = (
            '<p class="question-text" data-step>'
            f"{_escape(question)}"
            "</p>"
            + _render_points(slide)
        )

    elif slide.type == "concept_boundary":
        body = _render_statement(slide)

        if slide.table.rows:
            body += _render_table(slide)
        else:
            body += _render_points(slide)

    elif slide.type == "comparison":
        body = (
            _render_statement(slide)
            + _render_table(slide)
        )

    elif slide.type == "misconception":
        body = _render_misconceptions(
            slide
        )

    elif slide.type == "knowledge_map":
        body = _render_knowledge_map(
            slide
        )

    elif slide.type == "closing":
        body = (
            '<div class="closing-content">'
            '<p class="hero-statement">'
            f"{_escape(slide.statement)}"
            "</p>"
            "</div>"
        )

    else:
        body = ""

    return (
        body
        + _render_takeaway(slide)
    )


class PPTHTMLRenderer:
    def render(
        self,
        deck: ResolvedPPT,
    ) -> str:
        slides_html = "\n".join(
            self._render_slide(
                resolved,
                index,
                len(deck.slides),
            )
            for index, resolved in enumerate(
                deck.slides
            )
        )

        template_css = deck.template.css.replace(
            "</style",
            "<\\/style",
        )

        return f"""<!doctype html>
<html lang="{_escape(deck.plan.language)}">
<head>
  <meta charset="utf-8">
  <meta
    name="viewport"
    content="width=device-width,initial-scale=1"
  >
  <title>{_escape(deck.plan.title)}</title>
  <style>
    {BASE_CSS}
    {template_css}
  </style>
</head>
<body data-template="{_escape(deck.template.manifest.id)}">
  <div class="deck-viewport">
    <main
      class="deck-stage"
      id="deckStage"
    >
      {slides_html}
    </main>
  </div>

  <div class="deck-progress">
    <span id="deckProgress"></span>
  </div>

  <nav
    class="deck-controls"
    aria-label="演示控制"
  >
    <button
      id="prevSlide"
      aria-label="上一页"
    >
      ←
    </button>

    <span
      class="deck-counter"
      id="deckCounter"
    ></span>

    <button
      id="nextSlide"
      aria-label="下一页"
    >
      →
    </button>

    <button
      id="notesToggle"
      aria-label="显示讲稿"
    >
      N
    </button>

    <button
      id="downloadDeck"
      aria-label="下载 HTML"
    >
      ↓
    </button>
  </nav>

  <div
    class="speaker-notes-panel"
    id="notesPanel"
  ></div>

  <script>
    {CONTROLLER_JS}
  </script>
</body>
</html>"""

    def _render_slide(
        self,
        resolved: ResolvedPPTSlide,
        index: int,
        total: int,
    ) -> str:
        slide = resolved.spec
        layout = resolved.layout

        subtitle_html = ""

        if slide.subtitle:
            subtitle_html = (
                '<p class="slide-subtitle">'
                f"{_escape(slide.subtitle)}"
                "</p>"
            )

        title_size = (
            "compact"
            if len(slide.title) > 24
            else "normal"
        )

        active_class = (
            " active visible"
            if index == 0
            else ""
        )

        notes = _escape(
            slide.speaker_notes
        )

        return f"""
<section
  class="slide{active_class}"
  data-type="{slide.type}"
  data-layout="{_escape(layout.id)}"
  data-skeleton="{_escape(layout.skeleton)}"
  data-animation="{slide.animation}"
  data-title-size="{title_size}"
  data-notes="{notes}"
>
  <div class="slide-shell">
    <span class="slide-index">
      {index + 1:02d} / {total:02d}
    </span>

    <header class="slide-header">
      <div class="eyebrow">
        {_escape(slide.eyebrow or layout.name)}
      </div>

      <h2 class="slide-title">
        {_escape(slide.title)}
      </h2>

      {subtitle_html}
    </header>

    <div class="slide-content">
      {render_slide_body(slide)}
    </div>
  </div>
</section>
"""


class PPTHTMLPublisher:
    def __init__(
        self,
        output_dir: Path,
    ) -> None:
        self.output_dir = output_dir

    def publish(
        self,
        file_id: str,
        content: str,
    ) -> Path:
        if not _SAFE_FILE_ID.fullmatch(
            file_id
        ):
            raise ValueError(
                "PPT file_id contains unsafe characters"
            )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        final_path = (
            self.output_dir
            / f"{file_id}.html"
        )

        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.output_dir,
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(
                    handle.fileno()
                )

                temporary_path = Path(
                    handle.name
                )

            os.replace(
                temporary_path,
                final_path,
            )

            return final_path

        finally:
            if (
                temporary_path is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink()