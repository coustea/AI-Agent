from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import math
import os
import tempfile
from pathlib import Path

from app.shared.ppt.contract import DiagramLayout, VisualRenderMode, visual_component
from app.shared.ppt.models import PPTDeck, PPTSlide, VisualSpec


@dataclass(frozen=True)
class PPTPublication:
    generated_at: datetime


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _render_points(slide: PPTSlide) -> str:
    if not slide.points:
        return ""
    cards = "".join(
        f'<article class="point"><h3>{_escape(point.label)}</h3><p>{_escape(point.detail)}</p></article>'
        for point in slide.points
    )
    return f'<div class="points points-{len(slide.points)}">{cards}</div>'


def _positions(layout: DiagramLayout, count: int) -> list[tuple[float, float]]:
    if count == 1:
        return [(800, 225)]
    if layout is DiagramLayout.HIERARCHY:
        return [(800, 84)] + [
            (240 + item * 1120 / max(count - 2, 1), 324) for item in range(count - 1)
        ]
    if layout is DiagramLayout.RING:
        return [
            (
                800 + 430 * math.cos(-math.pi / 2 + item * 2 * math.pi / count),
                225 + 158 * math.sin(-math.pi / 2 + item * 2 * math.pi / count),
            )
            for item in range(count)
        ]
    if layout is DiagramLayout.GRID:
        columns = min(3, count)
        return [
            (360 + (item % columns) * 440, 120 + (item // columns) * 210)
            for item in range(count)
        ]
    return [(170 + item * 1260 / max(count - 1, 1), 225) for item in range(count)]


def _render_diagram(visual: VisualSpec) -> str:
    nodes = visual.nodes
    if not nodes:
        return '<div class="empty-visual"><b>Visual focus</b><span>本页以关键结论组织讲解</span></div>'
    positions = _positions(visual_component(visual.kind).layout, len(nodes))
    by_id = {node.id: positions[index] for index, node in enumerate(nodes)}
    edges = visual.edges or [
        type("Edge", (), {"source": nodes[index].id, "target": nodes[index + 1].id})()
        for index in range(len(nodes) - 1)
    ]
    lines = "".join(
        f'<path class="diagram-edge" d="M {by_id[edge.source][0]:.0f} {by_id[edge.source][1]:.0f} L {by_id[edge.target][0]:.0f} {by_id[edge.target][1]:.0f}" />'
        for edge in edges
        if edge.source in by_id and edge.target in by_id
    )
    boxes = "".join(
        f'<g class="diagram-node tone-{node.tone}"><rect x="{x - 142:.0f}" y="{y - 54:.0f}" width="284" height="108" rx="20" />'
        f'<text x="{x:.0f}" y="{y - 7:.0f}">{_escape(node.label)}</text>'
        f'<text class="diagram-detail" x="{x:.0f}" y="{y + 24:.0f}">{_escape(node.detail)}</text></g>'
        for node, (x, y) in zip(nodes, positions, strict=True)
    )
    return (
        '<div class="diagram-wrap">'
        f'<svg class="diagram" viewBox="0 0 1600 450" role="img" aria-label="{_escape(visual.title or visual.kind)}">'
        f'{lines}{boxes}</svg><p class="visual-caption">{_escape(visual.caption)}</p></div>'
    )


def _render_visual(visual: VisualSpec) -> str:
    mode = visual_component(visual.kind).render_mode
    if mode is VisualRenderMode.CODE:
        return (
            '<section class="code-panel"><div class="code-head"><i></i><i></i><i></i>'
            f'<b>{_escape(visual.code_language or "example")}</b></div><pre><code>{_escape(visual.code)}</code></pre></section>'
        )
    if mode is VisualRenderMode.FORMULA:
        steps = "".join(f'<li>{_escape(step)}</li>' for step in visual.formula_steps)
        return f'<section class="formula-panel"><div class="formula">{_escape(visual.formula)}</div><ol>{steps}</ol></section>'
    if mode is VisualRenderMode.METRICS:
        metrics = "".join(
            f'<article><strong>{_escape(metric.value)}</strong><b>{_escape(metric.label)}</b><p>{_escape(metric.detail)}</p></article>'
            for metric in visual.metrics
        )
        return f'<section class="metrics">{metrics}</section>'
    return _render_diagram(visual)


def _render_slide(slide: PPTSlide, index: int, total: int) -> str:
    eyebrow_html = f'<div class="eyebrow">{_escape(slide.eyebrow or slide.kind.value)}</div>'
    if slide.kind == "cover" or slide.kind.value == "cover":
        eyebrow_html = f'<div class="author-badge">Presented by Mentorly</div>{eyebrow_html}'

    subtitle = f'<p class="subtitle">{_escape(slide.subtitle)}</p>' if slide.subtitle else ""
    lead = f'<p class="lead">{_escape(slide.lead)}</p>' if slide.lead else ""
    takeaway = f'<footer><span>TAKEAWAY</span>{_escape(slide.takeaway)}</footer>' if slide.takeaway else ""
    active = " active" if index == 0 else ""
    return f'''<section class="slide layout-{slide.layout.value} kind-{slide.kind.value}{active}" data-notes="{_escape(slide.speaker_notes)}">
  <div class="orb orb-one"></div><div class="orb orb-two"></div>
  <div class="shell">
    <header>{eyebrow_html}<div class="page">{index + 1:02d}<i></i>{total:02d}</div><h1>{_escape(slide.title)}</h1>{subtitle}</header>
    <div class="slide-main"><section class="copy">{lead}{_render_points(slide)}</section><section class="visual visual-{slide.visual.kind.value}">{_render_visual(slide.visual)}</section></div>
    {takeaway}
  </div>
</section>'''


BASE_CSS = r'''
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
*{box-sizing:border-box}html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#f8fbff}
body{font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;color:#173b42}
code,.cs-term{font-family:'JetBrains Mono',monospace;background:rgba(70,184,180,0.1);color:#005552;padding:2px 8px;border-radius:6px;font-size:.9em;letter-spacing:-.02em}
.viewport{position:fixed;inset:0;overflow:hidden}.stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px}
.slide{position:absolute;inset:0;width:1920px;height:1080px;visibility:hidden;opacity:0;overflow:hidden;background:linear-gradient(135deg,#ffffff 0%,#f0f5fa 100%);transition:opacity .28s ease}
.slide.active{visibility:visible;opacity:1}
.shell{position:relative;height:100%;padding:68px 102px 82px}
.orb{position:absolute;border:1px solid #46B8B4;border-radius:50%;opacity:.15}
.orb-one{right:-130px;top:-168px;width:540px;height:540px}
.orb-two{left:-188px;bottom:-246px;width:500px;height:500px;border-color:#173B42}
header{position:relative;z-index:1;padding-left:24px;border-left:4px solid #46B8B4}
.author-badge{color:#46B8B4;font-size:18px;font-weight:800;letter-spacing:.15em;margin-bottom:12px;text-transform:uppercase}
.eyebrow{color:#46B8B4;font-size:16px;font-weight:800;letter-spacing:.12em}
.page{position:absolute;right:18px;top:3px;color:#8293ad;font:800 16px/1 'JetBrains Mono',monospace;letter-spacing:.12em}
.page i{display:inline-block;width:48px;height:1px;margin:0 12px 5px;background:#b9cbe7}
h1{max-width:1260px;margin:16px 0 0;font-size:54px;line-height:1.12;letter-spacing:-.045em;color:#0b1d21}
.subtitle{max-width:860px;margin:14px 0 0;color:#526970;font-size:22px;line-height:1.45}
.slide-main{position:relative;z-index:1;height:685px;padding:34px 22px 58px;display:flex;gap:46px;align-items:center}
.copy{flex:1;min-width:0}.visual{flex:1;min-width:0;height:100%;padding:0}
.lead{max-width:720px;margin:0 0 24px;font-size:29px;line-height:1.36;font-weight:750;letter-spacing:-.025em}
.points{display:grid;gap:20px}
.points-3,.points-4{grid-template-columns:repeat(2,minmax(0,1fr))}
.point{min-width:0;min-height:96px;padding:24px;border-radius:18px;background:#fff;box-shadow:0 8px 30px rgba(23,59,66,.05);border:1px solid #e1e9eb}
.point h3{margin:0 0 10px;color:#173B42;font-size:20px;font-weight:800}
.point p{margin:0;color:#526970;font-size:16px;line-height:1.5}
.diagram-wrap{height:100%;display:flex;flex-direction:column;justify-content:center}
.diagram{display:block;width:100%;height:100%;overflow:visible;min-height:450px}
.diagram-edge{fill:none;stroke:#46B8B4;stroke-width:3;marker-end:url(#arrow)}
marker path{fill:#46B8B4}
.diagram-node rect{fill:#fff;stroke:#46B8B4;stroke-width:2}
.diagram-node.tone-secondary rect{fill:#f3fbfa;stroke:#46B8B4}
.diagram-node.tone-accent rect{fill:#fff8ec;stroke:#eeaa42}
.diagram-node.tone-muted rect{fill:#f6f7fa;stroke:#a1aab9}
.diagram-node.tone-warning rect{fill:#fff1f0;stroke:#e78278}
.diagram-node text{fill:#173b42;text-anchor:middle;font-size:25px;font-weight:760}
.diagram-node .diagram-detail{fill:#526970;font-size:15px;font-weight:500}
.visual-caption{margin:16px 0 0;padding:0 18px;color:#71809a;font-size:16px;line-height:1.4;text-align:center;font-style:italic}
.empty-visual{display:grid;place-content:center;height:100%;border:2px dashed #c8d9ef;border-radius:18px;color:#8291a7;text-align:center}
.code-panel{height:100%;overflow:hidden;border-radius:16px;background:#173b42;box-shadow:0 16px 40px rgba(23,59,66,.2)}
.code-head{display:flex;align-items:center;gap:8px;height:46px;padding:0 17px;background:#0b1d21}
.code-head i{width:10px;height:10px;border-radius:50%;background:#ff7e71}
.code-head i:nth-child(2){background:#ffc762}
.code-head i:nth-child(3){background:#65d5a7}
.code-head b{margin-left:auto;color:#46b8b4;font:600 14px 'JetBrains Mono',monospace;text-transform:uppercase}
.code-panel pre{height:calc(100% - 46px);margin:0;padding:27px;color:#f0f5fa;font:18px/1.6 'JetBrains Mono',monospace;white-space:pre-wrap;overflow:auto}
.formula-panel{height:100%;padding:40px;background:#fff;border-radius:24px;border:1px solid #e1e9eb;box-shadow:0 8px 30px rgba(23,59,66,.05)}
.formula{padding:30px;border-radius:17px;background:#f3fbfa;color:#173B42;font:700 36px/1.35 'JetBrains Mono',monospace;text-align:center}
.formula-panel ol{margin:30px 0 0;padding-left:27px;color:#526970;font-size:20px;line-height:1.8}
.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;height:100%}
.metrics article{display:flex;flex-direction:column;justify-content:center;min-height:145px;padding:24px;border:1px solid #e1e9eb;border-radius:20px;background:#fff}
.metrics strong{color:#46B8B4;font-size:48px;letter-spacing:-.05em;font-family:'JetBrains Mono',monospace}
.metrics b{margin-top:12px;font-size:20px;color:#173b42}
.metrics p{margin:8px 0 0;color:#526970;font-size:15px;line-height:1.4}
footer{position:absolute;z-index:1;right:102px;bottom:58px;left:102px;padding:20px 0;border-top:2px solid rgba(70,184,180,0.2);color:#526970;font-size:18px;font-weight:600}
footer span{margin-right:16px;color:#46B8B4;font:800 14px 'JetBrains Mono',monospace;letter-spacing:.15em;text-transform:uppercase}
.layout-hero .slide-main{display:flex;flex-direction:column;justify-content:center;align-items:flex-start;text-align:left;padding:0;height:654px}
.layout-hero .copy{flex:none;width:100%;max-width:1000px}
.layout-hero .lead{font-size:38px;line-height:1.4}
.layout-hero h1{font-size:80px;margin-bottom:24px}
.layout-hero .visual{display:none}
.layout-route .slide-main,.layout-statement .slide-main,.layout-studio .slide-main{display:grid;grid-template-columns:1fr 1fr;gap:60px}
.layout-route .visual,.layout-statement .visual,.layout-studio .visual{height:100%}
.layout-studio .slide-main{grid-template-columns:1.2fr 0.8fr}
.layout-diagram .slide-main,.layout-sequence .slide-main{display:flex;flex-direction:column;align-items:center;text-align:center}
.layout-diagram .copy,.layout-sequence .copy{flex:none}
.layout-diagram header,.layout-sequence header{border:none;padding-left:0;text-align:center}
.layout-diagram header h1,.layout-sequence header h1{margin-left:auto;margin-right:auto}
.layout-diagram .visual,.layout-sequence .visual{width:100%;height:500px;flex:1}
.layout-diagram .points,.layout-sequence .points{display:none}
.layout-comparison .slide-main,.layout-mosaic .slide-main,.layout-recap .slide-main{display:grid;grid-template-columns:1fr 1fr;gap:40px}
.layout-mosaic .points{grid-template-columns:1fr 1fr;grid-column:span 2}
.layout-mosaic .visual{display:none}
.layout-recap .slide-main{grid-template-columns:0.8fr 1.2fr}
.layout-recap .point{background:#173b42;color:#fff}
.layout-recap .point h3{color:#46B8B4}
.layout-recap .point p{color:#a8bee0}
.kind-question h1{font-size:60px}
.deck-controls{position:fixed;z-index:5;right:24px;bottom:22px;display:flex;align-items:center;gap:9px;padding:8px 12px;border-radius:12px;background:rgba(255,255,255,.6);box-shadow:0 4px 15px rgba(0,0,0,.05);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.4)}
.deck-controls button{width:36px;height:32px;border:0;border-radius:8px;background:transparent;color:#526970;font-size:18px;cursor:pointer;transition:all .2s}
.deck-controls button:hover{background:#46b8b4;color:#fff}
.deck-controls button:focus-visible{outline:2px solid #46b8b4;outline-offset:2px}
.deck-counter{min-width:60px;color:#526970;font:600 14px 'JetBrains Mono',monospace;text-align:center}
.speaker-notes{position:fixed;z-index:4;right:24px;bottom:84px;width:360px;max-height:250px;padding:16px 18px;border:1px solid #d2ddec;border-radius:14px;background:#fff;color:#526079;font-size:14px;line-height:1.6;box-shadow:0 12px 30px #1d457d22;display:none}
.speaker-notes.open{display:block}
body.embedded .deck-controls,body.embedded .speaker-notes{display:none}
'''


CONTROLLER_JS = r'''
class DeckController {
  constructor() { this.slides = Array.from(document.querySelectorAll('.slide')); this.current = 0; this.counter = document.getElementById('deckCounter'); this.notes = document.getElementById('speakerNotes'); this.embedded = window.parent !== window; if (this.embedded) document.body.classList.add('embedded'); this.fit(); this.show(0, false); this.bind(); this.post('ready'); }
  post(type) { if (this.embedded) window.parent.postMessage({ source: 'mentorly-ppt', type, current: this.current + 1, total: this.slides.length }, '*'); }
  fit() { const scale = Math.min(innerWidth / 1920, innerHeight / 1080); document.getElementById('deckStage').style.transform = `translate(-50%, -50%) scale(${scale})`; }
  show(index, notify = true) { this.current = Math.max(0, Math.min(index, this.slides.length - 1)); this.slides.forEach((slide, item) => slide.classList.toggle('active', item === this.current)); this.counter.textContent = `${this.current + 1} / ${this.slides.length}`; this.notes.textContent = this.slides[this.current].dataset.notes || '暂无讲稿'; if (notify) this.post('state'); }
  bind() { addEventListener('resize', () => this.fit()); addEventListener('keydown', event => { if (['ArrowRight','PageDown',' '].includes(event.key)) { event.preventDefault(); this.show(this.current + 1); } if (['ArrowLeft','PageUp'].includes(event.key)) { event.preventDefault(); this.show(this.current - 1); } }); document.getElementById('prevSlide').addEventListener('click', () => this.show(this.current - 1)); document.getElementById('nextSlide').addEventListener('click', () => this.show(this.current + 1)); document.getElementById('notesToggle').addEventListener('click', () => document.getElementById('speakerNotes').classList.toggle('open')); let touchStartX = 0; addEventListener('touchstart', e => { touchStartX = e.changedTouches[0].screenX; }, {passive: true}); addEventListener('touchend', e => { const dx = e.changedTouches[0].screenX - touchStartX; if (dx > 50) this.show(this.current - 1); else if (dx < -50) this.show(this.current + 1); }, {passive: true}); addEventListener('message', event => { if (event.source !== window.parent) return; const data = event.data; if (!data || data.source !== 'mentorly-ppt' || data.type !== 'command') return; if (data.action === 'next') this.show(this.current + 1); if (data.action === 'previous') this.show(this.current - 1); if (data.action === 'goto') this.show(Number(data.page) - 1); if (data.action === 'state') this.post('state'); }); }
}
new DeckController();
'''


class PPTHTMLRenderer:
    def render(self, deck: PPTDeck, publication: PPTPublication) -> str:
        slides = "".join(_render_slide(slide, index, len(deck.slides)) for index, slide in enumerate(deck.slides))
        return f'''<!doctype html><html lang="{_escape(deck.language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_escape(deck.title)}</title><style>{BASE_CSS}</style></head><body><svg style="display:none;" aria-hidden="true"><defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#87a9e8" /></marker></defs></svg><div class="viewport"><div class="stage" id="deckStage">{slides}</div></div><nav class="deck-controls"><button id="prevSlide" aria-label="上一页">←</button><span class="deck-counter" id="deckCounter"></span><button id="nextSlide" aria-label="下一页">→</button><button id="notesToggle" aria-label="讲稿">N</button></nav><aside class="speaker-notes" id="speakerNotes"></aside><script>{CONTROLLER_JS}</script></body></html>'''


class PPTHTMLPublisher:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def publish(self, file_id: str, content: str) -> Path:
        if file_id != "slides":
            raise ValueError("PPT publisher only accepts the canonical slides file")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.output_dir / "slides.html"
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.output_dir, suffix=".tmp", delete=False) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, final_path)
            return final_path
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
