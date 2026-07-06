from __future__ import annotations

import html
import os
import re
import tempfile
from pathlib import Path

from app.shared.ppt.models import KeyPoint, PPTSlide
from app.shared.ppt.templates import ResolvedPPT, ResolvedPPTSlide


BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; overflow: hidden; background: var(--stage-bg, #000); }
body { user-select: none; }
.deck-viewport { position: fixed; inset: 0; overflow: hidden; background: var(--stage-bg, #000); }
.deck-stage { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; overflow: hidden; transform-origin: 0 0; background: var(--slide-bg, #fff); }
.slide { position: absolute; inset: 0; width: 1920px; height: 1080px; overflow: hidden; visibility: hidden; opacity: 0; pointer-events: none; }
.slide.active, .slide.visible { visibility: visible; opacity: 1; pointer-events: auto; z-index: 1; }
.deck-controls { position: fixed; left: 50%; bottom: 20px; transform: translateX(-50%); z-index: 1000; display: flex; align-items: center; gap: 8px; padding: 8px; border: 1px solid rgba(255,255,255,.2); border-radius: 999px; background: rgba(7,10,16,.8); color: #fff; backdrop-filter: blur(14px); font: 600 13px sans-serif; }
.deck-controls button { width: 36px; height: 32px; border: 0; border-radius: 999px; background: rgba(255,255,255,.1); color: #fff; cursor: pointer; }
.deck-controls button:hover { background: rgba(255,255,255,.22); }
.deck-counter { min-width: 62px; text-align: center; }
.deck-progress { position: fixed; left: 0; right: 0; bottom: 0; z-index: 999; height: 3px; background: rgba(255,255,255,.12); }
.deck-progress > span { display: block; width: 0; height: 100%; background: #5e9eff; transition: width .35s ease; }
.edit-hotzone { position: fixed; left: 0; top: 0; z-index: 10000; width: 80px; height: 80px; cursor: pointer; }
.edit-toggle { position: fixed; left: 18px; top: 18px; z-index: 10001; width: 42px; height: 42px; border: 0; border-radius: 50%; opacity: 0; pointer-events: none; transition: opacity .2s ease; cursor: pointer; }
.edit-toggle.show, .edit-toggle.active { opacity: 1; pointer-events: auto; }
body.editing { user-select: text; }
body.editing [contenteditable="true"] { outline: 2px dashed #5e9eff; outline-offset: 4px; }
.speaker-notes-panel { position: fixed; right: 18px; bottom: 74px; z-index: 1002; width: min(520px, 40vw); max-height: 32vh; overflow: auto; display: none; padding: 18px 20px; border-radius: 12px; background: rgba(6,10,16,.92); color: #e8eef7; font: 16px/1.55 sans-serif; box-shadow: 0 12px 50px rgba(0,0,0,.35); }
.speaker-notes-panel.open { display: block; }
@media print {
  html, body { width: 1920px; height: auto; overflow: visible; background: #fff; }
  .deck-viewport { position: static; overflow: visible; }
  .deck-stage { position: static; width: auto; height: auto; transform: none !important; }
  .slide { position: relative; display: block !important; visibility: visible !important; opacity: 1 !important; pointer-events: auto !important; break-after: page; }
  .deck-controls, .deck-progress, .edit-hotzone, .edit-toggle, .speaker-notes-panel { display: none !important; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
"""


class PPTHTMLRenderer:
    """Render validated slide data into a standalone presentation document."""

    def render(self, deck: ResolvedPPT) -> str:
        slides = "\n".join(
            self._render_slide(slide, index, len(deck.slides))
            for index, slide in enumerate(deck.slides)
        )
        title = html.escape(deck.plan.title)
        template_css = deck.template.css.replace("</style", "<\\/style")
        return f"""<!doctype html>
<html lang="{html.escape(deck.plan.language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{BASE_CSS}\n{template_css}</style>
</head>
<body data-template="{deck.template.manifest.id}">
  <div class="deck-viewport">
    <main class="deck-stage" id="deckStage">{slides}</main>
  </div>
  <div class="deck-progress"><span id="deckProgress"></span></div>
  <nav class="deck-controls" aria-label="演示控制">
    <button id="prevSlide" aria-label="上一页">←</button>
    <span class="deck-counter" id="deckCounter">1 / {len(deck.slides)}</span>
    <button id="nextSlide" aria-label="下一页">→</button>
    <button id="notesToggle" aria-label="讲稿">N</button>
    <button id="downloadDeck" aria-label="保存 HTML">↓</button>
  </nav>
  <div class="speaker-notes-panel" id="notesPanel"></div>
  <div class="edit-hotzone" id="editHotzone"></div>
  <button class="edit-toggle" id="editToggle" aria-label="编辑模式">✎</button>
  <script>{CONTROLLER_JS}</script>
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
        body = self._render_content(slide, layout.id)
        eyebrow = slide.eyebrow or self._role_label(slide.role)
        title_size = "compact" if len(slide.title) > 26 else "normal"
        return f"""
<section class="slide{' active visible' if index == 0 else ''}" data-layout="{layout.id}" data-shape="{slide.shape}" data-animation="{slide.animation}" data-title-size="{title_size}" data-notes="{html.escape(slide.speaker_notes, quote=True)}">
  <div class="slide-shell">
    <div class="slide-index">{index + 1:02d} / {total:02d}</div>
    <div class="eyebrow" data-step style="--step:0">{html.escape(eyebrow)}</div>
    <h2 class="slide-title" data-step style="--step:1" contenteditable="false">{html.escape(slide.title)}</h2>
    {self._optional("p", "slide-subtitle", slide.subtitle, step=2)}
    {body}
    <div class="shape-label">{slide.shape} · {layout.name}</div>
  </div>
</section>"""

    def _render_content(self, slide: PPTSlide, layout_id: str) -> str:
        if layout_id.startswith("cover-"):
            visual = self._points(slide.points) if layout_id == "cover-index" else ""
            return f'<div class="content-stage">{visual}</div>'
        if layout_id == "closing-line":
            return f'<div class="content-stage">{self._takeaway(slide)}</div>'
        if layout_id == "summary-map":
            return self._summary(slide)
        if layout_id == "section-marker":
            return (
                '<div class="content-stage">'
                f'{self._statement(slide)}{self._points(slide.points)}</div>'
            )
        if slide.shape == "quiz":
            return self._quiz(slide)
        if slide.shape == "misconception":
            return self._misconception(slide)
        if slide.shape == "hierarchy":
            return self._hierarchy(slide)
        if slide.shape == "timeline":
            return self._timeline(slide)
        if slide.shape == "matrix":
            return self._matrix(slide)
        renderers = {
            "statement": self._statement_content,
            "concept": self._concept,
            "sequence": self._sequence,
            "comparison": self._comparison,
            "system": self._system,
            "code": self._code,
            "formula": self._formula,
        }
        return renderers[slide.shape](slide)

    def _statement_content(self, slide: PPTSlide) -> str:
        statement = self._statement(slide)
        points = self._points(slide.points)
        takeaway = self._takeaway(slide)
        return (
            '<div class="content-stage">'
            f'<div class="statement-panel">{statement}{takeaway}</div>{points}</div>'
        )

    def _concept(self, slide: PPTSlide) -> str:
        core = slide.statement or slide.takeaway or slide.title
        return (
            '<div class="content-stage">'
            f'<div class="concept-core" data-step style="--step:3">{html.escape(core)}</div>'
            f'{self._points(slide.points)}</div>'
        )

    def _sequence(self, slide: PPTSlide) -> str:
        steps = "".join(
            f"""<article class="step" data-step style="--step:{index + 3}">
  <div class="step-number">{index + 1:02d}</div>
  <h3 class="step-title">{html.escape(step.title)}</h3>
  <p class="step-detail">{html.escape(step.detail)}</p>
</article>"""
            for index, step in enumerate(slide.steps)
        )
        return f'<div class="content-stage"><div class="steps">{steps}</div></div>'

    def _comparison(self, slide: PPTSlide) -> str:
        sides = "".join(
            f"""<article class="comparison-side" data-step style="--step:{index + 3}">
  <h3 class="comparison-title">{html.escape(side.title)}</h3>
  <ul class="comparison-list">{''.join(f'<li>{html.escape(point)}</li>' for point in side.points)}</ul>
</article>"""
            for index, side in enumerate(slide.comparison)
        )
        takeaway_class = " has-takeaway" if slide.takeaway else ""
        return (
            f'<div class="content-stage"><div class="comparison{takeaway_class}">{sides}</div>'
            f'{self._takeaway(slide)}</div>'
        )

    def _system(self, slide: PPTSlide) -> str:
        nodes = "".join(
            f"""<article class="system-node" data-step style="--step:{index + 3}">
  <div class="node-id">{html.escape(node.layer or node.id)}</div>
  <h3 class="node-label">{html.escape(node.label)}</h3>
  <p class="node-detail">{html.escape(node.detail)}</p>
</article>"""
            for index, node in enumerate(slide.nodes)
        )
        return f'<div class="content-stage"><div class="system-nodes">{nodes}</div></div>'

    def _code(self, slide: PPTSlide) -> str:
        notes = slide.points or [
            KeyPoint(label=step.title, detail=step.detail) for step in slide.steps
        ]
        return f"""<div class="content-stage"><div class="code-stage">
  <div class="code-window" data-step style="--step:3">
    <div class="code-caption">{html.escape(slide.code_language or "code")} / execution</div>
    <pre><code>{html.escape(slide.code)}</code></pre>
  </div>
  <div class="code-notes">{self._points(notes)}</div>
</div></div>"""

    def _formula(self, slide: PPTSlide) -> str:
        return f"""<div class="content-stage"><div class="formula-stage">
  <div class="formula" data-step style="--step:3">{html.escape(slide.formula)}</div>
  {self._points(slide.points)}
</div></div>"""

    def _quiz(self, slide: PPTSlide) -> str:
        question = slide.question or slide.title
        return f"""<div class="content-stage">
  <div class="statement" data-step style="--step:3">{html.escape(question)}</div>
  {self._points(slide.points)}
  <div class="answer-panel" data-step style="--step:8"><strong>答案：</strong>{html.escape(slide.answer)}</div>
  <div class="question-mark">?</div>
</div>"""

    def _misconception(self, slide: PPTSlide) -> str:
        """新增：误区纠正布局"""
        sides = "".join(
            f"""<article class="comparison-side" data-step style="--step:{index + 3}">
  <h3 class="comparison-title">{html.escape(side.title)}</h3>
  <ul class="comparison-list">{''.join(f'<li>{html.escape(point)}</li>' for point in side.points)}</ul>
</article>"""
            for index, side in enumerate(slide.comparison)
        )
        return (
            f'<div class="content-stage">'
            f'<div class="statement" data-step style="--step:3">{html.escape(slide.statement)}</div>'
            f'<div class="comparison">{sides}</div>'
            f'{self._takeaway(slide)}</div>'
        )

    def _hierarchy(self, slide: PPTSlide) -> str:
        """新增：层级结构布局"""
        nodes = "".join(
            f"""<article class="hierarchy-node level-{node.level}" data-step style="--step:{index + 3}">
  <div class="hierarchy-label">{html.escape(node.label)}</div>
  <p class="hierarchy-detail">{html.escape(node.detail)}</p>
</article>"""
            for index, node in enumerate(slide.hierarchy)
        )
        return (
            f'<div class="content-stage">'
            f'<div class="hierarchy-tree">{nodes}</div>'
            f'{self._takeaway(slide)}</div>'
        )

    def _timeline(self, slide: PPTSlide) -> str:
        """新增：时间线布局"""
        events = "".join(
            f"""<article class="timeline-event" data-step style="--step:{index + 3}">
  <div class="timeline-time">{html.escape(event.time)}</div>
  <h3 class="timeline-title">{html.escape(event.title)}</h3>
  <p class="timeline-detail">{html.escape(event.detail)}</p>
</article>"""
            for index, event in enumerate(slide.timeline)
        )
        return (
            f'<div class="content-stage">'
            f'<div class="timeline">{events}</div>'
            f'{self._takeaway(slide)}</div>'
        )

    def _matrix(self, slide: PPTSlide) -> str:
        """新增：矩阵表格布局"""
        cells = "".join(
            f"""<div class="matrix-cell{' highlight' if cell.highlight else ''}" data-row="{cell.row}" data-col="{cell.col}" data-step style="--step:{index + 3}">
  {html.escape(cell.content)}
</div>"""
            for index, cell in enumerate(slide.matrix)
        )
        return (
            f'<div class="content-stage">'
            f'<div class="matrix-grid">{cells}</div>'
            f'{self._takeaway(slide)}</div>'
        )

    def _summary(self, slide: PPTSlide) -> str:
        points = slide.points
        if not points:
            points = [
                KeyPoint(label=step.title, detail=step.detail) for step in slide.steps
            ]
        return (
            '<div class="content-stage">'
            f'{self._statement(slide)}{self._points(points)}{self._takeaway(slide)}</div>'
        )

    @staticmethod
    def _statement(slide: PPTSlide) -> str:
        value = slide.statement or slide.question or slide.takeaway or slide.title
        return (
            f'<div class="statement" data-step style="--step:3" '
            f'contenteditable="false">{html.escape(value)}</div>'
        )

    @staticmethod
    def _points(points: list[KeyPoint]) -> str:
        if not points:
            return ""
        items = "".join(
            f"""<article class="point" data-step style="--step:{index + 4}">
  <div class="point-label">{html.escape(point.label)}</div>
  <p class="point-detail">{html.escape(point.detail)}</p>
</article>"""
            for index, point in enumerate(points)
        )
        return f'<div class="points-grid">{items}</div>'

    @staticmethod
    def _takeaway(slide: PPTSlide) -> str:
        if not slide.takeaway:
            return ""
        return (
            f'<div class="takeaway" data-step style="--step:9">'
            f'{html.escape(slide.takeaway)}</div>'
        )

    @staticmethod
    def _optional(
        tag: str,
        class_name: str,
        value: str,
        *,
        step: int,
    ) -> str:
        if not value:
            return ""
        return (
            f'<{tag} class="{class_name}" data-step style="--step:{step}" '
            f'contenteditable="false">{html.escape(value)}</{tag}>'
        )

    @staticmethod
    def _role_label(role: str) -> str:
        labels = {
            "cover": "LESSON OPEN",
            "section": "NEW CHAPTER",
            "hook": "KEY QUESTION",
            "explain": "CONCEPT",
            "derive": "STEP BY STEP",
            "case": "CASE STUDY",
            "practice": "CHECKPOINT",
            "summary": "RECAP",
            "closing": "ONE MORE THING",
        }
        return labels[role]


CONTROLLER_JS = r"""
class SlidePresentation {
  constructor() {
    this.stage = document.getElementById('deckStage');
    this.slides = [...document.querySelectorAll('.slide')];
    this.current = 0;
    this.touchX = null;
    this.editing = false;
    this.scaleStage();
    this.bind();
    this.show(0);
    addEventListener('resize', () => this.scaleStage());
  }
  scaleStage() {
    const factor = Math.min(innerWidth / 1920, innerHeight / 1080);
    const x = (innerWidth - 1920 * factor) / 2;
    const y = (innerHeight - 1080 * factor) / 2;
    this.stage.style.transform = `translate(${x}px, ${y}px) scale(${factor})`;
  }
  show(index) {
    this.current = Math.max(0, Math.min(index, this.slides.length - 1));
    this.slides.forEach((slide, i) => {
      slide.classList.toggle('active', i === this.current);
      slide.classList.toggle('visible', i === this.current);
    });
    document.getElementById('deckCounter').textContent = `${this.current + 1} / ${this.slides.length}`;
    document.getElementById('deckProgress').style.width = `${(this.current + 1) / this.slides.length * 100}%`;
    document.getElementById('notesPanel').textContent = this.slides[this.current].dataset.notes || '本页暂无讲稿。';
  }
  next() { this.show(this.current + 1); }
  prev() { this.show(this.current - 1); }
  bind() {
    document.getElementById('nextSlide').onclick = () => this.next();
    document.getElementById('prevSlide').onclick = () => this.prev();
    document.getElementById('notesToggle').onclick = () => document.getElementById('notesPanel').classList.toggle('open');
    document.addEventListener('keydown', event => {
      if (event.target.closest('[contenteditable="true"]')) return;
      if (['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)) { event.preventDefault(); this.next(); }
      if (['ArrowLeft','ArrowUp','PageUp'].includes(event.key)) { event.preventDefault(); this.prev(); }
      if (event.key.toLowerCase() === 'n') document.getElementById('notesPanel').classList.toggle('open');
      if (event.key.toLowerCase() === 'e') this.toggleEdit();
    });
    document.addEventListener('touchstart', event => { this.touchX = event.changedTouches[0].clientX; }, {passive:true});
    document.addEventListener('touchend', event => {
      if (this.touchX === null) return;
      const delta = event.changedTouches[0].clientX - this.touchX;
      if (Math.abs(delta) > 60) delta < 0 ? this.next() : this.prev();
      this.touchX = null;
    }, {passive:true});
    let wheelLock = false;
    document.addEventListener('wheel', event => {
      if (wheelLock || Math.abs(event.deltaY) < 35) return;
      wheelLock = true;
      event.deltaY > 0 ? this.next() : this.prev();
      setTimeout(() => wheelLock = false, 450);
    }, {passive:true});
    document.getElementById('downloadDeck').onclick = () => this.download();
    const hotzone = document.getElementById('editHotzone');
    const toggle = document.getElementById('editToggle');
    let hideTimer;
    const show = () => { clearTimeout(hideTimer); toggle.classList.add('show'); };
    const hide = () => { hideTimer = setTimeout(() => { if (!this.editing) toggle.classList.remove('show'); }, 400); };
    hotzone.onmouseenter = show; hotzone.onmouseleave = hide;
    toggle.onmouseenter = show; toggle.onmouseleave = hide;
    hotzone.onclick = () => this.toggleEdit();
    toggle.onclick = () => this.toggleEdit();
  }
  toggleEdit() {
    this.editing = !this.editing;
    document.body.classList.toggle('editing', this.editing);
    document.getElementById('editToggle').classList.toggle('active', this.editing);
    document.querySelectorAll('.slide-title,.slide-subtitle,.statement,.point-label,.point-detail,.step-title,.step-detail,.takeaway').forEach(node => {
      node.contentEditable = this.editing ? 'true' : 'false';
    });
  }
  download() {
    const source = '<!doctype html>\n' + document.documentElement.outerHTML;
    const url = URL.createObjectURL(new Blob([source], {type:'text/html;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = (document.title || 'slides') + '.html';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }
}
new SlidePresentation();
"""


_SAFE_FILE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class PPTHTMLPublisher:
    """Atomically publish a standalone PPT document."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def publish(self, file_id: str, content: str) -> Path:
        if not _SAFE_FILE_ID.fullmatch(file_id):
            raise ValueError("PPT file_id contains unsafe characters")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.output_dir / f"{file_id}.html"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.output_dir,
                prefix=f".{file_id}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, final_path)
            return final_path
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
