from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import os
import tempfile
from pathlib import Path

from app.shared.ppt.contract import SLIDE_KIND_LABELS, SlideKind
from app.shared.ppt.models import DeckLogicModel, PPTDeck, PPTSlide
from app.shared.ppt.visual_renderers import render_visual


@dataclass(frozen=True)
class PPTPublication:
    generated_at: datetime


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _render_points(slide: PPTSlide) -> str:
    if not slide.points:
        return ""
    items = "".join(
        f'<article class="point">'
        f'<span class="point-index">{index:02d}</span>'
        f'<div class="point-copy"><h3>{_escape(point.label)}</h3>'
        f'<p>{_escape(point.detail)}</p></div></article>'
        for index, point in enumerate(slide.points, start=1)
    )
    return f'<div class="points points-{len(slide.points)}">{items}</div>'


def _render_cover_visual() -> str:
    """Return a renderer-owned visual anchor for otherwise text-only covers."""
    return '''<div class="cover-signal" aria-hidden="true">
  <span class="cover-ring cover-ring-a"></span><span class="cover-ring cover-ring-b"></span>
  <span class="cover-link cover-link-a"></span><span class="cover-link cover-link-b"></span>
  <i class="cover-node cover-node-a"></i><i class="cover-node cover-node-b"></i>
  <i class="cover-node cover-node-c"></i><i class="cover-node cover-node-d"></i>
  <b>知识结构</b>
</div>'''


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
        f'<div class="logic-bookends">'
        f'<div class="logic-origin"><span>核心问题</span><strong>{_escape(logic_model.central_question)}</strong></div>'
        f'<div class="logic-bridge" aria-hidden="true"><i></i><span>知识链</span><i></i></div>'
        f'<div class="logic-outcome"><span>{"最终结论" if summary else "学习目标"}</span>'
        f'<strong>{_escape(logic_model.thesis)}</strong></div></div>'
        f'<div class="logic-stages" aria-label="{mode}">{chapters}</div>'
        f'</section>'
    )


def _render_chapter_rail(logic_model: DeckLogicModel, active_chapter: str | None) -> str:
    items = "".join(
        f'<span class="{"active" if chapter.id == active_chapter else ""}">'
        f'<i>{index + 1:02d}</i>{_escape(chapter.title)}</span>'
        for index, chapter in enumerate(logic_model.chapters)
    )
    return f'<nav class="chapter-rail" aria-label="课程章节进度">{items}</nav>'


