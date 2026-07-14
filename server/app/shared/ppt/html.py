from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import math
import os
import tempfile
from pathlib import Path

from app.shared.ppt.contract import SlideKind, VisualRenderMode, visual_component
from app.shared.ppt.models import DeckLogicModel, DiagramModel, PPTDeck, PPTSlide, VisualSpec


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


def _diagram_positions(model: DiagramModel) -> dict[str, tuple[float, float]]:
    nodes = model.nodes
    if model.layout == "flow":
        columns = min(4, len(nodes))
        rows = math.ceil(len(nodes) / columns)
        return {
            node.id: (
                120 + (index % columns) * 760 / max(1, columns - 1),
                280 if rows == 1 else 170 + (index // columns) * 220,
            )
            for index, node in enumerate(nodes)
        }
    if model.layout == "comparison":
        split = max(1, math.ceil(len(nodes) / 2))
        return {
            node.id: (270 if index < split else 730, 110 + (index % split) * 340 / max(1, split - 1))
            for index, node in enumerate(nodes)
        }
    if model.layout == "network":
        positions = {nodes[0].id: (500, 280)}
        for index, node in enumerate(nodes[1:]):
            angle = -math.pi / 2 + 2 * math.pi * index / max(1, len(nodes) - 1)
            positions[node.id] = (500 + 320 * math.cos(angle), 280 + 180 * math.sin(angle))
        return positions

    children: dict[str, list[str]] = {node.id: [] for node in nodes}
    incoming: set[str] = set()
    for edge in model.edges:
        children[edge.source_id].append(edge.target_id)
        incoming.add(edge.target_id)
    roots = [node.id for node in nodes if node.id not in incoming] or [nodes[0].id]
    levels: list[list[str]] = []
    pending, seen = roots, set()
    while pending:
        level = [node_id for node_id in pending if node_id not in seen]
        if not level:
            break
        levels.append(level)
        seen.update(level)
        pending = [child for node_id in level for child in children[node_id] if child not in seen]
    levels.extend([[node.id] for node in nodes if node.id not in seen])
    return {
        node_id: (100 + column * 800 / max(1, len(levels) - 1), 100 + row * 360 / max(1, len(level) - 1))
        for column, level in enumerate(levels)
        for row, node_id in enumerate(level)
    }


def _edge_endpoints(
    source: tuple[float, float],
    target: tuple[float, float],
) -> tuple[float, float, float, float]:
    source_x, source_y = source
    target_x, target_y = target
    delta_x = target_x - source_x
    delta_y = target_y - source_y
    if not delta_x and not delta_y:
        return source_x, source_y, target_x, target_y
    scale = 1 / max(abs(delta_x) / 92, abs(delta_y) / 46)
    offset_x = delta_x * scale
    offset_y = delta_y * scale
    return source_x + offset_x, source_y + offset_y, target_x - offset_x, target_y - offset_y


def _render_model(model: DiagramModel, *, marker_id: str, label: str) -> str:
    positions = _diagram_positions(model)
    rendered_edges: list[str] = []
    for edge in model.edges:
        x1, y1, x2, y2 = _edge_endpoints(positions[edge.source_id], positions[edge.target_id])
        edge_label = ""
        if edge.label:
            edge_label = (
                f'<text x="{(x1 + x2) / 2:.1f}" y="{(y1 + y2) / 2 - 14:.1f}">'
                f'{_escape(edge.label)}</text>'
            )
        rendered_edges.append(
            f'<g class="diagram-edge"><line x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#{marker_id})"/>{edge_label}</g>'
        )
    edges = "".join(rendered_edges)
    nodes = "".join(
        f'<g class="diagram-node tone-{node.tone}" transform="translate({positions[node.id][0]:.1f} {positions[node.id][1]:.1f})"><rect x="-92" y="-46" width="184" height="92" rx="18"/>'
        '<foreignObject x="-82" y="-38" width="164" height="76">'
        '<div xmlns="http://www.w3.org/1999/xhtml" class="diagram-node-copy">'
        f'<strong>{_escape(node.label)}</strong>'
        + (f'<span>{_escape(node.detail)}</span>' if node.detail else "")
        + "</div></foreignObject>"
        + "</g>"
        for node in model.nodes
    )
    return (
        f'<svg class="diagram" viewBox="0 0 1000 560" role="img" aria-label="{_escape(label)}">'
        f'<defs><marker id="{marker_id}" markerWidth="9" markerHeight="9" refX="7" '
        'refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z"/></marker></defs>'
        f'{nodes}{edges}</svg>'
    )



def _render_logic_overview(logic_model: DeckLogicModel, *, summary: bool) -> str:
    relation_labels = {
        "prerequisite": "前置",
        "decomposes": "拆解",
        "supports": "支撑",
        "derives": "推导",
        "causes": "因果",
        "contrasts": "对比",
        "applies": "应用",
        "verifies": "验证",
        "summarizes": "收束",
    }
    chapter_by_node = {
        node_id: chapter.id for chapter in logic_model.chapters for node_id in chapter.node_ids
    }
    links: dict[tuple[str, str], str] = {}
    for edge in logic_model.edges:
        source_chapter = chapter_by_node[edge.source_id]
        target_chapter = chapter_by_node[edge.target_id]
        if source_chapter != target_chapter:
            links.setdefault((source_chapter, target_chapter), relation_labels[edge.relation.value])

    rendered_chapters: list[str] = []
    for index, chapter in enumerate(logic_model.chapters):
        relation_attribute = ""
        if index < len(logic_model.chapters) - 1:
            target_chapter = logic_model.chapters[index + 1]
            relation = links.get((chapter.id, target_chapter.id), "推进")
            relation_attribute = f' data-relation="{_escape(relation)}"'
        rendered_chapters.append(
            f'<article class="logic-stage"{relation_attribute}>'
            f'<span>{index + 1:02d}</span><h3>{_escape(chapter.title)}</h3>'
            f'<p>{_escape(chapter.outcome if summary else chapter.question)}</p>'
            '</article>'
        )
    chapters = "".join(rendered_chapters)
    mode = "已建立的答案" if summary else "需要解决的问题"
    return (
        f'<section class="logic-overview {"is-summary" if summary else ""}">'
        f'<div class="logic-origin"><span>核心问题</span><strong>{_escape(logic_model.central_question)}</strong></div>'
        f'<div class="logic-stages" aria-label="{mode}">{chapters}</div>'
        f'<div class="logic-outcome"><span>{"最终结论" if summary else "学习目标"}</span>'
        f'<strong>{_escape(logic_model.thesis)}</strong></div></section>'
    )


def _render_chapter_rail(logic_model: DeckLogicModel, active_chapter: str | None) -> str:
    items = "".join(
        f'<span class="{"active" if chapter.id == active_chapter else ""}">'
        f'<i>{index + 1:02d}</i>{_escape(chapter.title)}</span>'
        for index, chapter in enumerate(logic_model.chapters)
    )
    return f'<nav class="chapter-rail" aria-label="课程章节进度">{items}</nav>'


def _render_visual(visual: VisualSpec, *, slide_id: str) -> str:
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
    if mode is VisualRenderMode.MODEL:
        if visual.model is None:
            raise ValueError("model visual is missing its structured diagram")
        label = visual.title or visual.caption or "逻辑关系图"
        return (
            f'<div class="diagram-wrap">{_render_model(visual.model, marker_id=f"arrow-{slide_id}", label=label)}'
            f'<p class="visual-caption">{_escape(visual.caption)}</p></div>'
        )
    raise RuntimeError(f"Unsupported visual render mode: {mode}")


def _render_slide(
    slide: PPTSlide,
    index: int,
    total: int,
    logic_model: DeckLogicModel,
) -> str:
    eyebrow_html = f'<div class="eyebrow">{_escape(slide.eyebrow or slide.kind.value)}</div>'
    if slide.kind == "cover" or slide.kind.value == "cover":
        eyebrow_html = f'<div class="author-badge">Presented by Mentorly</div>{eyebrow_html}'

    subtitle = f'<p class="subtitle">{_escape(slide.subtitle)}</p>' if slide.subtitle else ""
    question = f'<p class="logic-question">{_escape(slide.question)}</p>' if slide.question else ""
    lead = f'<p class="lead">{_escape(slide.lead)}</p>' if slide.lead else ""
    conclusion = slide.takeaway or slide.claim
    takeaway = (
        f'<footer><span>本页结论</span><strong>{_escape(conclusion)}</strong></footer>'
        if conclusion
        else '<footer class="empty-footer"></footer>'
    )
    if slide.kind is SlideKind.ROADMAP:
        visual = _render_logic_overview(logic_model, summary=False)
        meta_class = " has-meta-visual"
    elif slide.kind is SlideKind.SUMMARY:
        visual = _render_logic_overview(logic_model, summary=True)
        meta_class = " has-meta-visual"
    else:
        visual = _render_visual(slide.visual, slide_id=slide.id)
        meta_class = ""
    active = " active" if index == 0 else ""
    chapter_rail = (
        ""
        if slide.kind in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}
        else _render_chapter_rail(logic_model, slide.chapter_id)
    )
    notes = "\n\n".join(
        part for part in (f"承接：{slide.bridge}" if slide.bridge else "", slide.speaker_notes) if part
    )
    return f'''<section class="slide layout-{slide.layout.value} kind-{slide.kind.value}{meta_class}{active}" data-notes="{_escape(notes)}" data-chapter="{_escape(slide.chapter_id or "")}">
  <div class="shell">
    <header>{eyebrow_html}<div class="page">{index + 1:02d}<i></i>{total:02d}</div><h1>{_escape(slide.title)}</h1>{subtitle}</header>
    {chapter_rail}
    <div class="slide-main"><section class="copy">{question}{lead}{_render_points(slide)}</section><section class="visual visual-{slide.visual.kind.value}">{visual}</section></div>
    {takeaway}
  </div>
</section>'''


