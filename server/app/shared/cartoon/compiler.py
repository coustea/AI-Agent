"""Compile a structured teaching storyboard into deterministic HyperFrames HTML.

通用计算机理论知识动画演示编译器。
支持数据结构、算法、数学、数据库、编译原理、操作系统等所有理论课程。
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
        background="#ffffff",
        surface="#f8fafc",
        surface_strong="#f1f5f9",
        foreground="#0f172a",
        muted="#64748b",
        accent="#4f46e5",
        accent_two="#f43f5e",
        line="#e2e8f0",
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
        "table": "table-rows",
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
    """Render SVG edges for tree/graph/state_diagram layouts."""
    if not scene.connections or scene.layout not in ("tree", "graph", "state_diagram"):
        return ""
    edges = []
    for conn in scene.connections:
        edge_id = f"edge-{scene_index}-{conn.source}-{conn.target}"
        if conn.kind == "pointer":
            dash = 'stroke-dasharray="8,4"'
        elif conn.kind == "transition":
            dash = 'stroke-dasharray="6,3"'
        else:
            dash = ""
        # transition 类型添加条件标注
        cond_label = ""
        if conn.kind == "transition" and conn.condition:
            cond_label = f'<text class="edge-condition" data-from="{conn.source}" data-to="{conn.target}">{_escape(conn.condition)}</text>'
        edges.append(
            f'<path id="{edge_id}" class="scene-edge {conn.kind}" '
            f'd="M 0 0 L 0 0" fill="none" stroke="var(--line)" stroke-width="2.5" {dash} '
            f'marker-end="url(#arrow-marker-{scene_index})" '
            f'data-from="{conn.source}" data-to="{conn.target}"/>'
            f"{cond_label}"
        )
    defs = (
        '<defs>'
        f'<marker id="arrow-marker-{scene_index}" viewBox="0 0 10 10" refX="6" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        '<path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="var(--line)" />'
        '</marker>'
        f'<marker id="arrow-marker-active-{scene_index}" viewBox="0 0 10 10" refX="6" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
        '<path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="var(--accent)" />'
        '</marker>'
        '</defs>'
    )
    return f'<svg class="edges-layer" aria-hidden="true">{defs}{"".join(edges)}</svg>'


def _render_tree(scene: SceneBrief, scene_index: int) -> str:
    nodes = "".join(_render_element(e, scene_index) for e in scene.elements if e.kind != "code")
    code_elements = [e for e in scene.elements if e.kind == "code"]
    edges = _render_svg_edges(scene, scene_index)
    if code_elements:
        code_html = "".join(_render_element(e, scene_index) for e in code_elements)
        return f'<div class="split-stage"><div class="visual-stage tree-stage">{edges}{nodes}</div><div class="sidebar-stage">{code_html}</div></div>'
    return f'<div class="visual-stage tree-stage">{edges}{nodes}</div>'


def _render_graph(scene: SceneBrief, scene_index: int) -> str:
    nodes = "".join(_render_element(e, scene_index) for e in scene.elements if e.kind != "code")
    code_elements = [e for e in scene.elements if e.kind == "code"]
    edges = _render_svg_edges(scene, scene_index)
    if code_elements:
        code_html = "".join(_render_element(e, scene_index) for e in code_elements)
        return f'<div class="split-stage"><div class="visual-stage graph-stage">{edges}{nodes}</div><div class="sidebar-stage">{code_html}</div></div>'
    return f'<div class="visual-stage graph-stage">{edges}{nodes}</div>'


def _render_state_diagram(scene: SceneBrief, scene_index: int) -> str:
    nodes = "".join(_render_element(e, scene_index) for e in scene.elements if e.kind != "code")
    code_elements = [e for e in scene.elements if e.kind == "code"]
    edges = _render_svg_edges(scene, scene_index)
    if code_elements:
        code_html = "".join(_render_element(e, scene_index) for e in code_elements)
        return f'<div class="split-stage"><div class="visual-stage state-diagram-stage">{edges}{nodes}</div><div class="sidebar-stage">{code_html}</div></div>'
    return f'<div class="visual-stage state-diagram-stage">{edges}{nodes}</div>'


def _render_array_view(scene: SceneBrief, scene_index: int) -> str:
    cells = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage array-view-stage">{cells}</div>'


def _render_queue_view(scene: SceneBrief, scene_index: int) -> str:
    cells = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage queue-view-stage"><div class="queue-label left">← 入队</div>{cells}<div class="queue-label right">出队 →</div></div>'


def _render_table_view(scene: SceneBrief, scene_index: int) -> str:
    rows = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage table-view-stage">{rows}</div>'


def _render_derivation(scene: SceneBrief, scene_index: int) -> str:
    steps = "".join(_render_element(e, scene_index) for e in scene.elements)
    return f'<div class="visual-stage derivation-stage">{steps}</div>'


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
    if scene.layout == "state_diagram": return _render_state_diagram(scene, scene_index)
    if scene.layout == "array_view": return _render_array_view(scene, scene_index)
    if scene.layout == "queue_view": return _render_queue_view(scene, scene_index)
    if scene.layout == "table_view": return _render_table_view(scene, scene_index)
    if scene.layout == "derivation": return _render_derivation(scene, scene_index)
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
    return (
        f'<section id="scene-{si}" class="scene clip layout-{scene.layout}" '
        f'data-start="{_seconds(scene.start_time)}" data-duration="{_seconds(scene.duration)}" data-track-index="0">'
        '<div class="scene-shell"><header class="scene-header">'
        f'<div><span class="scene-role">{_escape(scene.role)}</span><h2 id="scene-title-{si}">{_escape(scene.title)}</h2></div>'
        f'<span class="scene-number">{si + 1:02d} / {sc:02d}</span></header>'
        f"{_render_stage(scene, si)}{callout}"
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
    return ", ".join(f'"#s{si}-{t}"' for t in cue.targets)


def _cue_timeline(scene: SceneBrief, si: int, req: CartoonVideoRequest) -> list:
    lines = []
    pc = _PACE_CONFIG.get(req.pace, _PACE_CONFIG["normal"])
    bd, st = pc["duration"], pc["stagger"]
    for ci, cue in enumerate(scene.cues):
        at = _seconds(_cue_time(scene, cue, ci))
        sel = _selectors(si, cue)
        if cue.action == "reveal":
            lines.append(f"HF_Animator.reveal(tl, [{sel}], {at}, {bd:.2f}, {st:.2f});")
        elif cue.action == "focus":
            lines.append(f"HF_Animator.focus(tl, [{sel}], {at}, {bd:.2f});")
        elif cue.action == "insert":
            parentId = ""
            for conn in scene.connections:
                if conn.target in cue.targets:
                    parentId = f'"#s{si}-{conn.source}"'
                    break
            p_val = parentId if parentId else "null"
            lines.append(f"HF_Animator.insert(tl, [{sel}], '{cue.direction}', {p_val}, {at}, {bd:.2f}, {st:.2f});")
        elif cue.action == "remove":
            lines.append(f"HF_Animator.remove(tl, [{sel}], '{cue.direction}', {at}, {bd:.2f}, {st:.2f});")
        elif cue.action == "swap":
            lines.append(f"HF_Animator.swap(tl, [{sel}], {at}, {bd:.2f});")
        elif cue.action == "traverse":
            lines.append(f"HF_Animator.traverse(tl, [{sel}], {at}, {bd:.2f}, {st:.2f});")
        elif cue.action == "state_change":
            lines.append(f"HF_Animator.stateChange(tl, [{sel}], {at}, {bd:.2f});")
        elif cue.action == "value_change":
            lines.append(f"HF_Animator.valueChange(tl, [{sel}], '{_escape(cue.new_value)}', {at}, {bd:.2f});")
        elif cue.action == "highlight_path" and cue.path:
            path_list = ", ".join(f"'{n}'" for n in cue.path)
            lines.append(f"HF_Animator.highlightPath(tl, [{path_list}], {si}, {at}, {bd:.2f});")
        elif cue.action == "transfer":
            from_node = cue.targets[0] if len(cue.targets) > 0 else ""
            to_node = cue.targets[1] if len(cue.targets) > 1 else ""
            if from_node and to_node:
                lines.append(f"HF_Animator.transfer(tl, '{from_node}', '{to_node}', {si}, {at}, {bd:.2f});")
            else:
                lines.append(f"HF_Animator.focus(tl, [{sel}], {at}, {bd:.2f});")
        elif cue.action == "branch":
            lines.append(f"HF_Animator.branch(tl, [{sel}], {at}, {bd:.2f}, {st:.2f});")
        elif cue.action == "count":
            lines.append(f"HF_Animator.count(tl, [{sel}], {at}, {bd:.2f});")
        elif cue.action == "shift":
            lines.append(f"HF_Animator.shift(tl, [{sel}], {at}, {bd:.2f}, {st:.2f});")
        elif cue.action == "derive":
            res_val = f'"#s{si}-{cue.result}"' if cue.result else "null"
            lines.append(f"HF_Animator.derive(tl, [{sel}], {res_val}, {at}, {bd:.2f});")
        elif cue.action == "transform":
            res_val = f'"#s{si}-{cue.result}"' if cue.result else "null"
            lines.append(f"HF_Animator.transform(tl, [{sel}], {res_val}, {at}, {bd:.2f});")
        elif cue.action == "highlight_code":
            line_idx = int(cue.new_value) if cue.new_value.isdigit() else 0
            lines.append(f"HF_Animator.highlightCodeLine(tl, [{sel}], {line_idx}, {at}, {bd:.2f});")
    return lines


def _caption_timeline(scene: SceneBrief, si: int) -> list:
    lines = []
    for ci, grp in enumerate(_caption_groups(scene)):
        fw, lw = grp[0][1], grp[-1][1]
        st = scene.start_time + fw.start_ms / 1000
        en = min(scene.start_time + scene.duration - 0.08, scene.start_time + lw.end_ms / 1000 + 0.12)
        cs = f"#caption-cue-{si}-{ci}"
        lines.append(f'tl.fromTo("{cs}", {{autoAlpha:0,y:14}}, {{autoAlpha:1,y:0,duration:.14}}, {_seconds(st)});')
        lines.append(f'tl.to("{cs}", {{autoAlpha:0,y:-10,duration:.12}}, {_seconds(en)});')
    return lines


def _build_timeline(brief: VideoBrief, req: CartoonVideoRequest) -> str:
    lines = [
        'const tl = gsap.timeline({paused:true});',
        'gsap.registerPlugin(MotionPathPlugin);',
        'window.__timelines = window.__timelines || {};'
    ]
    for si, sc in enumerate(brief.scenes):
        lines.append(f'tl.fromTo("#scene-title-{si}", {{autoAlpha:0,y:-22}},{{autoAlpha:1,y:0,duration:.48,ease:"power3.out"}},{_seconds(sc.start_time + 0.12)});')
        
        # Filter out elements that are targets of custom entry animations (insert, reveal, branch, derive, transform)
        entry_targets = set()
        for cue in sc.cues:
            if cue.action in ("reveal", "insert", "branch", "derive", "transform"):
                entry_targets.update(cue.targets)
            if cue.action in ("derive", "transform") and cue.result:
                entry_targets.add(cue.result)
        
        default_reveal_elements = [e for e in sc.elements if e.id not in entry_targets]
        if default_reveal_elements:
            os = ", ".join(f'"#{_object_id(si, e.id)}"' for e in default_reveal_elements)
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
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: var(--bg); color: var(--fg); font-family: Inter, sans-serif; }
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
    .object-items.code-lines { flex-direction: column; font-family: Consolas, monospace; }
    .object-items.table-rows { flex-direction: column; gap: 4px; }
    .object-item { flex: 1; min-width: 0; padding: 10px 12px; border-radius: 10px; background: var(--surface-strong); text-align: center; font-size: 18px; font-weight: 750; }
    .object-items.code-lines .object-item { text-align: left; color: var(--accent); }
    
    .tree-stage .kind-node, .graph-stage .kind-node, .state-diagram-stage .kind-node { min-width: 100px; min-height: 100px; border-radius: 50%; display: grid; place-items: center; font-size: 36px; font-weight: 800; box-shadow: 0 8px 24px rgba(0,0,0,0.06); border-width: 3px; }
    .kind-cell { min-width: 70px; min-height: 70px; border-radius: 12px; position: relative; }
    .kind-cell::before { content: attr(data-index); position: absolute; top: -22px; left: 50%; transform: translateX(-50%); font-size: 14px; color: var(--muted); font-weight: 600; }
    .kind-state { min-width: 100px; min-height: 100px; border-radius: 50%; display: grid; place-items: center; font-size: 26px; font-weight: 800; border-width: 3px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
    .kind-step { border-left: 4px solid var(--accent); border-radius: 12px; padding-left: 20px; }
    .kind-formula .object-label { font-size: 36px; color: var(--accent); font-family: serif; }
    .kind-packet { min-width: 60px; border-radius: 8px; border: 2px dashed var(--accent); background: var(--accent-soft); }
    .kind-table { border-radius: 12px; overflow: hidden; }
    .kind-table .object-items.table-rows .object-item { border-radius: 0; border-bottom: 1px solid var(--line); text-align: left; }
    
    .edges-layer { position: absolute; inset: 0; pointer-events: none; z-index: 1; width: 100%; height: 100%; }
    .scene-edge { stroke-linecap: round; stroke-linejoin: round; transition: stroke 0.25s, stroke-width 0.25s; stroke-width: 3.5px; }
    .scene-edge.pointer { stroke-dasharray: 8 4; }
    .scene-edge.transition { stroke-dasharray: 6 3; stroke: var(--accent-two); }
    .edge-condition { font-size: 16px; fill: var(--accent-two); font-weight: 700; font-family: sans-serif; text-anchor: middle; }
    
    .tree-stage, .graph-stage, .state-diagram-stage { display: block; position: relative; }
    .tree-stage .visual-object, .graph-stage .visual-object, .state-diagram-stage .visual-object { position: absolute; transform: translate(-50%, -50%); }
    .array-view-stage, .queue-view-stage { display: flex; flex-direction: row; gap: 16px; justify-content: center; align-items: center; }
    .queue-label { font-size: 16px; font-weight: 700; color: var(--muted); padding: 8px 16px; border-radius: 8px; background: var(--surface-strong); }
    .queue-label.left { border-top-left-radius: 0; border-bottom-left-radius: 0; }
    .queue-label.right { border-top-right-radius: 0; border-bottom-right-radius: 0; }
    .stack-layout-stage { display: flex; flex-direction: column-reverse; gap: 12px; justify-content: center; align-items: center; }
    .stack-label { font-size: 16px; font-weight: 700; color: var(--muted); padding: 8px 16px; border-radius: 8px; background: var(--surface-strong); }
    .table-view-stage { display: flex; flex-direction: column; gap: 4px; justify-content: center; align-items: center; }
    .derivation-stage { display: flex; flex-direction: column; gap: 28px; justify-content: center; align-items: center; max-width: 1200px; margin: 0 auto; }
    .derivation-stage .visual-object { width: 100%; text-align: center; }
    .derivation-stage .kind-formula { border-left: 4px solid var(--accent); }
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
    .kind-metric .object-value { font-size: 40px; color: var(--accent); }
    .kind-code { background: #0f172a; border-color: #1e293b; color: #cbd5e1; font-family: Consolas, Monaco, monospace; box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
    .kind-code .object-kind { color: #64748b; }
    .kind-code .object-value { color: var(--accent-two); }
    .kind-code .object-label { color: #f8fafc; font-size: 22px; margin-bottom: 12px; }
    .object-items.code-lines .object-item { font-family: Consolas, Monaco, monospace; color: #cbd5e1; text-align: left; background: transparent; padding: 4px 8px; border-radius: 4px; font-size: 16px; font-weight: 500; transition: background 0.2s, border-left 0.2s, color 0.2s; }
    .object-items.code-lines .object-item.highlighted { background: rgba(99, 102, 241, 0.25); color: #ffffff; border-left: 4px solid var(--accent); padding-left: 8px; font-weight: 700; }
    
    .split-stage { display: flex; flex-direction: row; gap: 32px; min-height: 555px; width: 100%; align-items: stretch; }
    .split-stage .visual-stage { flex: 1.2; position: relative; min-height: 555px; border: 2px dashed var(--line); border-radius: 20px; background: color-mix(in srgb, var(--surface) 20%, transparent); overflow: hidden; }
    .split-stage .sidebar-stage { flex: 0.8; display: flex; flex-direction: column; gap: 20px; justify-content: center; }
    .split-stage .sidebar-stage .visual-object { width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; }

    .scene-callout { position: absolute; z-index: 4; right: 48px; bottom: 118px; max-width: 690px; display: flex; align-items: center; gap: 16px; padding: 14px 20px; border-left: 5px solid var(--accent-two); background: var(--surface); border-radius: 10px; }
    .scene-callout span { color: var(--accent-two); font-size: 14px; font-weight: 850; }
    .scene-callout strong { font-size: 20px; }
    .scene-footer { position: absolute; z-index: 4; left: 48px; right: 48px; bottom: 72px; display: flex; align-items: center; gap: 24px; color: var(--muted); font-size: 13px; }
    .progress-track { flex: 1; height: 4px; overflow: hidden; border-radius: 999px; background: var(--line); }
    .progress-track i { display: block; height: 100%; background: var(--accent); }
    .captions { position: absolute; z-index: 20; left: 50%; bottom: 12px; width: 1550px; height: 58px; transform: translateX(-50%); text-align: center; pointer-events: none; }
    .caption-cue { position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); padding: 10px 22px; border: 1px solid var(--line); border-radius: 12px; background: color-mix(in srgb, var(--bg) 92%, transparent); color: var(--fg); font-size: 30px; font-weight: 800; line-height: 1.3; white-space: nowrap; opacity: 0; }
    .caption-word { display: inline-block; padding: 0 .08em; border-radius: .2em; }
    
    .transfer-pulse { position: absolute; z-index: 8; width: 22px; height: 22px; border: 4px solid var(--bg); border-radius: 50%; background: var(--accent-two); box-shadow: 0 0 10px var(--accent-two); opacity: 0; transform: translate(-50%, -50%); }
    .active-particle { animation: pulse-shadow 0.6s infinite alternate; }
    @keyframes pulse-shadow {
      from { box-shadow: 0 0 6px var(--accent-two); }
      to { box-shadow: 0 0 16px var(--accent-two); }
    }
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
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/MotionPathPlugin.min.js"></script>
  <script>
    // === HyperFrames Client-Side Animator and Auto-Layout Engine ===
    window.HF_Animator = {{
      getCenter: (el) => {{
        if (!el) return {{ x: 0, y: 0 }};
        return {{
          x: el.offsetLeft,
          y: el.offsetTop
        }};
      }},
      
      reveal: (tl, targets, startTime, duration, stagger = 0.12) => {{
        tl.fromTo(targets, 
          {{ autoAlpha: 0, y: 30, scale: 0.92 }}, 
          {{ autoAlpha: 1, y: 0, scale: 1, duration: duration, stagger: stagger, ease: "power3.out", immediateRender: false }}, 
          startTime
        );
      }},
      
      focus: (tl, targets, startTime, duration) => {{
        tl.to(targets, {{ scale: 1.08, borderColor: "var(--accent)", boxShadow: "0 0 20px var(--accent-soft)", duration: duration * 0.4, ease: "power2.out" }}, startTime)
          .to(targets, {{ scale: 1, borderColor: "var(--line)", boxShadow: "0 16px 40px rgba(0,0,0,0.08)", duration: duration * 0.6, ease: "power2.inOut" }}, startTime + duration * 0.4);
      }},
      
      insert: (tl, targets, direction, parentId, startTime, duration, stagger = 0.12) => {{
        targets.forEach((targetSel, idx) => {{
          const targetEl = document.querySelector(targetSel);
          const parentEl = parentId ? document.querySelector(parentId) : null;
          let startX = 0, startY = 0;
          
          if (parentEl && targetEl) {{
            const tPos = HF_Animator.getCenter(targetEl);
            const pPos = HF_Animator.getCenter(parentEl);
            startX = pPos.x - tPos.x;
            startY = pPos.y - tPos.y;
          }} else {{
            startX = direction === "left" ? -120 : direction === "right" ? 120 : 0;
            startY = direction === "top" ? -80 : direction === "bottom" ? 80 : 0;
          }}
          
          tl.fromTo(targetSel,
            {{ autoAlpha: 0, x: startX, y: startY, scale: 0.7 }},
            {{ autoAlpha: 1, x: 0, y: 0, scale: 1, duration: duration, ease: "back.out(1.2)", delay: idx * stagger, immediateRender: false }},
            startTime
          );
        }});
      }},
      
      remove: (tl, targets, direction, startTime, duration, stagger = 0.12) => {{
        targets.forEach((targetSel, idx) => {{
          const destX = direction === "left" ? -120 : direction === "right" ? 120 : 0;
          const destY = direction === "top" ? -80 : direction === "bottom" ? 80 : 0;
          
          tl.to(targetSel,
            {{ autoAlpha: 0, x: destX, y: destY, scale: 0.6, duration: duration, ease: "power2.in", delay: idx * stagger }},
            startTime
          );
        }});
      }},
      
      swap: (tl, targets, startTime, duration) => {{
        if (targets.length < 2) return;
        const elA = document.querySelector(targets[0]);
        const elB = document.querySelector(targets[1]);
        if (!elA || !elB) return;
        
        const posA = HF_Animator.getCenter(elA);
        const posB = HF_Animator.getCenter(elB);
        const dx = posB.x - posA.x;
        const dy = posB.y - posA.y;
        
        tl.to(targets[0], {{ x: dx, y: dy, zIndex: 10, duration: duration * 0.5, ease: "power2.inOut" }}, startTime)
          .to(targets[0], {{ x: dx, y: dy, zIndex: 1, duration: duration * 0.5, ease: "power2.out" }}, startTime + duration * 0.5)
          
          .to(targets[1], {{ x: -dx, y: -dy, zIndex: 1, duration: duration * 0.5, ease: "power2.inOut" }}, startTime)
          .to(targets[1], {{ x: -dx, y: -dy, zIndex: 1, duration: duration * 0.5, ease: "power2.out" }}, startTime + duration * 0.5);
      }},
      
      traverse: (tl, targets, startTime, duration, stagger = 0.24) => {{
        targets.forEach((targetSel, idx) => {{
          const t = startTime + idx * stagger;
          tl.to(targetSel, {{ backgroundColor: "var(--accent-soft)", borderColor: "var(--accent)", scale: 1.04, duration: duration * 0.4 }}, t)
            .to(targetSel, {{ backgroundColor: "var(--surface)", borderColor: "var(--line)", scale: 1, duration: duration * 0.6 }}, t + duration * 0.4);
        }});
      }},
      
      stateChange: (tl, targets, startTime, duration) => {{
        tl.to(targets, {{ backgroundColor: "var(--accent-soft)", borderColor: "var(--accent)", color: "var(--fg)", scale: 1.05, duration: duration * 0.5, ease: "power2.out" }}, startTime)
          .to(targets, {{ scale: 1, duration: duration * 0.5, ease: "power2.inOut" }}, startTime + duration * 0.5);
      }},
      
      valueChange: (tl, targets, newValue, startTime, duration) => {{
        targets.forEach(targetSel => {{
          tl.to(targetSel, {{ scale: 0.85, duration: duration * 0.3, ease: "power2.in" }}, startTime)
            .call(() => {{
              const el = document.querySelector(targetSel);
              if (el) {{
                const v = el.querySelector(".object-value");
                if (v) v.textContent = newValue;
              }}
            }}, null, startTime + duration * 0.3)
            .to(targetSel, {{ scale: 1, duration: duration * 0.7, ease: "back.out(1.5)" }}, startTime + duration * 0.3);
        }});
      }},
      
      highlightPath: (tl, pathNodes, sceneIndex, startTime, duration) => {{
        const stepDuration = duration / (pathNodes.length || 1);
        pathNodes.forEach((nodeId, idx) => {{
          const t = startTime + idx * stepDuration;
          const ns = `#s${{sceneIndex}}-${{nodeId}}`;
          tl.to(ns, {{ borderColor: "var(--accent)", boxShadow: "0 0 25px var(--accent-soft)", scale: 1.08, duration: stepDuration * 0.5 }}, t)
            .to(ns, {{ scale: 1, duration: stepDuration * 0.5 }}, t + stepDuration * 0.5);
          
          if (idx < pathNodes.length - 1) {{
            const nextId = pathNodes[idx + 1];
            const es = `#edge-${{sceneIndex}}-${{nodeId}}-${{nextId}}`;
            tl.to(es, {{ stroke: "var(--accent)", strokeWidth: 5, duration: stepDuration }}, t);
            tl.set(es, {{ markerEnd: "url(#arrow-marker-active-" + sceneIndex + ")" }}, t);
          }}
        }});
      }},
      
      highlightCodeLine: (tl, targets, lineIndex, startTime, duration) => {{
        targets.forEach(targetSel => {{
          tl.call(() => {{
            const codeObj = document.querySelector(targetSel);
            if (codeObj) {{
              const lines = codeObj.querySelectorAll(".object-item");
              lines.forEach((line, idx) => {{
                if (idx === lineIndex) {{
                  line.classList.add("highlighted");
                }} else {{
                  line.classList.remove("highlighted");
                }}
              }});
            }}
          }}, null, startTime)
          .to(targetSel, {{ scale: 1.02, duration: 0.15, ease: "power2.out" }}, startTime)
          .to(targetSel, {{ scale: 1, duration: 0.25, ease: "power2.inOut" }}, startTime + 0.15);
        }});
      }},
      
      transfer: (tl, fromNode, toNode, sceneIndex, startTime, duration) => {{
        const particleId = `particle-${{sceneIndex}}-${{fromNode}}-${{toNode}}`;
        const edgeId = `#edge-${{sceneIndex}}-${{fromNode}}-${{toNode}}`;
        
        tl.call(() => {{
          const path = document.querySelector(edgeId);
          const stage = document.querySelector("#scene-" + sceneIndex + " .visual-stage");
          if (path && stage) {{
            const particle = document.createElement("i");
            particle.id = particleId;
            particle.className = "transfer-pulse active-particle";
            stage.appendChild(particle);
            
            gsap.to(particle, {{
              motionPath: {{
                path: path,
                align: path,
                alignOrigin: [0.5, 0.5]
              }},
              autoAlpha: 1,
              duration: duration,
              ease: "power1.inOut",
              onComplete: () => particle.remove()
            }});
          }}
        }}, null, startTime);
      }},
      
      branch: (tl, targets, startTime, duration, stagger = 0.16) => {{
        tl.fromTo(targets, 
          {{ autoAlpha: 0, scale: 0.7, transformOrigin: "50% 0%" }},
          {{ autoAlpha: 1, scale: 1, duration: duration, stagger: stagger, ease: "back.out(1.4)", immediateRender: false }},
          startTime
        );
      }},
      
      count: (tl, targets, startTime, duration) => {{
        tl.fromTo(targets, 
          {{ scale: 0.82, autoAlpha: 0.5 }},
          {{ scale: 1, autoAlpha: 1, duration: duration, ease: "back.out(1.7)", immediateRender: false }},
          startTime
        );
      }},
      
      shift: (tl, targets, startTime, duration, stagger = 0.06) => {{
        tl.to(targets, {{ x: -120, duration: duration, ease: "power2.inOut", stagger: stagger }}, startTime);
      }},
      
      derive: (tl, targets, resultSelector, startTime, duration) => {{
        tl.to(targets, {{ autoAlpha: 0, scale: 0.8, y: -20, duration: duration * 0.5, ease: "power2.in" }}, startTime);
        if (resultSelector) {{
          tl.fromTo(resultSelector,
            {{ autoAlpha: 0, scale: 0.8, y: 20 }},
            {{ autoAlpha: 1, scale: 1, y: 0, duration: duration * 0.5, ease: "back.out(1.4)", immediateRender: false }},
            startTime + duration * 0.5
          );
        }}
      }},
      
      transform: (tl, targets, resultSelector, startTime, duration) => {{
        tl.to(targets, {{ borderColor: "var(--accent-two)", boxShadow: "0 0 15px var(--accent-soft)", duration: duration * 0.3 }}, startTime)
          .to(targets, {{ autoAlpha: 0, scale: 0.6, duration: duration * 0.3, ease: "power2.in" }}, startTime + duration * 0.3);
        if (resultSelector) {{
          tl.fromTo(resultSelector,
            {{ autoAlpha: 0, scale: 0.5, transformOrigin: "50% 50%" }},
            {{ autoAlpha: 1, scale: 1, duration: duration * 0.4, ease: "back.out(1.4)", immediateRender: false }},
            startTime + duration * 0.6
          );
        }}
      }}
    }};

    function updateSvgEdges(stage) {{
      const svgLayer = stage.querySelector(".edges-layer");
      if (!svgLayer) return;
      const paths = svgLayer.querySelectorAll("path");
      
      paths.forEach(path => {{
        const fromId = path.getAttribute("data-from");
        const toId = path.getAttribute("data-to");
        const sceneId = path.id.split("-")[1];
        
        const fromEl = stage.querySelector("#s" + sceneId + "-" + fromId);
        const toEl = stage.querySelector("#s" + sceneId + "-" + toId);
        
        if (fromEl && toEl) {{
          const fromX = fromEl.offsetLeft;
          const fromY = fromEl.offsetTop;
          const toX = toEl.offsetLeft;
          const toY = toEl.offsetTop;
          
          const fromW = fromEl.offsetWidth || 100;
          const toW = toEl.offsetWidth || 100;
          const r1 = fromW / 2;
          const r2 = toW / 2;
          
          const dx = toX - fromX;
          const dy = toY - fromY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          let startX = fromX;
          let startY = fromY;
          let endX = toX;
          let endY = toY;
          
          if (dist > 0) {{
            const ux = dx / dist;
            const uy = dy / dist;
            startX = fromX + r1 * ux;
            startY = fromY + r1 * uy;
            endX = toX - r2 * ux;
            endY = toY - r2 * uy;
          }}
          
          path.setAttribute("d", "M " + startX + " " + startY + " L " + endX + " " + endY);
          
          const textEl = stage.querySelector('.edge-condition[data-from="' + fromId + '"][data-to="' + toId + '"]');
          if (textEl) {{
            textEl.setAttribute("x", (startX + endX) / 2);
            textEl.setAttribute("y", (startY + endY) / 2 - 10);
          }}
        }}
      }});
    }}

    function layoutTree(nodes, edges, width, height) {{
      const nodeMap = new Map(nodes.map(n => [n.getAttribute("data-object"), n]));
      const adj = new Map();
      const inDegree = new Map();
      
      nodes.forEach(n => {{
        const id = n.getAttribute("data-object");
        adj.set(id, []);
        inDegree.set(id, 0);
      }});
      
      edges.forEach(e => {{
        if (nodeMap.has(e.source) && nodeMap.has(e.target)) {{
          adj.get(e.source).push(e.target);
          inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
        }}
      }});
      
      const roots = nodes.filter(n => inDegree.get(n.getAttribute("data-object")) === 0)
                         .map(n => n.getAttribute("data-object"));
      if (roots.length === 0 && nodes.length > 0) {{
        roots.push(nodes[0].getAttribute("data-object"));
      }}
      
      const levels = [];
      function traverse(nodeId, depth) {{
        if (levels.length <= depth) levels.push([]);
        if (!levels[depth].includes(nodeId)) levels[depth].push(nodeId);
        adj.get(nodeId).forEach(childId => traverse(childId, depth + 1));
      }}
      roots.forEach(r => traverse(r, 0));
      
      const levelHeight = height / (levels.length || 1);
      levels.forEach((levelNodes, depth) => {{
        const levelY = 160 + depth * (levelHeight * 0.7);
        const levelWidth = width / (levelNodes.length + 1);
        levelNodes.forEach((nodeId, idx) => {{
          const el = nodeMap.get(nodeId);
          if (el && (!el.style.left || !el.style.top)) {{
            const levelX = (idx + 1) * levelWidth;
            el.style.left = `${{levelX}}px`;
            el.style.top = `${{levelY}}px`;
          }}
        }});
      }});
    }}

    function layoutGraph(nodes, edges, width, height) {{
      const centerX = width / 2;
      const centerY = height / 2 + 30;
      const radius = Math.min(width, height) * 0.32;
      const count = nodes.length;
      nodes.forEach((n, idx) => {{
        if (!n.style.left || !n.style.top) {{
          const angle = (idx * 2 * Math.PI) / count;
          const x = centerX + radius * Math.cos(angle);
          const y = centerY + radius * Math.sin(angle);
          n.style.left = `${{x}}px`;
          n.style.top = `${{y}}px`;
        }}
      }});
    }}

    document.addEventListener("DOMContentLoaded", () => {{
      const stages = document.querySelectorAll(".visual-stage");
      stages.forEach(stage => {{
        const parentComp = stage.closest("[data-composition-id]");
        const stageWidth = stage.clientWidth || (parentComp ? parseInt(parentComp.getAttribute("data-width") || "1920") - 144 : 1776);
        const stageHeight = stage.clientHeight || (parentComp ? parseInt(parentComp.getAttribute("data-height") || "1080") - 300 : 780);
        
        const objects = Array.from(stage.querySelectorAll(".visual-object"));
        const svgLayer = stage.querySelector(".edges-layer");
        
        const edges = [];
        if (svgLayer) {{
          const paths = svgLayer.querySelectorAll("path");
          paths.forEach(path => {{
            edges.push({{
              source: path.getAttribute("data-from"),
              target: path.getAttribute("data-to")
            }});
          }});
        }}
        
        const isTree = stage.classList.contains("tree-stage");
        const isGraph = stage.classList.contains("graph-stage");
        const isState = stage.classList.contains("state-diagram-stage");
        
        const needsLayout = objects.some(el => !el.style.left || !el.style.top);
        if (needsLayout) {{
          if (isTree) {{
            layoutTree(objects, edges, stageWidth, stageHeight);
          }} else if (isGraph || isState) {{
            layoutGraph(objects, edges, stageWidth, stageHeight);
          }}
        }}
        
        updateSvgEdges(stage);
      }});
      
      // Update SVG edges in real-time on every animation tick
      gsap.ticker.add(() => {{
        document.querySelectorAll(".visual-stage").forEach(stage => {{
          updateSvgEdges(stage);
        }});
      }});
    }});

    {timeline}
  </script>
</body>
</html>
"""

    @staticmethod
    def theme_name(style: str) -> str:
        return _THEMES.get(style, _THEMES["diagram"]).name