def _render_slide(
    slide: PPTSlide,
    index: int,
    total: int,
    logic_model: DeckLogicModel,
) -> str:
    label = SLIDE_KIND_LABELS[slide.kind]
    eyebrow = f'<div class="eyebrow">{_escape(label)}</div>'
    if slide.kind is SlideKind.COVER:
        eyebrow = (
            '<div class="author-badge">MENTORLY · AI COURSEWARE</div>'
            f'{eyebrow}'
        )

    subtitle = (
        f'<p class="subtitle">{_escape(slide.subtitle)}</p>'
        if slide.subtitle
        else ""
    )
    question = (
        f'<p class="logic-question">{_escape(slide.question)}</p>'
        if slide.question
        else ""
    )
    lead = f'<p class="lead">{_escape(slide.lead)}</p>' if slide.lead else ""

    meta_kinds = {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}
    takeaway = (
        '<footer class="takeaway">'
        '<span>核心结论</span>'
        f'<strong>{_escape(slide.claim)}</strong>'
        '</footer>'
        if slide.kind not in meta_kinds and slide.claim
        else '<footer class="empty-footer"></footer>'
    )

    if slide.kind is SlideKind.ROADMAP:
        visual = _render_logic_overview(logic_model, summary=False)
        visual_kind = "logic-overview"
        meta_class = " has-meta-visual"
    elif slide.kind is SlideKind.SUMMARY:
        visual = _render_logic_overview(logic_model, summary=True)
        visual_kind = "logic-overview"
        meta_class = " has-meta-visual"
    elif slide.kind is SlideKind.COVER:
        visual = _render_cover_visual()
        visual_kind = "cover"
        meta_class = ""
    else:
        if slide.visual is None:
            raise ValueError(f"content slide {slide.id} is missing its visual payload")
        visual = render_visual(slide.visual, slide.id)
        visual_kind = slide.visual.kind
        meta_class = ""

    active = " active" if index == 0 else ""
    chapter_rail = (
        ""
        if slide.kind in meta_kinds
        else _render_chapter_rail(logic_model, slide.chapter_id)
    )
    notes = "\n\n".join(
        part
        for part in (
            f"承接：{slide.bridge}" if slide.bridge else "",
            slide.speaker_notes,
        )
        if part
    )
    slide_classes = (
        f"slide layout-{slide.layout.value} kind-{slide.kind.value}"
        f" density-{slide.density} visual-type-{visual_kind}"
        f"{meta_class}{active}"
    )
    return f'''<section class="{slide_classes}" data-notes="{_escape(notes)}" data-chapter="{_escape(slide.chapter_id or "")}">
  <div class="shell">
    <header>{eyebrow}<div class="page"><b>{index + 1:02d}</b><i></i><span>{total:02d}</span></div><h1>{_escape(slide.title)}</h1>{subtitle}</header>
    {chapter_rail}
    <div class="slide-main"><section class="copy">{question}{lead}{_render_points(slide)}</section><section class="visual visual-{_escape(visual_kind)}">{visual}</section></div>
    {takeaway}
  </div>
</section>'''