BASE_CSS = r'''
:root{--paper:#f7f8fa;--surface:#fff;--ink:#142326;--muted:#52666b;--quiet:#77898d;--line:#d7e0e2;--accent:#158f8b;--accent-soft:#e8f5f4;--warm:#c77a16;--warning:#b84d43;--code-bg:#102c31;--code-head:#0a2024;--code-text:#f5fbfb;--radius:8px}
*{box-sizing:border-box}html,body{width:100%;height:100%;margin:0;overflow:hidden;background:var(--paper)}
body{font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink)}
code,.cs-term{font-family:Menlo,Monaco,Consolas,monospace;color:var(--ink)}
.viewport{position:fixed;inset:0;overflow:hidden}.stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px}
.slide{position:absolute;inset:0;width:1920px;height:1080px;visibility:hidden;opacity:0;overflow:hidden;background:var(--paper);transition:opacity .22s ease}
.slide.active{visibility:visible;opacity:1}
.shell{display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;height:100%;padding:54px 104px 34px 88px}
.kind-cover .shell,.kind-roadmap .shell,.kind-summary .shell{grid-template-rows:auto minmax(0,1fr) auto}
header{position:relative;padding-left:22px;border-left:4px solid var(--accent)}
.author-badge{margin-bottom:10px;color:var(--accent);font-size:17px;font-weight:800;text-transform:uppercase}
.eyebrow{color:var(--accent);font-size:16px;font-weight:800}
.page{position:absolute;right:0;top:2px;color:var(--quiet);font:700 16px/1 Menlo,Monaco,Consolas,monospace}
.page i{display:inline-block;width:42px;height:1px;margin:0 12px 5px;background:var(--line)}
h1{max-width:1380px;margin:12px 0 0;font-size:52px;line-height:1.12;letter-spacing:0;color:var(--ink)}
.subtitle{max-width:1040px;margin:10px 0 0;color:var(--muted);font-size:21px;line-height:1.4}
.chapter-rail{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:24px;margin-top:22px;border-bottom:1px solid var(--line)}
.chapter-rail span{position:relative;padding:0 0 12px;color:var(--quiet);font-size:15px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chapter-rail span:after{content:"";position:absolute;right:0;bottom:-1px;left:0;height:3px;background:transparent}
.chapter-rail span.active{color:var(--ink)}.chapter-rail span.active:after{background:var(--accent)}
.chapter-rail i{margin-right:8px;color:var(--accent);font:700 13px Menlo,Monaco,Consolas,monospace;font-style:normal}
.slide-main{display:grid;grid-template-columns:minmax(0,42fr) minmax(0,58fr);gap:54px;min-height:0;padding:28px 0 22px;align-items:stretch}
.copy,.visual{min-width:0;min-height:0}.copy{align-self:center}.visual{height:100%}
.logic-question{margin:0 0 16px;padding-left:14px;border-left:3px solid var(--warm);color:#7b4a0f;font-size:18px;font-weight:800;line-height:1.4}
.lead{max-width:780px;margin:0 0 24px;font-size:29px;line-height:1.38;font-weight:750}
.points{display:grid;grid-template-columns:1fr;gap:14px}
.points-3,.points-4{grid-template-columns:repeat(2,minmax(0,1fr))}
.point{min-width:0;min-height:108px;padding:20px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}
.point h3{margin:0 0 8px;color:var(--ink);font-size:21px;font-weight:800}
.point p{margin:0;color:var(--muted);font-size:19px;line-height:1.45}
.diagram-wrap{display:flex;flex-direction:column;justify-content:center;height:100%;min-height:0}
.diagram{display:block;width:100%;height:100%;min-height:390px;overflow:visible}
.diagram-edge{fill:none;stroke:var(--accent);stroke-width:3}.diagram-edge text{fill:#316d6a;font-size:16px;font-weight:700;text-anchor:middle;paint-order:stroke;stroke:var(--paper);stroke-width:6px}
marker path{fill:var(--accent)}
.diagram-node rect{fill:var(--surface);stroke:var(--accent);stroke-width:2;rx:8}
.diagram-node.tone-secondary rect{fill:var(--accent-soft)}.diagram-node.tone-accent rect{fill:#fff8ea;stroke:var(--warm)}
.diagram-node.tone-muted rect{fill:#eef1f2;stroke:#8b999d}.diagram-node.tone-warning rect{fill:#fff0ee;stroke:var(--warning)}
.diagram-node-copy{display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;height:100%;color:var(--ink);text-align:center;line-height:1.2}
.diagram-node-copy strong{font-size:18px}.diagram-node-copy span{margin-top:5px;color:var(--muted);font-size:14px}
.visual-caption{margin:8px 0 0;color:var(--quiet);font-size:17px;line-height:1.4;text-align:center}
.code-panel{height:100%;overflow:hidden;border-radius:var(--radius);background:var(--code-bg);box-shadow:0 12px 28px rgba(16,44,49,.16)}
.code-head{display:flex;align-items:center;gap:8px;height:46px;padding:0 18px;background:var(--code-head)}
.code-head i{width:10px;height:10px;border-radius:50%;background:#e56d62}.code-head i:nth-child(2){background:#e5b853}.code-head i:nth-child(3){background:#55bd91}
.code-head b{margin-left:auto;color:#8bd4d0;font:700 14px Menlo,Monaco,Consolas,monospace;text-transform:uppercase}
.code-panel pre{height:calc(100% - 46px);margin:0;padding:26px 30px;color:var(--code-text);font:21px/1.45 Menlo,Monaco,Consolas,monospace;white-space:pre-wrap;overflow:hidden}
.code-panel pre code{padding:0;border:0;border-radius:0;background:transparent;color:var(--code-text);font:inherit;letter-spacing:0}
.formula-panel{height:100%;padding:34px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}
.formula{padding:26px;border-left:5px solid var(--accent);background:var(--accent-soft);color:var(--ink);font:700 38px/1.35 Menlo,Monaco,Consolas,monospace;text-align:center}
.formula-panel ol{margin:24px 0 0;padding-left:27px;color:var(--muted);font-size:20px;line-height:1.65}
.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;height:100%}
.metrics article{display:flex;flex-direction:column;justify-content:center;min-height:145px;padding:22px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}
.metrics strong{color:var(--accent);font:700 46px/1 Menlo,Monaco,Consolas,monospace}.metrics b{margin-top:12px;font-size:21px}.metrics p{margin:8px 0 0;color:var(--muted);font-size:18px;line-height:1.4}
footer{display:grid;grid-template-columns:118px minmax(0,1fr);gap:16px;align-items:start;min-height:62px;padding:16px 320px 0 0;border-top:1px solid var(--line)}
footer span{color:var(--accent);font:800 14px Menlo,Monaco,Consolas,monospace}footer strong{color:var(--muted);font-size:18px;line-height:1.4}.empty-footer{visibility:hidden}
.logic-overview{display:grid;grid-template-columns:minmax(220px,.8fr) minmax(0,3fr) minmax(240px,1fr);gap:26px;align-items:stretch;height:100%}
.logic-origin,.logic-outcome{display:flex;flex-direction:column;justify-content:center;padding:26px;border-left:5px solid var(--accent);background:var(--surface)}
.logic-origin span,.logic-outcome span{margin-bottom:12px;color:var(--accent);font-size:15px;font-weight:800}.logic-origin strong,.logic-outcome strong{font-size:24px;line-height:1.35}
.logic-stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:42px;align-items:center;position:relative}
.logic-stage{position:relative;min-height:190px;padding:22px 18px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}
.logic-stage:not(:last-child):after{content:attr(data-relation) " \2192";position:absolute;z-index:2;right:-48px;top:50%;width:54px;color:var(--accent);font-size:13px;font-weight:800;text-align:center;transform:translateY(-50%)}
.logic-stage span{color:var(--accent);font:800 14px Menlo,Monaco,Consolas,monospace}.logic-stage h3{margin:18px 0 10px;font-size:22px}.logic-stage p{margin:0;color:var(--muted);font-size:17px;line-height:1.45}
.logic-overview.is-summary .logic-stage{border-top:4px solid var(--accent)}
.has-meta-visual .slide-main{grid-template-columns:1fr}.has-meta-visual .copy{display:none}.has-meta-visual .visual{grid-column:1/-1}
.layout-hero .slide-main{grid-template-columns:minmax(0,48fr) minmax(0,52fr);padding-top:38px}.layout-hero h1{max-width:1180px;font-size:76px}.layout-hero .lead{font-size:36px}
.layout-route .slide-main,.layout-recap .slide-main{grid-template-columns:1fr}
.layout-statement .slide-main{grid-template-columns:minmax(0,46fr) minmax(0,54fr)}
.layout-diagram .slide-main{grid-template-columns:minmax(0,36fr) minmax(0,64fr)}
.layout-sequence .slide-main{grid-template-columns:1fr;grid-template-rows:auto minmax(0,1fr);gap:18px}.layout-sequence .copy{display:grid;grid-template-columns:minmax(260px,.75fr) minmax(0,1.25fr);gap:28px;align-items:start}.layout-sequence .copy .points{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}.layout-sequence .logic-question,.layout-sequence .lead{grid-column:1}.layout-sequence .points{grid-column:2;grid-row:1/3}
.layout-comparison .slide-main{grid-template-columns:1fr 1fr}.layout-studio .slide-main{grid-template-columns:minmax(0,34fr) minmax(0,66fr)}.layout-mosaic .slide-main{grid-template-columns:minmax(0,56fr) minmax(0,44fr)}
.deck-controls{position:fixed;z-index:5;right:10px;top:50%;display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px;border:1px solid rgba(20,35,38,.12);border-radius:var(--radius);background:rgba(255,255,255,.9);box-shadow:0 6px 20px rgba(20,35,38,.1);backdrop-filter:blur(8px);transform:translateY(-50%)}
.deck-controls button{width:36px;height:32px;border:0;border-radius:6px;background:transparent;color:var(--muted);font-size:18px;cursor:pointer}.deck-controls button:hover{background:var(--accent-soft);color:var(--ink)}.deck-controls button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.deck-counter{min-width:42px;padding:7px 0;color:var(--muted);font:700 13px Menlo,Monaco,Consolas,monospace;text-align:center;writing-mode:vertical-rl}
.speaker-notes{position:fixed;z-index:4;right:76px;top:50%;width:380px;max-height:320px;padding:18px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);color:var(--muted);font-size:15px;line-height:1.6;box-shadow:0 12px 30px rgba(20,35,38,.14);display:none;transform:translateY(-50%)}.speaker-notes.open{display:block}
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
        slides = "".join(
            _render_slide(slide, index, len(deck.slides), deck.logic_model)
            for index, slide in enumerate(deck.slides)
        )
        return f'''<!doctype html><html lang="{_escape(deck.language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_escape(deck.title)}</title><style>{BASE_CSS}</style></head><body><div class="viewport"><div class="stage" id="deckStage">{slides}</div></div><nav class="deck-controls"><button id="prevSlide" aria-label="上一页">←</button><span class="deck-counter" id="deckCounter"></span><button id="nextSlide" aria-label="下一页">→</button><button id="notesToggle" aria-label="讲稿">N</button></nav><aside class="speaker-notes" id="speakerNotes"></aside><script>{CONTROLLER_JS}</script></body></html>'''


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
