from __future__ import annotations

import html
import os
import tempfile
from pathlib import Path

from app.shared.ppt.renderers import get_slide_body_renderer
from app.shared.ppt.templates import ResolvedPPT, ResolvedPPTSlide


BASE_CSS = """
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
  background: var(--stage-bg, #000);
}

body {
  user-select: none;
}

.deck-viewport {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: var(--stage-bg, #000);
}

.deck-stage {
  position: absolute;
  left: 0;
  top: 0;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  transform-origin: 0 0;
  background: var(--slide-bg, #fff);
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
}

.slide.active,
.slide.visible {
  visibility: visible;
  opacity: 1;
  pointer-events: auto;
  z-index: 1;
}

.slide-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
}

.slide-title,
.slide-subtitle,
.eyebrow,
.slide-index,
[data-step] {
  position: relative;
  z-index: 2;
}

.deck-controls {
  position: fixed;
  left: 50%;
  bottom: 20px;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 999px;
  background: rgba(7,10,16,.78);
  color: #fff;
  backdrop-filter: blur(14px);
  font: 600 13px sans-serif;
}

.deck-controls button {
  width: 36px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: rgba(255,255,255,.1);
  color: #fff;
  cursor: pointer;
}

.deck-controls button:hover {
  background: rgba(255,255,255,.22);
}

.deck-counter {
  min-width: 62px;
  text-align: center;
}

.deck-progress {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  height: 3px;
  background: rgba(255,255,255,.12);
}

.deck-progress > span {
  display: block;
  width: 0;
  height: 100%;
  background: #5e9eff;
  transition: width .35s ease;
}

.edit-hotzone {
  position: fixed;
  left: 0;
  top: 0;
  z-index: 10000;
  width: 80px;
  height: 80px;
  cursor: pointer;
}

.edit-toggle {
  position: fixed;
  left: 18px;
  top: 18px;
  z-index: 10001;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  opacity: 0;
  pointer-events: none;
  transition: opacity .2s ease;
  cursor: pointer;
}

.edit-toggle.show,
.edit-toggle.active {
  opacity: 1;
  pointer-events: auto;
}

body.editing {
  user-select: text;
}

body.editing [contenteditable="true"] {
  outline: 2px dashed #5e9eff;
  outline-offset: 4px;
}

.speaker-notes-panel {
  position: fixed;
  right: 18px;
  bottom: 74px;
  z-index: 1002;
  width: min(560px, 42vw);
  max-height: 34vh;
  overflow: auto;
  display: none;
  padding: 18px 20px;
  border-radius: 12px;
  background: rgba(6,10,16,.92);
  color: #e8eef7;
  font: 16px/1.55 sans-serif;
  box-shadow: 0 12px 50px rgba(0,0,0,.35);
}

.speaker-notes-panel.open {
  display: block;
}

@media print {
  html,
  body {
    width: 1920px;
    height: auto;
    overflow: visible;
    background: #fff;
  }

  .deck-viewport {
    position: static;
    overflow: visible;
  }

  .deck-stage {
    position: static;
    width: auto;
    height: auto;
    transform: none !important;
  }

  .slide {
    position: relative;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    break-after: page;
  }

  .deck-controls,
  .deck-progress,
  .edit-hotzone,
  .edit-toggle,
  .speaker-notes-panel {
    display: none !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
  }
}
"""


class PPTHTMLRenderer:
    """将 PPTPlan 渲染为独立 HTML。

    现在渲染器只负责：
    1. 输出 HTML 外壳
    2. 根据 template_id 选择专属 body renderer
    3. 保留单文件 HTML 导出能力

    页面主体 DOM 由 app.shared.ppt.renderers 下的模板专属 renderer 负责。
    """

    def render(self, deck: ResolvedPPT) -> str:
        template_id = deck.template.manifest.id
        body_renderer = get_slide_body_renderer(template_id)

        slides = "\n".join(
            self._render_slide(
                resolved=resolved,
                index=index,
                total=len(deck.slides),
                body_renderer=body_renderer,
            )
            for index, resolved in enumerate(deck.slides)
        )

        title = html.escape(deck.plan.title)
        lang = html.escape(deck.plan.language)
        escaped_template_id = html.escape(template_id)
        template_css = deck.template.css.replace("</style", "<\\/style")

        return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{BASE_CSS}\n{template_css}</style>
</head>
<body data-template="{escaped_template_id}">
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
        *,
        resolved: ResolvedPPTSlide,
        index: int,
        total: int,
        body_renderer,
    ) -> str:
        slide = resolved.spec
        layout = resolved.layout
        title_size = "compact" if len(slide.title) > 24 else "normal"
        subtitle = (
            f'<p class="slide-subtitle" data-step style="--step:2" contenteditable="false">'
            f"{html.escape(slide.subtitle)}</p>"
            if slide.subtitle
            else ""
        )
        body = body_renderer.render(slide, layout)

        return f"""
<section class="slide{' active visible' if index == 0 else ''}"
  data-layout="{html.escape(layout.id)}"
  data-skeleton="{html.escape(layout.skeleton)}"
  data-type="{html.escape(slide.type)}"
  data-animation="{html.escape(slide.animation)}"
  data-title-size="{title_size}"
  data-notes="{html.escape(slide.speaker_notes, quote=True)}">
  <div class="slide-shell">
    <div class="slide-index">{index + 1:02d} / {total:02d}</div>
    <div class="eyebrow" data-step style="--step:0">{html.escape(slide.eyebrow or layout.name)}</div>
    <h2 class="slide-title" data-step style="--step:1" contenteditable="false">{html.escape(slide.title)}</h2>
    {subtitle}
    {body}
  </div>
</section>"""


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
      if (['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)) {
        event.preventDefault();
        this.next();
      }
      if (['ArrowLeft','ArrowUp','PageUp'].includes(event.key)) {
        event.preventDefault();
        this.prev();
      }
      if (event.key.toLowerCase() === 'n') {
        document.getElementById('notesPanel').classList.toggle('open');
      }
      if (event.key.toLowerCase() === 'e') {
        this.toggleEdit();
      }
    });

    document.addEventListener('touchstart', event => {
      this.touchX = event.changedTouches[0].clientX;
    }, {passive:true});

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

    const show = () => {
      clearTimeout(hideTimer);
      toggle.classList.add('show');
    };

    const hide = () => {
      hideTimer = setTimeout(() => {
        if (!this.editing) toggle.classList.remove('show');
      }, 400);
    };

    hotzone.onmouseenter = show;
    hotzone.onmouseleave = hide;
    toggle.onmouseenter = show;
    toggle.onmouseleave = hide;
    hotzone.onclick = () => this.toggleEdit();
    toggle.onclick = () => this.toggleEdit();
  }

  toggleEdit() {
    this.editing = !this.editing;
    document.body.classList.toggle('editing', this.editing);
    document.getElementById('editToggle').classList.toggle('active', this.editing);
    document.querySelectorAll('[contenteditable]').forEach(node => {
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


_SAFE_FILE_ID = __import__("re").compile(r"^[A-Za-z0-9_-]+$")


class PPTHTMLPublisher:
    """原子化发布独立 HTML PPT。"""

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