BASE_CSS = r'''
:root{
  --paper:#f8fbfb;
  --surface:#ffffff;
  --surface-soft:#f2f8f7;
  --ink:#17363a;
  --ink-strong:#0e2a2e;
  --muted:#557277;
  --quiet:#86a0a4;
  --line:#d8e7e5;
  --line-strong:#bdd7d4;
  --accent:#149b95;
  --accent-deep:#0d716d;
  --accent-soft:rgba(20,155,149,.09);
  --accent-faint:rgba(20,155,149,.035);
  --warm:#bf7617;
  --warm-soft:#fff7eb;
  --warning:#b84d43;
  --radius:14px;
  --shadow:0 18px 48px rgba(27,61,64,.07);
}
*{box-sizing:border-box}
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#eaf1f0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC",sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.viewport{position:fixed;inset:0;overflow:hidden}
.stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px;filter:drop-shadow(0 22px 50px rgba(26,54,58,.12))}
.slide{position:absolute;inset:0;width:1920px;height:1080px;visibility:hidden;opacity:0;overflow:hidden;background:var(--paper);background-image:radial-gradient(rgba(20,155,149,.028) 1.2px,transparent 1.2px);background-size:30px 30px;transform:translateY(8px);transition:opacity .16s ease,transform .18s ease}
.slide.active{visibility:visible;opacity:1;transform:translateY(0)}
.slide:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(135deg,rgba(255,255,255,.4),transparent 34%)}
.kind-cover{background:radial-gradient(circle at 78% 22%,rgba(20,155,149,.14),transparent 36%),radial-gradient(circle at 94% 82%,rgba(191,118,23,.08),transparent 28%),var(--paper)}
.shell{position:relative;z-index:1;display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;height:100%;padding:48px 86px 34px}
.kind-cover .shell,.kind-roadmap .shell,.kind-summary .shell{grid-template-rows:auto minmax(0,1fr) auto}
header{position:relative;padding-left:22px}
header:before{content:"";position:absolute;left:0;top:2px;width:5px;height:100%;max-height:92px;border-radius:3px;background:linear-gradient(180deg,var(--accent),var(--accent-deep))}
.author-badge{margin-bottom:10px;color:var(--accent-deep);font-size:15px;font-weight:850;letter-spacing:.13em}
.eyebrow{color:var(--accent);font-size:16px;font-weight:850;letter-spacing:.12em}
.page{position:absolute;right:0;top:0;display:flex;align-items:center;gap:12px;color:var(--quiet);font:750 15px/1 "JetBrains Mono","Fira Code",monospace}
.page b{color:var(--accent-deep);font-size:17px}.page span{font-size:14px}.page i{display:block;width:46px;height:1px;background:var(--line-strong)}
h1{max-width:1390px;margin:10px 0 0;color:var(--ink-strong);font-size:50px;line-height:1.15;font-weight:820;letter-spacing:-.035em}
.subtitle{max-width:1100px;margin:10px 0 0;color:var(--muted);font-size:20px;line-height:1.45}
.chapter-rail{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:34px;margin-top:20px;border-bottom:1px solid var(--line)}
.chapter-rail span{position:relative;padding:0 0 11px;color:var(--quiet);font-size:16px;font-weight:720;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chapter-rail span:after{content:"";position:absolute;right:0;bottom:-1px;left:0;height:3px;background:transparent;border-radius:3px 3px 0 0}
.chapter-rail span.active{color:var(--ink-strong)}.chapter-rail span.active:after{background:var(--accent)}
.chapter-rail i{margin-right:9px;color:var(--accent);font:750 13px "JetBrains Mono",monospace;font-style:normal}
.slide-main{display:grid;grid-template-columns:minmax(0,39fr) minmax(0,61fr);gap:48px;min-height:0;padding:24px 0 18px;align-items:stretch}
.copy,.visual{min-width:0;min-height:0}.copy{align-self:center;overflow:hidden;padding-right:2px}.visual{position:relative;display:flex;align-items:center;justify-content:center;height:100%;padding:22px 26px;overflow:hidden;border:1px solid rgba(20,155,149,.12);border-radius:18px;background:linear-gradient(145deg,rgba(255,255,255,.9),rgba(240,248,247,.72));box-shadow:inset 0 1px 0 rgba(255,255,255,.9),var(--shadow)}
.visual:before{content:"";position:absolute;inset:0;pointer-events:none;background-image:linear-gradient(rgba(20,155,149,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(20,155,149,.035) 1px,transparent 1px);background-size:36px 36px;mask-image:linear-gradient(to bottom right,black,transparent 82%)}
.visual>*{position:relative;z-index:1}
.logic-question{display:inline-block;max-width:100%;margin:0 0 18px;padding:7px 12px;border-left:4px solid var(--warm);border-radius:0 7px 7px 0;background:var(--warm-soft);color:#7d4b0d;font-size:17px;font-weight:780;line-height:1.42}
.lead{max-width:770px;margin:0 0 24px;color:var(--ink-strong);font-size:29px;line-height:1.42;font-weight:790;letter-spacing:-.018em}
.points{display:grid;grid-template-columns:1fr;gap:0;border-top:1px solid var(--line)}
.point{position:relative;display:grid;grid-template-columns:38px minmax(0,1fr);gap:12px;min-width:0;padding:15px 0;border-bottom:1px solid var(--line);background:transparent}
.point-index{display:grid;place-items:center;width:32px;height:32px;margin-top:1px;border:1px solid rgba(20,155,149,.26);border-radius:9px;background:var(--accent-soft);color:var(--accent-deep);font:800 12px/1 "JetBrains Mono",monospace}
.point-copy{min-width:0}.point h3{margin:0 0 5px;color:var(--ink-strong);font-size:20px;font-weight:800;letter-spacing:-.012em}.point p{margin:0;color:var(--muted);font-size:17.5px;line-height:1.48;overflow-wrap:anywhere}
.density-concise .lead{font-size:31px}.density-concise .point p{font-size:17px}.density-detailed .lead{font-size:27px}.density-detailed .point p{font-size:16.5px;line-height:1.44}
.diagram-wrap{display:flex;flex-direction:column;justify-content:center;width:100%;height:100%;min-height:0}.diagram{display:block;width:100%;height:100%;min-height:0;overflow:visible}
.diagram-edge{fill:none;stroke:var(--accent);stroke-width:3}.diagram-edge text{fill:var(--accent-deep);font-size:16px;font-weight:750;text-anchor:middle;paint-order:stroke;stroke:var(--surface);stroke-width:7px}.diagram-edge path,.diagram-edge line{stroke:var(--accent);stroke-width:3}
marker path{fill:var(--accent)}
.diagram-node rect{fill:rgba(255,255,255,.96);stroke:var(--accent);stroke-width:2.2;rx:12;filter:drop-shadow(0 5px 10px rgba(25,69,71,.08))}
.diagram-node.tone-secondary rect{fill:var(--accent-soft)}.diagram-node.tone-accent rect{fill:#fff7e9;stroke:var(--warm)}.diagram-node.tone-muted rect{fill:#eef2f2;stroke:#8b999d}.diagram-node.tone-warning rect{fill:#fff0ee;stroke:var(--warning)}
.diagram-node-copy{display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;height:100%;padding:4px;color:var(--ink-strong);text-align:center;line-height:1.23}.diagram-node-copy strong{font-size:18px}.diagram-node-copy span{margin-top:5px;color:var(--muted);font-size:14px}
.timeline-event-copy{display:flex;align-items:center;justify-content:center;width:100%;height:100%;padding:2px 4px;color:var(--ink-strong);font:700 12px/1.12 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;text-align:center;overflow:hidden;word-break:break-all}
.visual-caption{margin:10px 0 0;color:var(--quiet);font-size:17px;line-height:1.4;text-align:center;font-weight:550}
.visual-table_matrix,.visual-algorithm_frames,.visual-formula{align-items:center}
.table-matrix-panel{display:flex;align-items:center;width:100%;height:100%;min-height:0;overflow:hidden}.table-matrix-panel table{width:100%;border-collapse:separate;border-spacing:0;border:1px solid var(--line-strong);border-radius:13px;background:var(--surface);box-shadow:0 12px 28px rgba(20,35,38,.05);overflow:hidden}.table-matrix-panel th,.table-matrix-panel td{padding:17px 21px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);font-size:18px;line-height:1.42;text-align:left;vertical-align:middle;overflow-wrap:anywhere;word-break:break-word}.table-matrix-panel th:last-child,.table-matrix-panel td:last-child{border-right:0}.table-matrix-panel tbody tr:last-child td{border-bottom:0}.table-matrix-panel th{color:var(--accent-deep);background:var(--accent-soft);font-size:17px;font-weight:820}.table-matrix-panel td:first-child{width:29%;color:var(--ink-strong);font-weight:780}.table-matrix-panel td.highlighted{background:#f3fbfa}.table-matrix-panel tr.highlighted td{box-shadow:inset 4px 0 0 var(--accent)}
.algorithm-frames-panel{display:flex;align-items:center;width:100%;height:100%;min-height:0;overflow:hidden}.frames-row{display:flex;align-items:stretch;width:100%;gap:16px}.algo-frame{display:flex;flex:1;flex-direction:column;justify-content:center;min-height:220px;padding:22px;border:1px solid var(--line-strong);border-radius:14px;background:rgba(255,255,255,.95);box-shadow:0 10px 24px rgba(20,35,38,.05)}.algo-frame h4{margin:0 0 15px;color:var(--accent-deep);font-size:18px;font-weight:820}.algo-cells{display:grid;gap:9px}.algo-cells span{display:block;padding:13px 14px;border-left:4px solid var(--line-strong);border-radius:0 7px 7px 0;background:#f5f9f9;color:var(--ink);font-size:18px;font-weight:680;line-height:1.4;overflow-wrap:anywhere}.algo-cells span.highlighted{border-left-color:var(--accent);background:var(--accent-soft)}.frame-arrow{display:grid;place-items:center;flex:0 0 24px;color:var(--accent);font-size:30px;font-weight:800}
.formula-panel{display:flex;flex-direction:column;justify-content:center;width:min(100%,900px);padding:27px;border:1px solid var(--line-strong);border-radius:14px;background:var(--surface);box-shadow:0 14px 30px rgba(20,35,38,.05)}.formula{padding:22px 25px;border-left:6px solid var(--accent);border-radius:0 12px 12px 0;background:var(--accent-soft);color:var(--ink-strong);font:700 33px/1.3 "JetBrains Mono",monospace;text-align:center}.formula-panel ol{margin:19px 0 0;padding-left:24px;color:var(--muted);font-size:19px;line-height:1.55}
.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:17px;width:100%;height:100%}.metrics article{display:flex;flex-direction:column;justify-content:center;min-height:140px;padding:22px;border:1px solid var(--line-strong);border-radius:14px;background:var(--surface);box-shadow:0 8px 20px rgba(17,35,38,.035)}.metrics strong{color:var(--accent);font:750 46px/1 "JetBrains Mono",monospace}.metrics b{margin-top:11px;font-size:21px}.metrics p{margin:7px 0 0;color:var(--muted);font-size:17px;line-height:1.43}
.takeaway{display:grid;grid-template-columns:96px minmax(0,1fr);gap:18px;align-items:center;min-height:58px;padding-top:14px;border-top:1px solid var(--line)}.takeaway span{color:var(--accent-deep);font:800 13px "JetBrains Mono",monospace;letter-spacing:.04em}.takeaway strong{color:var(--muted);font-size:17px;line-height:1.42}.empty-footer{min-height:0;visibility:hidden}
.visual-logic-overview{display:flex;align-items:center;padding:30px 38px}.logic-overview{display:flex;flex-direction:column;width:min(100%,1580px);gap:34px}.logic-bookends{display:grid;grid-template-columns:minmax(0,1fr) 118px minmax(0,1.18fr);gap:20px;align-items:stretch}.logic-origin,.logic-outcome{display:flex;flex-direction:column;justify-content:center;min-height:150px;padding:25px 30px;border:1px solid var(--line-strong);border-top:5px solid var(--accent);border-radius:14px;background:rgba(255,255,255,.96);box-shadow:0 12px 28px rgba(20,35,38,.05)}.logic-origin span,.logic-outcome span{margin-bottom:10px;color:var(--accent-deep);font-size:14px;font-weight:830;letter-spacing:.08em}.logic-origin strong,.logic-outcome strong{color:var(--ink-strong);font-size:23px;line-height:1.36}.logic-bridge{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:9px;color:var(--accent);font:800 13px "JetBrains Mono",monospace}.logic-bridge i{display:block;width:100%;height:2px;background:var(--accent)}.logic-bridge i:last-child:after{content:"";display:block;float:right;margin-top:-4px;border:5px solid transparent;border-left-color:var(--accent)}.logic-stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:42px;align-items:stretch}.logic-stage{position:relative;min-height:174px;padding:23px 24px;border:1px solid var(--line-strong);border-radius:14px;background:rgba(255,255,255,.96);box-shadow:0 10px 24px rgba(20,35,38,.04)}.logic-stage:not(:last-child):after{content:attr(data-relation) "  →";position:absolute;z-index:2;right:-48px;top:50%;width:54px;color:var(--accent-deep);font-size:13px;font-weight:800;text-align:center;transform:translateY(-50%)}.logic-stage span{color:var(--accent);font:800 13px "JetBrains Mono",monospace}.logic-stage h3{margin:13px 0 9px;color:var(--ink-strong);font-size:22px;font-weight:820}.logic-stage p{margin:0;color:var(--muted);font-size:17px;line-height:1.47}.logic-overview.is-summary .logic-stage{border-top:5px solid var(--accent)}
.has-meta-visual .slide-main{grid-template-columns:1fr;padding-top:30px}.has-meta-visual .copy{display:none}.has-meta-visual .visual{grid-column:1/-1}
.layout-hero .slide-main{grid-template-columns:minmax(0,50fr) minmax(0,50fr);gap:66px;padding-top:42px}.layout-hero h1{max-width:1160px;font-size:76px;line-height:1.08}.layout-hero .lead{max-width:900px;font-size:35px;line-height:1.38}.layout-hero .logic-question{font-size:18px}.layout-hero .point{padding:17px 0}.layout-hero .visual{border:0;background:transparent;box-shadow:none}.layout-hero .visual:before{display:none}
.visual-cover{display:flex;align-items:center;justify-content:center}.cover-signal{position:relative;width:570px;height:570px;border:1px solid rgba(20,155,149,.24);border-radius:50%;background:radial-gradient(circle at center,rgba(255,255,255,.96) 0 30%,transparent 30.5%),linear-gradient(135deg,rgba(20,155,149,.09),rgba(20,155,149,.015));overflow:hidden;box-shadow:0 24px 70px rgba(20,83,82,.08)}.cover-signal:before,.cover-signal:after{content:"";position:absolute;border-radius:50%}.cover-signal:before{inset:74px;border:1px solid rgba(20,155,149,.2)}.cover-signal:after{inset:144px;border:1px solid rgba(20,155,149,.16)}.cover-ring{position:absolute;border:2px solid var(--accent);border-radius:50%;animation:soft-rotate 36s infinite linear}.cover-ring-a{width:96px;height:96px;left:92px;top:142px;transform-origin:190px 140px}.cover-ring-b{width:130px;height:130px;right:72px;bottom:102px;border-color:var(--warm);animation-direction:reverse;animation-duration:48s}.cover-link{position:absolute;z-index:1;height:2px;background:var(--accent);transform-origin:left center}.cover-link-a{width:252px;left:162px;top:190px;transform:rotate(22deg)}.cover-link-b{width:208px;left:238px;top:345px;transform:rotate(-38deg);background:var(--warm)}.cover-node{position:absolute;z-index:2;width:29px;height:29px;border:6px solid var(--surface);border-radius:50%;background:var(--accent);box-shadow:0 4px 14px rgba(20,155,149,.22),0 0 0 2px var(--accent)}.cover-node-a{left:145px;top:173px}.cover-node-b{left:382px;top:266px}.cover-node-c{left:364px;top:216px;background:var(--warm);box-shadow:0 4px 14px rgba(191,118,23,.22),0 0 0 2px var(--warm)}.cover-node-d{left:247px;top:339px;background:var(--warm);box-shadow:0 4px 14px rgba(191,118,23,.22),0 0 0 2px var(--warm)}.cover-signal b{position:absolute;z-index:2;inset:0;display:grid;place-items:center;color:var(--accent-deep);font-size:23px;font-weight:840;letter-spacing:.18em}
@keyframes soft-rotate{to{transform:rotate(360deg)}}
.layout-route .slide-main,.layout-recap .slide-main{grid-template-columns:1fr}
.layout-statement .slide-main{grid-template-columns:minmax(0,40fr) minmax(0,60fr)}
.layout-diagram .slide-main{grid-template-columns:minmax(0,36fr) minmax(0,64fr)}
.layout-comparison .slide-main{grid-template-columns:minmax(0,37fr) minmax(0,63fr)}
.layout-studio .slide-main{grid-template-columns:minmax(0,32fr) minmax(0,68fr)}
.layout-mosaic .slide-main{grid-template-columns:minmax(0,49fr) minmax(0,51fr)}
.layout-sequence .slide-main{grid-template-columns:1fr;grid-template-rows:auto minmax(0,1fr);gap:17px;padding-top:20px}.layout-sequence .copy{display:grid;grid-template-columns:minmax(360px,.82fr) minmax(0,1.55fr);gap:34px;align-items:start}.layout-sequence .logic-question,.layout-sequence .lead{grid-column:1}.layout-sequence .lead{margin-bottom:0;font-size:27px}.layout-sequence .points{grid-column:2;grid-row:1/3;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;border-top:0}.layout-sequence .point{display:block;padding:16px 17px;border:1px solid var(--line-strong);border-radius:13px;background:rgba(255,255,255,.94)}.layout-sequence .point-index{margin-bottom:10px}.layout-sequence .point h3{font-size:18px}.layout-sequence .point p{font-size:16px;line-height:1.42}.layout-sequence .visual{min-height:300px;padding:14px 20px}
.deck-controls{position:fixed;z-index:8;right:24px;bottom:22px;display:flex;align-items:center;gap:5px;padding:7px;border:1px solid rgba(20,56,58,.13);border-radius:12px;background:rgba(255,255,255,.9);box-shadow:0 10px 30px rgba(20,45,48,.14);backdrop-filter:blur(10px)}.deck-controls button{width:38px;height:34px;border:0;border-radius:8px;background:transparent;color:var(--muted);font-size:18px;cursor:pointer}.deck-controls button:hover{background:var(--accent-soft);color:var(--ink-strong)}.deck-controls button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.deck-counter{min-width:72px;padding:0 8px;color:var(--muted);font:750 13px "JetBrains Mono",monospace;text-align:center}.speaker-notes{position:fixed;z-index:7;right:24px;bottom:74px;width:410px;max-height:330px;padding:20px;border:1px solid var(--line-strong);border-radius:14px;background:rgba(255,255,255,.97);color:var(--muted);font-size:15px;line-height:1.65;box-shadow:0 18px 44px rgba(20,45,48,.16);display:none;overflow:auto}.speaker-notes.open{display:block}
body.embedded .deck-controls,body.embedded .speaker-notes{display:none}
'''


