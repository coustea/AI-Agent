"""Compile a structured teaching storyboard into deterministic HyperFrames HTML.

支持计算机理论知识的动画演示 — 树、图、队列、栈、链表等数据结构的动态操作演示。
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from app.shared.cartoon.schemas import (
    AnimationCue,
    CartoonVideoRequest,
    SceneBrief,
    VideoBrief,
    VisualElement,
)


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _seconds(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


@dataclass(frozen=True)
class _Theme:
    name: str
    background: str
    surface: str
    surface_strong: str
    foreground: str
    muted: str
    accent: str
    accent_two: str
    line: str


_THEMES = {
    "diagram": _Theme(
        name="教学图解",
        background="#f4f1e9",
        surface="#fffdf8",
        surface_strong="#ebe5d8",
        foreground="#17202b",
        muted="#66707d",
        accent="#1769ff",
        accent_two="#ff8a3d",
        line="#cfd5dc",
    ),
    "minimal": _Theme(
        name="清晰简约",
        background="#f7f8fa",
        surface="#ffffff",
        surface_strong="#edf1f5",
        foreground="#111820",
        muted="#68727d",
        accent="#2563eb",
        accent_two="#12a594",
        line="#d7dde4",
    ),
    "dark_tech": _Theme(
        name="克制暗黑科技",
        background="#07111d",
        surface="#0d1b2a",
        surface_strong="#12283a",
        foreground="#f1f7fb",
        muted="#91a5b7",
        accent="#4bd8c3",
        accent_two="#5d9dff",
        line="#24445b",
    ),
    "chalkboard": _Theme(
        name="黑板粉笔",
        background="#1a3d2e",
        surface="#234d3a",
        surface_strong="#2d5f4a",
        foreground="#f5f5f0",
        muted="#a8c4b8",
        accent="#ffd700",
        accent_two="#ff6b6b",
        line="#3d6b52",
    ),
}


def _object_id(scene_index: int, object_id: str) -> str:
    return f"s{scene_index}-{object_id}"


_PACE_CONFIG = {
    "fast": {"duration": 0.35, "stagger": 0.06},
    "normal": {"duration": 0.55, "stagger": 0.12},
    "slow": {"duration": 0.85, "stagger": 0.18},
}


def _render_items(element: VisualElement) -> str:
    if not element.items:
        return ""
    item_class = {
        "array": "horizontal",
        "queue": "horizontal",
        "stack": "vertical",
        "code": "code-lines",
    }.get(element.kind, "horizontal")
    items = "".join(
        f'<span class="object-item">{_escape(item)}</span>'
        for item in element.items
    )
    return f'<div class="object-items {item_class}">{items}</div>'


def _render_element(element: VisualElement, scene_index: int) -> str:
    position_style = ""
    if element.x is not None and element.y is not None:
        position_style = f"left:{element.x}px;top:{element.y}px;"
    value = f'<strong class="object-value">{_escape(element.value)}</strong>' if element.value else ""
    detail = f'<p class="object-detail">{_escape(element.detail)}</p>' if element.detail else ""
    return (
        f'<article id="{_object_id(scene_index, element.id)}" '
        f'class="visual-object kind-{element.kind}" data-object="{_escape(element.id)}" '
        f'style="{position_style}">'
        '<div class="object-heading">'
        f'<span class="object-kind">{_escape(element.kind.replace("_", " "))}</span>'
        f"{value}</div>"
        f'<h3 class="object-label">{_escape(element.label)}</h3>'
        f"{detail}{_render_items(element)}</article>"
    )


def _render_svg_edges(scene: SceneBrief, scene_index: int) -> str:
    if not scene.connections or scene.layout not in ("tree", "graph"):
        return ""
    edges = []
    for conn in scene.connections:
        edge_id = f"edge-{scene_index}-{conn.source}-{conn.target}"
        dash = 'stroke-dasharray="8,4"' if conn.kind == "pointer" else ""
        edges.append(
            f'<path id="{edge_id}" class="scene-edge {conn.kind}" '
            f'd="M 0 0 L 0 0" fill="none" stroke="var(--line)" stroke-width="2" {dash} '
            f'data-from="{conn.source}" data-to="{conn.target}"/>'
        )
    return f'<svg class="edges-layer" aria-hidden="true">{"".join(edges)}</svg>'


def _render_tree(scene: SceneBrief, scene_index: int) -> str:
    nodes = "".join(_render_element(e, scene_index) for e in scene.elements)
    edges = _render_svg_edges(scene, scene_index)
    return f'<div class="visual-stage tree-stage">{edges}{nodes}</div>'


def _render_graph(scene: SceneBrief, scene_index: int) -> str:
    nodes = "".join(_render_element(e, scene_index) for e in scene.elements)
    edges = _render_svg_edges(scene, scene_index)
    return f'<div class="visual-stage graph-stage">{edges}{nodes}</div>'


def _render_array_view(scene: SceneBrief, scene_index: int) -> str:
    cells = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage array-view-stage">{cells}</div>'


def _render_queue_view(scene: SceneBrief, scene_index: int) -> str:
    cells = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage queue-view-stage"><div class="queue-label left">← 入队</div>{cells}<div class="queue-label right">出队 →</div></div>'


def _render_flow(scene: SceneBrief, scene_index: int) -> str:
    parts = []
    labels = {(c.source, c.target): c.label for c in scene.connections}
    for i, e in enumerate(scene.elements):
        parts.append(_render_element(e, scene_index))
        if i < len(scene.elements) - 1:
            next_e = scene.elements[i + 1]
            label = labels.get((e.id, next_e.id), "")
            parts.append(f'<div class="flow-connector"><span>{_escape(label)}</span><i></i></div>')
    return f'<div class="visual-stage flow-stage">{"".join(parts)}</div>'


def _render_compare(scene: SceneBrief, scene_index: int) -> str:
    mid = max(1, (len(scene.elements) + 1) // 2)
    left = "".join(_render_element(e, scene_index) for e in scene.elements[:mid])
    right = "".join(_render_element(e, scene_index) for e in scene.elements[mid:])
    return f'<div class="visual-stage compare-stage"><section class="compare-column"><span class="column-index">A</span>{left}</section><div class="versus">VS</div><section class="compare-column"><span class="column-index">B</span>{right}</section></div>'


def _render_stack_layout(scene: SceneBrief, scene_index: int) -> str:
    cells = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage stack-layout-stage"><div class="stack-label top">← 出栈/入栈</div>{cells}</div>'


def _render_standard(scene: SceneBrief, scene_index: int) -> str:
    objects = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage {scene.layout}-stage">{objects}</div>'


def _render_stage(scene: SceneBrief, scene_index: int) -> str:
    if scene.layout == "tree": return _render_tree(scene, scene_index)
    if scene.layout == "graph": return _render_graph(scene, scene_index)
    if scene.layout == "array_view": return _render_array_view(scene, scene_index)
    if scene.layout == "queue_view": return _render_queue_view(scene, scene_index)
    if scene.layout == "flow": return _render_flow(scene, scene_index)
    if scene.layout == "compare": return _render_compare(scene, scene_index)
    if scene.layout == "stack": return _render_stack_layout(scene, scene_index)
    return _render_standard(scene, scene_index)


def _caption_groups(scene: SceneBrief) -> list:
    groups, current = [], []
    punct = set("，。！？；：,.!?;:")
    for i, w in enumerate(scene.words):
        current.append((i, w))
        cc = sum(len(x.text) for _, x in current)
        em = current[-1][1].end_ms - current[0][1].start_ms
        if w.text[-1:] in punct or cc >= 18 or em >= 2600:
            groups.append(current)
            current = []
    if current: groups.append(current)
    return groups


def _render_captions(scene: SceneBrief, scene_index: int) -> str:
    cues = []
    for ci, grp in enumerate(_caption_groups(scene)):
        words = "".join(f'<span id="caption-{scene_index}-{wi}" class="caption-word">{_escape(w.text)}</span>' for wi, w in grp)
        cues.append(f'<div id="caption-cue-{scene_index}-{ci}" class="caption-cue">{words}</div>')
    return f'<div class="captions" aria-hidden="true">{"".join(cues)}</div>'


def _render_scene(scene: SceneBrief, si: int, sc: int, req: CartoonVideoRequest) -> str:
    callout = f'<aside class="scene-callout"><span>关键结论</span><strong>{_escape(scene.callout)}</strong></aside>' if scene.callout and req.visuals != "clean" else ""
    prog = round((si + 1) / sc * 100, 2)
    ta = "".join(f'<i id="transfer-{si}-{ci}" class="transfer-pulse"></i>' for ci, c in enumerate(scene.cues) if c.action == "transfer")
    return (
        f'<section id="scene-{si}" class="scene clip layout-{scene.layout}" '
        f'data-start="{_seconds(scene.start_time)}" data-duration="{_seconds(scene.duration)}" data-track-index="0">'
        '<div class="scene-shell"><header class="scene-header">'
        f'<div><span class="scene-role">{_escape(scene.role)}</span><h2 id="scene-title-{si}">{_escape(scene.title)}</h2></div>'
        f'<span class="scene-number">{si + 1:02d} / {sc:02d}</span></header>'
        f"{_render_stage(scene, si)}{callout}{ta}"
        '<footer class="scene-footer"><span>ANIMATED EXPLAINER</span>'
        f'<div class="progress-track"><i style="width:{prog}%"></i></div></footer>'
        f"{_render_captions(scene, si)}</div></section>"
    )


def _render_audio(scene: SceneBrief, si: int) -> str:
    if not scene.audio_path: return ""
    ad = max(0.1, scene.duration - 0.35)
    return f'<audio id="scene-audio-{si}" data-start="{_seconds(scene.start_time)}" data-duration="{_seconds(ad)}" data-track-index="1" data-volume="1" src="{_escape(scene.audio_path)}"></audio>'


def _find_keyword_time(scene: SceneBrief, keyword: str) -> float | None:
    nk = "".join(keyword.split())
    if not nk or not scene.words: return None
    joined, offsets = "", []
    for w in scene.words:
        nw = "".join(w.text.split())
        s = len(joined)
        joined += nw
        offsets.append((s, len(joined), w.start_ms))
    pos = joined.find(nk)
    if pos < 0: return None
    for s, e, sm in offsets:
        if s <= pos < e: return sm / 1000
    return None


def _cue_time(scene: SceneBrief, cue: AnimationCue, idx: int) -> float:
    kt = _find_keyword_time(scene, cue.keyword)
    if kt is not None: return scene.start_time + max(0.25, kt)
    usable = max(0.8, scene.duration - 1.0)
    return scene.start_time + 0.45 + usable * (idx + 1) / (len(scene.cues) + 1)


def _selectors(si: int, cue: AnimationCue) -> str:
    return ", ".join(f'"#{_object_id(si, t)}"' for t in cue.targets)


def _cue_timeline(scene: SceneBrief, si: int, req: CartoonVideoRequest) -> list:
    lines = []
    pc = _PACE_CONFIG.get(req.pace, _PACE_CONFIG["normal"])
    bd, st = pc["duration"], pc["stagger"]
    for ci, cue in enumerate(scene.cues):
        at = _seconds(_cue_time(scene, cue, ci))
        sel = _selectors(si, cue)
        if cue.action == "reveal":
            lines.append(f"tl.fromTo([{sel}], {{autoAlpha:0,y:36,scale:.94}}, {{autoAlpha:1,y:0,scale:1,duration:{bd:.2f},stagger:{st:.2f},ease:'power3.out'}}, {at});")
        elif cue.action == "focus":
            lines.extend([f"tl.to([{sel}], {{scale:1.06,borderColor:'var(--accent)',boxShadow:'0 0 0 4px var(--accent-soft)',duration:.28}}, {at});", f"tl.to([{sel}], {{scale:1,boxShadow:'0 0 0 0 transparent',duration:.4}}, {_seconds(float(at) + 0.75)});"])
        elif cue.action == "transfer":
            p = f"#transfer-{si}-{ci}"
            lines.extend([f'tl.fromTo("{p}", {{autoAlpha:0,xPercent:-220,scale:.5}}, {{autoAlpha:1,xPercent:220,scale:1,duration:.75,ease:"power2.inOut"}}, {at});', f"tl.to([{sel}], {{borderColor:'var(--accent)',duration:.18,stagger:.18}}, {at});"])
        elif cue.action == "compare":
            lines.append(f"tl.fromTo([{sel}], {{y:18,filter:'saturate(.45)'}}, {{y:0,filter:'saturate(1)',borderColor:'var(--accent-two)',duration:.45,stagger:.15}}, {at});")
        elif cue.action == "swap":
            lines.extend([f"tl.to([{sel}], {{x:(i)=>i%2===0?110:-110,y:-18,duration:.45,ease:'power2.inOut'}}, {at});", f"tl.to([{sel}], {{x:0,y:0,duration:.4,ease:'power2.out'}}, {_seconds(float(at) + 0.46)});"])
        elif cue.action == "traverse":
            lines.append(f"tl.fromTo([{sel}], {{backgroundColor:'var(--surface)'}}, {{backgroundColor:'var(--accent-soft)',borderColor:'var(--accent)',duration:.34,stagger:.24}}, {at});")
        elif cue.action == "branch":
            lines.append(f"tl.fromTo([{sel}], {{autoAlpha:0,scale:.7,transformOrigin:'50% 0%'}}, {{autoAlpha:1,scale:1,duration:.5,stagger:.16,ease:'back.out(1.4)'}}, {at});")
        elif cue.action == "state_change":
            lines.append(f"tl.to([{sel}], {{backgroundColor:'var(--accent-soft)',color:'var(--fg)',borderColor:'var(--accent)',duration:.45}}, {at});")
        elif cue.action == "count":
            lines.append(f"tl.fromTo([{sel}], {{scale:.82,autoAlpha:.5}}, {{scale:1,autoAlpha:1,duration:.65,ease:'back.out(1.7)'}}, {at});")
        elif cue.action == "insert":
            d = cue.direction or "top"
            fx = {"left": -120, "right": 120, "top": 0, "bottom": 0}.get(d, 0)
            fy = {"left": 0, "right": 0, "top": -80, "bottom": 80}.get(d, 0)
            lines.append(f"tl.fromTo([{sel}], {{autoAlpha:0,x:{fx},y:{fy},scale:.7}}, {{autoAlpha:1,x:0,y:0,scale:1,duration:{bd:.2f},ease:'back.out(1.4)',stagger:{st:.2f}}}, {at});")
        elif cue.action == "remove":
            d = cue.direction or "left"
            tx = {"left": -120, "right": 120, "top": 0, "bottom": 0}.get(d, 0)
            ty = {"left": 0, "right": 0, "top": -80, "bottom": 80}.get(d, 0)
            lines.append(f"tl.to([{sel}], {{autoAlpha:0,x:{tx},y:{ty},scale:.6,duration:.4,stagger:.12}}, {at});")
        elif cue.action == "highlight_path" and cue.path:
            for i, nid in enumerate(cue.path):
                ns = f'"#{_object_id(si, nid)}"'
                lines.append(f"tl.to({ns}, {{borderColor:'var(--accent)',boxShadow:'0 0 0 4px var(--accent-soft)',duration:.25}}, {_seconds(float(at) + i * 0.3)});")
                if i < len(cue.path) - 1:
                    es = f'"#edge-{si}-{nid}-{cue.path[i+1]}"'
                    lines.append(f"tl.to({es}, {{stroke:'var(--accent)',strokeWidth:3,duration:.2}}, {_seconds(float(at) + i * 0.3 + 0.15)});")
        elif cue.action == "value_change":
            lines.append(f"tl.to([{sel}], {{scale:.85,duration:.15}}, {at});")
            lines.append(f"tl.call(() => {{[{sel}].forEach(el => {{const v = el.querySelector('.object-value');if(v) v.textContent = '{_escape(cue.new_value)}';}});}}, null, {_seconds(float(at) + 0.15)});")
            lines.append(f"tl.to([{sel}], {{scale:1,duration:.2,ease:'back.out(1.7)'}}, {_seconds(float(at) + 0.2)});")
        elif cue.action == "shift":
            lines.append(f"tl.to([{sel}], {{x:-120,duration:.35,ease:'power2.inOut',stagger:.06}}, {at});")
    return lines


def _caption_timeline(scene: SceneBrief, si: int) -> list:
    lines = []
    for ci, grp in enumerate(_caption_groups(scene)):
        fw, lw = grp[0][1], grp[-1][1]
        st = scene.start_time + fw.start_ms / 1000
        en = min(scene.start_time + scene.duration - 0.08, scene.start_time + lw.end_ms / 1000 + 0.12)
        cs = f"#caption-cue-{si}-{ci}"
        lines.append(f'tl.fromTo("{cs}", {{autoAlpha:0,y:14}}, {{autoAlpha:1,y:0,duration:.14}}, {_seconds(st)});')
        for wi, w in grp:
            tr = scene.start_time + w.start_ms / 1000
            lines.append(f'tl.to("#caption-{si}-{wi}", {{color:"var(--caption-active-fg)",backgroundColor:"var(--accent)",scale:1.06,duration:.1}}, {_seconds(tr)});')
        lines.append(f'tl.to("{cs}", {{autoAlpha:0,y:-10,duration:.12}}, {_seconds(en)});')
    return lines


def _build_timeline(brief: VideoBrief, req: CartoonVideoRequest) -> str:
    lines = ['const tl = gsap.timeline({paused:true});', 'window.__timelines = window.__timelines || {};']
    for si, sc in enumerate(brief.scenes):
        lines.append(f'tl.fromTo("#scene-title-{si}", {{autoAlpha:0,y:-22}},{{autoAlpha:1,y:0,duration:.48,ease:"power3.out"}},{_seconds(sc.start_time + 0.12)});')
        if not any(c.action == "reveal" for c in sc.cues):
            os = ", ".join(f'"#{_object_id(si, e.id)}"' for e in sc.elements)
            lines.append(f"tl.fromTo([{os}], {{autoAlpha:0,y:28}},{{autoAlpha:1,y:0,duration:.5,stagger:.1,ease:'power2.out'}},{_seconds(sc.start_time + 0.35)});")
        lines.extend(_cue_timeline(sc, si, req))
        lines.extend(_caption_timeline(sc, si))
    lines.append('window.__timelines["cartoon-explainer"] = tl;')
    return "\n    ".join(lines)


_CSS = """
    :root {
      --bg: THEME_BACKGROUND; --surface: THEME_SURFACE; --surface-strong: THEME_SURFACE_STRONG;
      --fg: THEME_FOREGROUND; --muted: THEME_MUTED; --accent: THEME_ACCENT; --accent-two: THEME_ACCENT_TWO; --line: THEME_LINE;
      --accent-soft: color-mix(in srgb, var(--accent) 17%, transparent); --caption-active-fg: THEME_BACKGROUND;
    }
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: var(--bg); color: var(--fg); font-family: Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif; }
    [data-composition-id] { position: relative; width: 1920px; height: 1080px; overflow: hidden; background: linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px), var(--bg); background-size: 64px 64px; }
    .scene { position: absolute; inset: 0; padding: 54px 72px; }
    .scene-shell { position: relative; width: 100%; height: 100%; padding: 42px 48px 174px; border: 1px solid var(--line); border-radius: 30px; overflow: hidden; background: color-mix(in srgb, var(--bg) 88%, transparent); }
    .scene-shell::before { content: ""; position: absolute; width: 520px; height: 520px; right: -210px; top: -240px; border-radius: 50%; border: 90px solid var(--accent-soft); pointer-events: none; }
    .scene-header { position: relative; z-index: 3; display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 34px; }
    .scene-role, .scene-number, .object-kind, .scene-footer { font-size: 18px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
    .scene-role { color: var(--accent); }
    .scene-header h2 { max-width: 1350px; margin: 10px 0 0; font-size: 54px; line-height: 1.08; letter-spacing: -.035em; }
    .scene-number { color: var(--muted); }
    .visual-stage { position: relative; z-index: 2; display: grid; gap: 22px; min-height: 555px; align-content: center; }
    .visual-object { position: relative; min-width: 0; padding: 24px 26px; border: 2px solid var(--line); border-radius: 20px; background: var(--surface); box-shadow: 0 16px 40px color-mix(in srgb, var(--fg) 8%, transparent); }
    .object-heading { display: flex; justify-content: space-between; gap: 16px; }
    .object-kind { color: var(--muted); font-size: 14px; }
    .object-value { color: var(--accent); font-size: 28px; line-height: 1; }
    .object-label { margin: 14px 0 0; font-size: 28px; line-height: 1.15; }
    .object-detail { margin: 10px 0 0; color: var(--muted); font-size: 20px; line-height: 1.45; }
    .object-items { display: flex; gap: 8px; margin-top: 18px; }
    .object-items.vertical { flex-direction: column-reverse; }
    .object-items.code-lines { flex-direction: column; font-family: "SFMono-Regular", Consolas, monospace; }
    .object-item { flex: 1; min-width: 0; padding: 10px 12px; border-radius: 10px; background: var(--surface-strong); text-align: center; font-size: 18px; font-weight: 750; }
    .object-items.code-lines .object-item { text-align: left; color: var(--accent); }
    .kind-tree_node, .kind-graph_node { min-width: 80px; min-height: 80px; border-radius: 50%; display: grid; place-items: center; font-size: 32px; font-weight: 800; }
    .kind-cell { min-width: 70px; min-height: 70px; border-radius: 12px; position: relative; }
    .kind-cell::before { content: attr(data-index); position: absolute; top: -22px; left: 50%; transform: translateX(-50%); font-size: 14px; color: var(--muted); font-weight: 600; }
    .kind-pointer { min-width: 40px; min-height: 40px; border: 3px dashed var(--accent); background: transparent; }
    .edges-layer { position: absolute; inset: 0; pointer-events: none; z-index: 1; }
    .scene-edge { stroke-linecap: round; stroke-linejoin: round; }
    .scene-edge.pointer { stroke-dasharray: 8 4; }
    .tree-stage, .graph-stage { display: block; }
    .tree-stage .visual-object, .graph-stage .visual-object { position: absolute; }
    .array-view-stage, .queue-view-stage { display: flex; flex-direction: row; gap: 16px; justify-content: center; align-items: center; }
    .queue-label { font-size: 16px; font-weight: 700; color: var(--muted); padding: 8px 16px; border-radius: 8px; background: var(--surface-strong); }
    .queue-label.left { border-top-left-radius: 0; border-bottom-left-radius: 0; }
    .queue-label.right { border-top-right-radius: 0; border-bottom-right-radius: 0; }
    .stack-layout-stage { display: flex; flex-direction: column-reverse; gap: 12px; justify-content: center; align-items: center; }
    .stack-label { font-size: 16px; font-weight: 700; color: var(--muted); padding: 8px 16px; border-radius: 8px; background: var(--surface-strong); }
    .flow-stage { grid-template-columns: repeat(11, auto); align-items: center; }
    .flow-stage .visual-object { min-width: 220px; }
    .flow-connector { min-width: 72px; display: grid; place-items: center; gap: 7px; color: var(--muted); }
    .flow-connector span { min-height: 22px; font-size: 14px; white-space: nowrap; }
    .flow-connector i { position: relative; width: 100%; height: 3px; background: var(--accent); }
    .flow-connector i::after { content: ""; position: absolute; right: -1px; top: -5px; width: 10px; height: 10px; border-top: 3px solid var(--accent); border-right: 3px solid var(--accent); transform: rotate(45deg); }
    .compare-stage { grid-template-columns: 1fr 84px 1fr; align-items: stretch; }
    .compare-column { position: relative; display: grid; gap: 18px; align-content: center; padding: 26px; border: 1px solid var(--line); border-radius: 24px; background: color-mix(in srgb, var(--surface) 68%, transparent); }
    .column-index { position: absolute; top: -20px; left: 26px; display: grid; place-items: center; width: 48px; height: 48px; border-radius: 50%; background: var(--accent); color: var(--caption-active-fg); font-weight: 900; }
    .versus { align-self: center; text-align: center; color: var(--accent-two); font-size: 28px; font-weight: 950; }
    .stack-stage { grid-template-columns: 1fr; max-width: 1180px; width: 100%; margin: auto; }
    .stack-stage .visual-object { padding: 18px 28px; }
    .code-stage { grid-template-columns: minmax(0, 1.4fr) minmax(300px, .6fr); }
    .grid-stage, .recap-stage { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .hero-stage { grid-template-columns: minmax(0, 1.4fr) minmax(280px, .6fr); }
    .hero-stage .visual-object:first-child { padding: 46px; border-color: var(--accent); background: linear-gradient(135deg, var(--surface), var(--accent-soft)); }
    .hero-stage .visual-object:first-child .object-label { font-size: 44px; }
    .kind-metric .object-value, .kind-formula .object-label { font-size: 40px; color: var(--accent); }
    .kind-code { font-family: "SFMono-Regular", Consolas, monospace; }
    .scene-callout { position: absolute; z-index: 4; right: 48px; bottom: 118px; max-width: 690px; display: flex; align-items: center; gap: 16px; padding: 14px 20px; border-left: 5px solid var(--accent-two); background: var(--surface); border-radius: 10px; }
    .scene-callout span { color: var(--accent-two); font-size: 14px; font-weight: 850; }
    .scene-callout strong { font-size: 20px; }
    .scene-footer { position: absolute; z-index: 4; left: 48px; right: 48px; bottom: 72px; display: flex; align-items: center; gap: 24px; color: var(--muted); font-size: 13px; }
    .progress-track { flex: 1; height: 4px; overflow: hidden; border-radius: 999px; background: var(--line); }
    .progress-track i { display: block; height: 100%; background: var(--accent); }
    .captions { position: absolute; z-index: 20; left: 50%; bottom: 12px; width: 1550px; height: 58px; transform: translateX(-50%); text-align: center; pointer-events: none; }
    .caption-cue { position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); padding: 10px 22px; border: 1px solid var(--line); border-radius: 12px; background: color-mix(in srgb, var(--bg) 92%, transparent); color: var(--fg); font-size: 30px; font-weight: 800; line-height: 1.3; white-space: nowrap; opacity: 0; }
    .caption-word { display: inline-block; padding: 0 .08em; border-radius: .2em; }
    .transfer-pulse { position: absolute; z-index: 8; left: 50%; top: 52%; width: 20px; height: 20px; border: 5px solid var(--bg); border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 12px var(--accent-soft); opacity: 0; }
"""


class CartoonCompiler:
    def compile(self, request: CartoonVideoRequest, brief: VideoBrief) -> str:
        theme = _THEMES[request.style]
        css = _CSS.replace("THEME_BACKGROUND", theme.background).replace("THEME_SURFACE_STRONG", theme.surface_strong).replace("THEME_SURFACE", theme.surface).replace("THEME_FOREGROUND", theme.foreground).replace("THEME_MUTED", theme.muted).replace("THEME_ACCENT_TWO", theme.accent_two).replace("THEME_ACCENT", theme.accent).replace("THEME_LINE", theme.line)
        scenes = "\n    ".join(_render_scene(s, i, len(brief.scenes), request) for i, s in enumerate(brief.scenes))
        audio = "\n    ".join(_render_audio(s, i) for i, s in enumerate(brief.scenes) if s.audio_path)
        timeline = _build_timeline(brief, request)
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(brief.title)}</title>
  <style>{css}</style>
</head>
<body>
  <main data-composition-id="cartoon-explainer" data-start="0" data-duration="{_seconds(brief.total_duration)}" data-width="1920" data-height="1080" data-fps="30">
    {scenes}
    {audio}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <script>
    {timeline}
  </script>
</body>
</html>
"""

    @staticmethod
    def theme_name(style: str) -> str:
        return _THEMES.get(style, _THEMES["diagram"]).name