CONTROLLER_JS = r'''
class DeckController {
  constructor() {
    this.slides = Array.from(document.querySelectorAll('.slide'));
    this.current = 0;
    this.counter = document.getElementById('deckCounter');
    this.notes = document.getElementById('speakerNotes');
    this.stage = document.getElementById('deckStage');
    this.embedded = window.parent !== window;
    this.resizeTimer = 0;
    if (this.embedded) document.body.classList.add('embedded');
    this.fitDeck();
    this.show(0, false);
    this.bind();
    this.post('ready');
  }

  post(type) {
    if (!this.embedded) return;
    window.parent.postMessage({
      source: 'mentorly-ppt',
      type,
      current: this.current + 1,
      total: this.slides.length,
    }, '*');
  }

  fitDeck() {
    const scale = Math.min(innerWidth / 1920, innerHeight / 1080);
    this.stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  }

  normalizeTimeline(svg) {
    if (!svg || svg.dataset.timelineNormalized === 'true') return;
    const rects = Array.from(svg.children).filter(node => node.tagName && node.tagName.toLowerCase() === 'rect');
    rects.forEach(rect => {
      const label = rect.nextElementSibling;
      if (!label || label.tagName.toLowerCase() !== 'text') return;
      const width = Number(rect.getAttribute('width') || 0);
      const height = 48;
      const x = Number(rect.getAttribute('x') || 0);
      const centerY = Number(rect.getAttribute('y') || 0) + Number(rect.getAttribute('height') || 0) / 2;
      rect.setAttribute('y', String(centerY - height / 2));
      rect.setAttribute('height', String(height));
      rect.setAttribute('rx', '10');

      const foreignObject = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
      foreignObject.setAttribute('x', String(x + 2));
      foreignObject.setAttribute('y', String(centerY - height / 2 + 2));
      foreignObject.setAttribute('width', String(Math.max(1, width - 4)));
      foreignObject.setAttribute('height', String(height - 4));
      const copy = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
      copy.setAttribute('class', 'timeline-event-copy');
      copy.textContent = label.textContent || '';
      foreignObject.appendChild(copy);
      label.replaceWith(foreignObject);
    });
    svg.dataset.timelineNormalized = 'true';
  }

  fitSvg(svg) {
    if (!svg || typeof svg.getBBox !== 'function') return;
    let box;
    try { box = svg.getBBox(); } catch (_) { return; }
    if (!box || box.width <= 0 || box.height <= 0) return;

    const host = svg.closest('.visual');
    if (!host || host.clientWidth <= 0 || host.clientHeight <= 0) return;
    const targetRatio = host.clientWidth / host.clientHeight;
    const padX = Math.max(28, box.width * 0.045);
    const padY = Math.max(24, box.height * 0.10);
    let width = box.width + padX * 2;
    let height = box.height + padY * 2;
    const centerX = box.x + box.width / 2;
    const centerY = box.y + box.height / 2;

    if (width / height > targetRatio) height = width / targetRatio;
    else width = height * targetRatio;

    svg.setAttribute('viewBox', `${centerX - width / 2} ${centerY - height / 2} ${width} ${height}`);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  }

  fitCurrentVisual() {
    const slide = this.slides[this.current];
    if (!slide) return;
    requestAnimationFrame(() => {
      slide.querySelectorAll('svg.diagram').forEach(svg => {
        if (svg.getAttribute('aria-label') === 'timeline') this.normalizeTimeline(svg);
        this.fitSvg(svg);
      });
    });
  }

  show(index, notify = true) {
    this.current = Math.max(0, Math.min(index, this.slides.length - 1));
    this.slides.forEach((slide, item) => {
      slide.classList.toggle('active', item === this.current);
      slide.setAttribute('aria-hidden', item === this.current ? 'false' : 'true');
    });
    this.counter.textContent = `${String(this.current + 1).padStart(2, '0')} / ${String(this.slides.length).padStart(2, '0')}`;
    this.notes.textContent = this.slides[this.current].dataset.notes || '暂无讲稿';
    this.fitCurrentVisual();
    if (notify) this.post('state');
  }

  bind() {
    addEventListener('resize', () => {
      clearTimeout(this.resizeTimer);
      this.resizeTimer = setTimeout(() => {
        this.fitDeck();
        this.fitCurrentVisual();
      }, 60);
    });

    addEventListener('keydown', event => {
      if (['ArrowRight', 'PageDown', ' '].includes(event.key)) {
        event.preventDefault();
        this.show(this.current + 1);
      }
      if (['ArrowLeft', 'PageUp'].includes(event.key)) {
        event.preventDefault();
        this.show(this.current - 1);
      }
      if (event.key === 'Home') this.show(0);
      if (event.key === 'End') this.show(this.slides.length - 1);
      if (event.key.toLowerCase() === 'n') this.notes.classList.toggle('open');
    });

    document.getElementById('prevSlide').addEventListener('click', () => this.show(this.current - 1));
    document.getElementById('nextSlide').addEventListener('click', () => this.show(this.current + 1));
    document.getElementById('notesToggle').addEventListener('click', () => this.notes.classList.toggle('open'));

    let touchStartX = 0;
    addEventListener('touchstart', event => {
      touchStartX = event.changedTouches[0].screenX;
    }, { passive: true });
    addEventListener('touchend', event => {
      const deltaX = event.changedTouches[0].screenX - touchStartX;
      if (deltaX > 50) this.show(this.current - 1);
      else if (deltaX < -50) this.show(this.current + 1);
    }, { passive: true });

    addEventListener('message', event => {
      if (event.source !== window.parent) return;
      const data = event.data;
      if (!data || data.source !== 'mentorly-ppt' || data.type !== 'command') return;
      if (data.action === 'next') this.show(this.current + 1);
      if (data.action === 'previous') this.show(this.current - 1);
      if (data.action === 'goto') this.show(Number(data.page) - 1);
      if (data.action === 'state') this.post('state');
    });
  }
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
