"""Compile semantic teaching scenes into a composition-led HyperFrames video."""

from __future__ import annotations

import html
import json
import math
from collections import defaultdict
from pathlib import Path

from app.shared.cartoon.schemas import CompositionPlan, TeachingLesson, VisualKind


COMPOSITION_ID = "cartoon-learning-studio"
SCENE_TRACK_INDEX = 0
AUDIO_TRACK_INDEX = 10
CAPTION_TRACK_INDEX = 20
_CONNECTED_KINDS = {VisualKind.MODEL, VisualKind.TREE, VisualKind.FLOW, VisualKind.STATE, VisualKind.MEMORY, VisualKind.NETWORK}


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}".rstrip("0").rstrip(".")


def _item_html(item, *, diagram: bool = False, position: tuple[float, float] | None = None) -> str:
    detail = f'<span class="diagram-detail">{html.escape(item.detail)}</span>' if item.detail else '<span class="diagram-detail"></span>'
    value = f'<em class="diagram-value">{html.escape(item.value)}</em>' if item.value else '<em class="diagram-value"></em>'
    classes = f"visual-item semantic-{item.role.value} tone-{item.tone}"
    style = ""
    if diagram and position:
        classes += " diagram-node"
        style = f' style="--x:{position[0]:.2f}%;--y:{position[1]:.2f}%"'
    return f'<article class="{classes}" data-item-id="{html.escape(item.id, quote=True)}" data-item-role="{item.role.value}"{style}><b class="diagram-label">{html.escape(item.label)}</b>{detail}{value}</article>'


def _tree_positions(items, edges) -> dict[str, tuple[float, float]]:
    item_ids = [item.id for item in items]
    children: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        children[edge.source_id].append(edge.target_id)
    child_ids = {edge.target_id for edge in edges}
    roots = [item_id for item_id in item_ids if item_id not in child_ids]
    pending = [(root, 0) for root in roots]
    seen: set[str] = set()
    levels: list[list[str]] = []
    while pending:
        node, depth = pending.pop(0)
        if node in seen:
            continue
        seen.add(node)
        while len(levels) <= depth:
            levels.append([])
        levels[depth].append(node)
        pending.extend((child, depth + 1) for child in children[node])
    for item_id in item_ids:
        if item_id not in seen:
            if not levels:
                levels.append([])
            levels[0].append(item_id)
    positions: dict[str, tuple[float, float]] = {}
    level_count = max(1, len(levels))
    for level_index, nodes in enumerate(levels):
        for node_index, node_id in enumerate(nodes):
            positions[node_id] = (100 * (node_index + 1) / (len(nodes) + 1), 14 + 72 * level_index / max(1, level_count - 1))
    return positions


def _diagram_positions(kind: VisualKind, items, edges) -> dict[str, tuple[float, float]]:
    if kind == VisualKind.TREE:
        return _tree_positions(items, edges)
    count = len(items)
    if kind == VisualKind.FLOW:
        return {item.id: (100 * (index + 1) / (count + 1), 50) for index, item in enumerate(items)}
    if kind == VisualKind.MEMORY:
        return {item.id: (50, 13 + 74 * index / max(1, count - 1)) for index, item in enumerate(items)}
    if kind == VisualKind.NETWORK:
        center = items[0]
        positions = {center.id: (50, 50)}
        for index, item in enumerate(items[1:]):
            angle = -math.pi / 2 + 2 * math.pi * index / max(1, count - 1)
            positions[item.id] = (50 + 36 * math.cos(angle), 50 + 34 * math.sin(angle))
        return positions
    if kind == VisualKind.MODEL:
        return _model_positions(items, edges)
    return {
        item.id: (50 + 35 * math.cos(-math.pi / 2 + 2 * math.pi * index / count), 50 + 34 * math.sin(-math.pi / 2 + 2 * math.pi * index / count))
        for index, item in enumerate(items)
    }


def _model_positions(items, edges) -> dict[str, tuple[float, float]]:
    """Lay out an arbitrary course model from its declared relationships.

    This is deliberately topology-driven. It never branches on course terms,
    which keeps the renderer reusable while preserving the declared model.
    """

    item_ids = [item.id for item in items]
    children: dict[str, list[str]] = defaultdict(list)
    incoming: set[str] = set()
    for edge in edges:
        children[edge.source_id].append(edge.target_id)
        incoming.add(edge.target_id)
    roots = [item_id for item_id in item_ids if item_id not in incoming]
    pending = roots or item_ids[:1]
    levels: list[list[str]] = []
    seen: set[str] = set()
    while pending:
        level = [item_id for item_id in pending if item_id not in seen]
        if not level:
            break
        levels.append(level)
        seen.update(level)
        pending = [child for item_id in level for child in children[item_id] if child not in seen]
    for item_id in item_ids:
        if item_id not in seen:
            levels.append([item_id])
    positions: dict[str, tuple[float, float]] = {}
    width = max(1, len(levels))
    for column, level in enumerate(levels):
        for row, item_id in enumerate(level):
            positions[item_id] = (12 + 76 * column / max(1, width - 1), 50 if len(level) == 1 else 16 + 68 * row / (len(level) - 1))
    return positions


def _edge_html(edge, positions: dict[str, tuple[float, float]], marker_id: str) -> str:
    source = positions[edge.source_id]
    target = positions[edge.target_id]
    label = ""
    if edge.label:
        label = f'<text x="{(source[0] + target[0]) / 2:.2f}" y="{(source[1] + target[1]) / 2 - 2:.2f}">{html.escape(edge.label)}</text>'
    return f'<g class="diagram-edge tone-{edge.tone}" data-edge-id="{html.escape(edge.id, quote=True)}" data-edge-target="{html.escape(edge.target_id, quote=True)}"><line x1="{source[0]:.2f}" y1="{source[1]:.2f}" x2="{target[0]:.2f}" y2="{target[1]:.2f}" marker-end="url(#{marker_id})"/>{label}</g>'


def _diagram_frame_html(visual, items, edges, marker_id: str) -> str:
    positions = _diagram_positions(visual.kind, items, edges)
    connectors = "".join(_edge_html(edge, positions, marker_id) for edge in edges)
    nodes = "".join(_item_html(item, diagram=True, position=positions[item.id]) for item in items)
    return f'<div class="diagram-frame" style="position:absolute;inset:0"><svg class="diagram-links" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><defs><marker id="{marker_id}" markerWidth="5" markerHeight="5" refX="4.2" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z"/></marker></defs>{connectors}</svg>{nodes}</div>'


def _state_items(visual, state):
    item_by_id = {item.id: item for item in visual.items}
    return [item_by_id[state_item.id].model_copy(update=state_item.model_dump(exclude={"id"}, exclude_none=True)) for state_item in state.items]


def _dynamic_diagram_html(scene) -> str:
    visual = scene.visual
    first_state = visual.states[0]
    first_items = _state_items(visual, first_state)
    first_positions = _diagram_positions(visual.kind, first_items, first_state.edges)
    fallback_positions = _diagram_positions(visual.kind, visual.items, visual.edges or first_state.edges)
    nodes = "".join(
        _item_html(
            next((item for item in first_items if item.id == source_item.id), source_item),
            diagram=True,
            position=first_positions.get(source_item.id, fallback_positions[source_item.id]),
        )
        for source_item in visual.items
    )
    marker_id = f"arrow-{scene.id}"
    edge_groups = "".join(
        f'<g class="diagram-edge-state" data-model-state="{html.escape(state.id, quote=True)}">'
        + "".join(_edge_html(edge, _diagram_positions(visual.kind, _state_items(visual, state), state.edges), marker_id) for edge in state.edges)
        + "</g>"
        for state in visual.states
    )
    initial_annotation = visual.states[0].annotation
    caption = f'<p class="visual-caption">{html.escape(visual.caption)}</p>' if visual.caption else ""
    return f'<div class="diagram-shell visual-{visual.kind.value}" data-model-scene="{html.escape(scene.id, quote=True)}"><div class="model-state-annotation" data-model-annotation>{html.escape(initial_annotation)}</div><div class="diagram-frame" style="position:absolute;inset:0"><svg class="diagram-links" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><defs><marker id="{marker_id}" markerWidth="5" markerHeight="5" refX="4.2" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 z"/></marker></defs>{edge_groups}</svg>{nodes}<span class="motion-signal" aria-hidden="true"></span></div>{caption}</div>'


def _diagram_html(scene) -> str:
    visual = scene.visual
    if visual.states:
        return _dynamic_diagram_html(scene)
    marker_id = f"arrow-{scene.id}"
    frames = _diagram_frame_html(visual, visual.items, visual.edges, marker_id)
    caption = f'<p class="visual-caption">{html.escape(visual.caption)}</p>' if visual.caption else ""
    return f'<div class="diagram-shell visual-{visual.kind.value}">{frames}<span class="motion-signal" aria-hidden="true"></span>{caption}</div>'


def _grid_html(visual) -> str:
    if visual.kind == VisualKind.CODE:
        extra = f'<pre class="code-panel"><code>{html.escape(visual.code)}</code></pre>'
    elif visual.kind == VisualKind.FORMULA:
        extra = f'<div class="formula-panel">{html.escape(visual.formula)}</div>'
    else:
        extra = ""
    if visual.kind == VisualKind.COMPARISON:
        midpoint = max(1, len(visual.items) // 2)
        items = "".join(_item_html(item) for item in visual.items[:midpoint])
        items += '<div class="comparison-divider">对照</div>'
        items += "".join(_item_html(item) for item in visual.items[midpoint:])
    else:
        items = "".join(_item_html(item) for item in visual.items)
    caption = f'<p class="visual-caption">{html.escape(visual.caption)}</p>' if visual.caption else ""
    return f'<div class="grid-shell visual-{visual.kind.value}">{extra}<div class="visual-grid">{items}</div>{caption}</div>'


def _stage_html(scene) -> str:
    visual = scene.visual
    content = _diagram_html(scene) if visual.kind in _CONNECTED_KINDS else _grid_html(visual)
    return f'<section class="scene-stage scene-stage-{visual.kind.value}">{content}</section>'


def _scene_html(timed_scene, total: int, course: str) -> str:
    scene = timed_scene.scene
    step_chips = "".join(f'<span data-step-chip="{html.escape(step.step.id, quote=True)}">{html.escape(step.step.focus)}</span>' for step in timed_scene.steps)
    return f'''<section id="scene-{html.escape(scene.id, quote=True)}" class="scene clip layout-{scene.layout.value}" data-scene-id="{html.escape(scene.id, quote=True)}" data-start="{_seconds(timed_scene.start_ms)}" data-duration="{_seconds(timed_scene.duration_ms)}" data-track-index="{SCENE_TRACK_INDEX}">
      <header class="scene-header"><div><p>{html.escape(course)}</p><span class="scene-function">{html.escape(scene.teaching_function.value)}</span><h1>{html.escape(scene.title)}</h1><strong>{html.escape(scene.objective)}</strong></div><span>{timed_scene.index + 1:02d} / {total:02d}</span></header>
      <div class="scene-body">{_stage_html(scene)}<div class="scene-principle"><span>本幕结论</span><strong>{html.escape(scene.takeaway)}</strong><div class="step-rail">{step_chips}</div></div></div>
    </section>'''


def _audio_html(plan: CompositionPlan) -> str:
    clips = [
        step
        for scene in plan.scenes
        for step in scene.steps
    ]
    return "".join(
        f'<audio id="audio-{html.escape(step.scene_id, quote=True)}-{html.escape(step.step.id, quote=True)}" data-start="{_seconds(step.start_ms)}" data-duration="{_seconds(step.audio_duration_ms)}" data-track-index="{AUDIO_TRACK_INDEX}" data-volume="1" src="{html.escape(step.audio_src, quote=True)}"></audio>'
        for step in clips
    )


def _captions_html(plan: CompositionPlan) -> str:
    captions = [
        step
        for scene in plan.scenes
        for step in scene.steps
    ]
    return "".join(
        f'<div id="caption-{html.escape(step.scene_id, quote=True)}-{html.escape(step.step.id, quote=True)}" class="caption clip" data-slot="caption" data-start="{_seconds(step.start_ms)}" data-duration="{_seconds(max(120, step.duration_ms - 80))}" data-track-index="{CAPTION_TRACK_INDEX}"><span>{html.escape(step.step.narration)}</span></div>'
        for step in captions
    )


def _targets(scene_id: str, target_ids: list[str]) -> str:
    selectors: list[str] = []
    for target_id in target_ids:
        prefix = f'[data-scene-id="{scene_id}"]'
        selectors.extend([
            f'{prefix} [data-item-id="{target_id}"]',
            f'{prefix} .diagram-links > [data-edge-id][data-edge-target="{target_id}"]',
            f'{prefix} [data-model-state][data-active="true"] [data-edge-target="{target_id}"]',
        ])
    return ", ".join(repr(selector) for selector in selectors)


def _diagram_runtime(lesson: TeachingLesson) -> str:
    """Emit the generic model-state player used by every dynamic diagram.

    The payload carries only lesson data.  The JavaScript understands stable
    objects, relationships and snapshots; it has no subject, algorithm or
    course-name branches. This keeps one renderer usable across courses,
    visual grammars and teaching mechanisms.
    """

    payload: dict[str, dict[str, dict[str, object]]] = {}
    for scene in lesson.scenes:
        visual = scene.visual
        if not visual.states:
            continue
        scene_states: dict[str, dict[str, object]] = {}
        for state in visual.states:
            items = _state_items(visual, state)
            positions = _diagram_positions(visual.kind, items, state.edges)
            scene_states[state.id] = {
                "items": {
                    item.id: {
                        "label": item.label,
                        "detail": item.detail,
                        "value": item.value,
                        "tone": item.tone,
                        "role": item.role.value,
                        "x": positions[item.id][0],
                        "y": positions[item.id][1],
                    }
                    for item in items
                },
                "annotation": state.annotation,
                "focusIds": state.focus_item_ids,
            }
        payload[scene.id] = scene_states
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'''const __diagramStates={encoded};
window.__applyDiagramState=function(sceneId,stateId,animated){{
  const sceneStates=__diagramStates[sceneId];
  const state=sceneStates&&sceneStates[stateId];
  const root=document.querySelector('[data-model-scene="'+sceneId+'"]');
  if(!state||!root) return;
  const duration=animated ? .46 : 0;
  const focusedIds=new Set(state.focusIds||[]);
  const annotation=root.querySelector('[data-model-annotation]');
  if(annotation){{
    annotation.textContent=state.annotation||'';
    if(animated) gsap.fromTo(annotation,{{autoAlpha:0,y:10}},{{autoAlpha:1,y:0,duration:.3,ease:'power2.out',overwrite:'auto'}});
  }}
  root.querySelectorAll('[data-item-id]').forEach(function(node){{
    const item=state.items[node.dataset.itemId];
    if(!item){{
      if(animated) gsap.to(node,{{autoAlpha:0,scale:.68,duration:.22,ease:'power2.in'}});
      else gsap.set(node,{{autoAlpha:0,scale:.68}});
      return;
    }}
    const updateText=function(){{
      node.querySelector('.diagram-label').textContent=item.label;
      node.querySelector('.diagram-detail').textContent=item.detail;
      node.querySelector('.diagram-value').textContent=item.value;
      node.dataset.itemRole=item.role;
      node.className='visual-item semantic-'+item.role+' tone-'+item.tone+' diagram-node';
    }};
    updateText();
    const focused=focusedIds.has(node.dataset.itemId);
    const target={{left:item.x+'%',top:item.y+'%',autoAlpha:focused ? 1 : .38,scale:focused ? 1.08 : .94,duration:duration,ease:'power3.inOut',overwrite:'auto'}};
    node.dataset.focused=focused?'true':'false';
    if(animated){{
      gsap.to(node,target);
      gsap.fromTo(node,{{scale:.84}},{{scale:1,duration:.36,ease:'back.out(1.6)',overwrite:'auto'}});
    }} else gsap.set(node,target);
  }});
  root.querySelectorAll('[data-model-state]').forEach(function(group){{
    const active=group.dataset.modelState===stateId;
    group.dataset.active=active?'true':'false';
    if(animated) gsap.to(group,{{autoAlpha:active ? .5 : 0,duration:active ? .36 : .18,ease:'power2.out',overwrite:'auto'}});
    else gsap.set(group,{{autoAlpha:active ? .22 : 0}});
  }});
}};'''


def _motion_runtime() -> str:
    """Run route-based teaching signals over the semantic model itself."""

    return r'''window.__playModelPath=function(sceneId,itemIds,duration){
  const scene=document.querySelector('[data-scene-id="'+sceneId+'"]');
  if(!scene||!itemIds||itemIds.length<2) return;
  const shell=scene.querySelector('.diagram-shell');
  const signal=shell&&shell.querySelector('.motion-signal');
  if(!shell||!signal) return;
  const shellRect=shell.getBoundingClientRect();
  const nodes=itemIds.map(function(itemId){return shell.querySelector('[data-item-id="'+itemId+'"]').getBoundingClientRect();});
  if(nodes.some(function(rect){return !rect.width||!rect.height;})) return;
  const points=nodes.map(function(rect){return {left:(rect.left-shellRect.left+rect.width/2),top:(rect.top-shellRect.top+rect.height/2)}});
  gsap.killTweensOf(signal);
  gsap.set(signal,{left:points[0].left,top:points[0].top,autoAlpha:1,scale:.65});
  const leg=Math.max(.22,duration/Math.max(1,points.length-1));
  const keyframes=points.slice(1).map(function(point){return {left:point.left,top:point.top,duration:leg,ease:'power2.inOut'};});
  gsap.to(signal,{keyframes:keyframes,onComplete:function(){gsap.to(signal,{autoAlpha:0,scale:.35,duration:.22});}});
  itemIds.forEach(function(itemId,index){
    const node=shell.querySelector('[data-item-id="'+itemId+'"]');
    if(node) gsap.fromTo(node,{scale:.96},{scale:1.12,duration:.18,delay:index*leg,yoyo:true,repeat:1,ease:'power2.out',overwrite:'auto'});
  });
};'''


def _timeline(plan: CompositionPlan) -> str:
    lines = [
        "const sceneEls = document.querySelectorAll('.scene');",
        "gsap.set(sceneEls, { autoAlpha: 0 });",
        (
            "tl.fromTo('[data-progress-fill]', { scaleX: 0 }, "
            f"{{ scaleX: 1, duration: {_seconds(plan.total_duration_ms)}, "
            "ease: 'none', transformOrigin: 'left center' }, 0);"
        ),
    ]
    for timed_scene in plan.scenes:
        scene_id = timed_scene.scene.id
        start = _seconds(timed_scene.start_ms)
        end = _seconds(timed_scene.start_ms + timed_scene.duration_ms - 240)
        hard_kill_at = _seconds(timed_scene.start_ms + timed_scene.duration_ms)
        scene_selector = f'[data-scene-id="{scene_id}"]'
        visual_selector = f'{scene_selector} [data-item-id], {scene_selector} [data-edge-id]'
        lines.extend([
            f"tl.set('{scene_selector}', {{ autoAlpha: 1 }}, {start});",
            f"tl.from('{scene_selector} .scene-header > *', {{ y: 28, autoAlpha: 0, duration: .5, stagger: .08, ease: 'power3.out' }}, {start});",
            f"tl.from('{scene_selector} .scene-stage', {{ scale: .95, autoAlpha: 0, duration: .58, ease: 'power3.out' }}, {_seconds(timed_scene.start_ms + 160)});",
            f"tl.set('{visual_selector}', {{ autoAlpha: .2 }}, {_seconds(timed_scene.start_ms + 260)});",
        ])
        for step_index, timed_step in enumerate(timed_scene.steps):
            if timed_step.step.state_id:
                should_animate = "true" if step_index else "false"
                lines.append(f"tl.call(function(){{window.__applyDiagramState('{scene_id}','{timed_step.step.state_id}',{should_animate});}}, [], {_seconds(timed_step.start_ms)});")
            for timed_motion in timed_step.motions:
                targets = _targets(scene_id, timed_motion.motion.target_ids)
                at = _seconds(timed_motion.start_ms)
                duration = _seconds(timed_motion.duration_ms)
                kind = timed_motion.motion.kind.value
                if kind == "reveal":
                    lines.append(f"tl.to([{targets}], {{ autoAlpha: 1, scale: 1, y: 0, duration: {duration}, stagger: .1, ease: 'power3.out' }}, {at});")
                elif kind in {"transfer", "traverse"}:
                    route = json.dumps(timed_motion.motion.path_ids, ensure_ascii=False)
                    lines.append(f"tl.call(function(){{window.__playModelPath('{scene_id}',{route},{duration});}}, [], {at});")
                    lines.append(f"tl.to([{targets}], {{ autoAlpha: 1, duration: .18, stagger: .08, ease: 'power2.out' }}, {at});")
                elif kind == "compare":
                    lines.append(f"tl.to([{targets}], {{ autoAlpha: 1, scale: 1.08, backgroundColor: '#fff1d6', duration: .28, stagger: .1, yoyo: true, repeat: 1 }}, {at});")
                elif kind == "transform":
                    lines.append(f"tl.to([{targets}], {{ autoAlpha: 1, rotate: 2, scale: 1.1, duration: .3, yoyo: true, repeat: 1, ease: 'power2.inOut' }}, {at});")
                else:
                    lines.append(f"tl.to([{targets}], {{ autoAlpha: 1, scale: 1.075, duration: .26, stagger: .08, yoyo: true, repeat: 1, ease: 'power2.out' }}, {at});")
        lines.extend([f"tl.from('{scene_selector} .scene-principle', {{ y: 16, autoAlpha: 0, duration: .42, ease: 'power3.out' }}, {_seconds(timed_scene.start_ms + 620)});", f"tl.to('{scene_selector}', {{ autoAlpha: 0, duration: .24 }}, {end});", f"tl.set('{scene_selector}', {{ autoAlpha: 0 }}, {hard_kill_at});"])
    lines.append(f"tl.to({{}}, {{ duration: {_seconds(plan.total_duration_ms)} }}, 0);")
    return "\n".join(lines)


_CSS = r'''
@font-face{font-family:"PingFang SC";src:local("PingFang SC")}@font-face{font-family:"Microsoft YaHei";src:local("Microsoft YaHei")}:root{--ink:#101828;--slate:#46556d;--line:#dbe4ee;--paper:#f7f9fc;--blue:#2563eb;--mint:#0f9f8d;--amber:#e78b19;--violet:#7557d9;--coral:#df4f5f}*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;background:var(--paper);color:var(--ink);font-family:Arial,"PingFang SC","Microsoft YaHei",sans-serif}main[data-composition-id]{position:relative;width:1920px;height:1080px;overflow:hidden}.composition-background{position:absolute;inset:0;background:linear-gradient(132deg,#f9fbff 0%,#eef4ff 50%,#f7fcfb 100%)}.composition-background:before{content:"";position:absolute;width:980px;height:980px;right:-420px;top:-440px;border:1px solid #c7dcff;border-radius:50%;box-shadow:0 0 0 90px rgba(210,228,255,.2),0 0 0 210px rgba(223,238,255,.16)}.scene{position:absolute;inset:0;padding:66px 92px 48px}.scene-header{position:relative;z-index:2;display:grid;grid-template-columns:1fr auto;column-gap:32px;align-items:end}.scene-header p{grid-column:1;margin:0 0 12px;color:var(--blue);font-size:17px;font-weight:800;letter-spacing:.12em}.scene-header h1{grid-column:1;margin:0;max-width:1260px;font-size:56px;line-height:1.05;letter-spacing:-.045em}.scene-header span{grid-column:2;grid-row:1/3;align-self:start;padding:10px 0 10px 24px;border-left:1px solid #b9c7dd;color:#61718a;font-size:18px;font-weight:800;letter-spacing:.15em}.scene-body{position:relative;height:814px}.scene-stage{position:absolute;inset:74px 0 68px;border:1px solid rgba(193,207,227,.9);border-radius:36px;background:rgba(255,255,255,.74);box-shadow:0 22px 70px rgba(41,77,128,.09);overflow:hidden}.scene-stage:before{content:"";position:absolute;inset:0;background:linear-gradient(125deg,transparent 46%,rgba(219,235,255,.32));pointer-events:none}.scene-note{position:absolute;z-index:3;left:38px;bottom:0;width:475px;padding:24px 28px;border:1px solid #d6e2f1;border-radius:22px;background:rgba(255,255,255,.92);box-shadow:0 16px 38px rgba(41,77,128,.1)}.scene-note>p{margin:0 0 10px;color:var(--blue);font-size:14px;font-weight:900;letter-spacing:.12em}.scene-note h2{margin:0;font-size:27px;line-height:1.3;letter-spacing:-.025em}.step-rail{display:flex;flex-wrap:wrap;gap:8px;margin-top:17px}.step-rail span{padding:7px 10px;border-radius:999px;background:#edf4ff;color:#50627e;font-size:13px;line-height:1.2}.scene-footer{position:absolute;right:92px;bottom:28px;max-width:760px;color:#697a93;font-size:16px;text-align:right}.scene-footer span{padding-bottom:8px;border-bottom:1px solid #c9d5e5}.diagram-shell{position:relative;width:100%;height:100%;min-height:550px}.diagram-links{position:absolute;inset:7% 6%;width:88%;height:86%;overflow:visible}.diagram-edge line{stroke:currentColor;stroke-width:.38;stroke-linecap:round;opacity:.72}.diagram-edge path{fill:currentColor}.diagram-edge text{fill:currentColor;font-size:2.25px;font-weight:700;text-anchor:middle}.diagram-node{position:absolute;left:var(--x);top:var(--y);width:166px;min-height:110px;padding:15px 16px;transform:translate(-50%,-50%);border:2px solid currentColor;border-radius:18px;background:rgba(255,255,255,.97);box-shadow:0 13px 28px rgba(23,47,88,.12);text-align:center}.visual-tree .diagram-node{width:122px;min-height:122px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:13px}.visual-tree .diagram-node b{font-size:22px}.visual-flow .diagram-node{border-radius:999px;min-height:86px}.visual-memory .diagram-node{width:250px;border-radius:13px;text-align:left}.visual-network .diagram-node:first-of-type{width:180px;min-height:180px;border-radius:50%;display:flex;flex-direction:column;justify-content:center}.visual-item b{display:block;font-size:18px;line-height:1.22}.visual-item span{display:block;margin-top:7px;color:var(--slate);font-size:13px;line-height:1.35}.visual-item em{display:block;margin-top:8px;font-size:18px;font-style:normal;font-weight:900}.tone-ink{color:#172238}.tone-blue{color:var(--blue)}.tone-mint{color:var(--mint)}.tone-amber{color:var(--amber)}.tone-violet{color:var(--violet)}.tone-coral{color:var(--coral)}.visual-caption{position:absolute;left:50%;bottom:22px;transform:translateX(-50%);margin:0;padding:8px 14px;border-radius:999px;background:rgba(255,255,255,.82);color:#667892;font-size:14px;white-space:nowrap}.grid-shell{position:relative;display:flex;flex-direction:column;justify-content:center;width:100%;height:100%;padding:56px 66px}.visual-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:18px}.grid-shell .visual-item{min-height:132px;padding:20px;border:1px solid currentColor;border-radius:20px;background:#fff;box-shadow:0 10px 24px rgba(26,55,99,.08)}.visual-metrics .visual-item{min-height:150px;border-top-width:6px}.visual-comparison .visual-grid{grid-template-columns:1fr 56px 1fr;align-items:center}.visual-comparison .visual-item{min-height:105px}.comparison-divider{color:var(--coral);font-size:17px;font-weight:900;text-align:center;letter-spacing:.08em}.code-panel,.formula-panel{margin:0 0 22px;padding:24px 28px;border-radius:22px;background:#10223c;color:#e0edff;font-family:Menlo,Monaco,monospace;font-size:18px;line-height:1.6;white-space:pre-wrap}.formula-panel{background:linear-gradient(135deg,#f1edff,#fbfaff);color:#5c41ba;font-family:Arial,"PingFang SC",sans-serif;font-size:38px;font-weight:900;text-align:center}.layout-hero .scene-stage{inset:68px 190px 110px}.layout-hero .scene-note{left:calc(50% - 330px);width:660px;bottom:12px;text-align:center}.layout-hero .step-rail{justify-content:center}.layout-hero .diagram-shell{min-height:410px}.layout-concept_map .scene-note,.layout-system_map .scene-note{left:auto;right:32px;bottom:34px}.layout-process_lane .scene-stage{inset:92px 0 104px}.layout-process_lane .scene-note{left:calc(50% - 430px);width:860px;bottom:10px}.layout-state_lab .scene-note{bottom:28px}.layout-comparison_board .scene-stage,.layout-formula_lab .scene-stage{inset:90px 74px 96px}.layout-comparison_board .scene-note,.layout-formula_lab .scene-note{left:calc(50% - 360px);width:720px;bottom:8px;text-align:center}.layout-comparison_board .step-rail,.layout-formula_lab .step-rail{justify-content:center}.layout-recap .scene-stage{inset:96px 340px 120px}.layout-recap .scene-note{width:370px;left:auto;right:64px;bottom:92px}.caption{position:absolute;z-index:10;bottom:34px;left:430px;right:430px;text-align:center;pointer-events:none}.caption span{display:inline-block;max-width:1060px;padding:14px 24px;border-radius:14px;background:#081830;color:white;font-size:22px;line-height:1.42;box-shadow:0 12px 28px rgba(0,0,0,.18)}[data-slot="progress"]{position:absolute;z-index:12;bottom:0;left:0;width:100%;height:7px;background:#dfe8f6}[data-progress-fill]{display:block;width:100%;height:100%;background:linear-gradient(90deg,var(--mint),var(--blue))}
'''

_CSS += r'''
.scene{padding:54px 86px 42px}.scene-header{min-height:144px;align-items:start}.scene-header>div{position:relative;padding-left:26px;border-left:4px solid var(--blue)}.scene-header p{display:inline-block;margin:0 14px 14px 0;font-size:15px;letter-spacing:.1em}.scene-header .scene-function{display:inline-block;position:static;padding:6px 10px;border:0;border-radius:999px;background:#e8f0ff;color:#2459d9;font-size:13px;letter-spacing:.08em;text-transform:uppercase}.scene-header h1{max-width:1340px;font-size:52px;line-height:1.08}.scene-header strong{display:block;max-width:1080px;margin-top:12px;color:#53647c;font-size:19px;font-weight:600;line-height:1.4}.scene-header>span{padding-top:12px;font-size:17px}.scene-body{height:840px}.scene-stage{inset:26px 0 142px;border-radius:30px;background:rgba(255,255,255,.82);box-shadow:0 18px 46px rgba(41,77,128,.1)}.scene-stage:before{background:linear-gradient(135deg,rgba(238,247,255,.68),transparent 42%,rgba(230,250,244,.42))}.scene-principle{position:absolute;left:0;right:0;bottom:56px;display:grid;grid-template-columns:118px minmax(0,1fr) auto;gap:18px;align-items:center;min-height:58px;padding:12px 20px;border-top:1px solid #d9e5f1;border-bottom:1px solid #d9e5f1;background:rgba(250,253,255,.85)}.scene-principle>span{color:var(--blue);font-size:13px;font-weight:900;letter-spacing:.1em}.scene-principle>strong{font-size:18px;line-height:1.35}.step-rail{justify-content:flex-end;gap:6px;margin:0}.step-rail span{padding:6px 9px;background:#eaf3ff;color:#486582;font-size:12px}.diagram-shell{min-height:0;padding:76px 28px 28px}.diagram-links{inset:13% 7% 10%;width:86%;height:77%}.diagram-node{width:188px;min-height:116px;padding:16px 18px;border-width:2px;border-radius:20px;box-shadow:0 16px 30px rgba(23,47,88,.14)}.diagram-node[data-focused="true"]{box-shadow:0 18px 42px rgba(37,99,235,.28)}.visual-tree .diagram-node{width:132px;min-height:132px}.visual-flow .diagram-node{width:184px;min-height:92px}.visual-memory .diagram-node{width:280px}.visual-network .diagram-node:first-of-type{width:196px;min-height:196px}.visual-item b{font-size:19px}.visual-item span{font-size:14px}.diagram-edge line{stroke-width:.5;opacity:.86}.diagram-edge text{font-size:2.5px}.diagram-edge-state{pointer-events:none}.diagram-edge-state[data-active="true"] .diagram-edge line{stroke-width:.7;opacity:1}.model-state-annotation{position:absolute;z-index:4;top:22px;left:28px;right:28px;max-width:830px;padding:10px 14px;border-left:4px solid var(--mint);border-radius:0 12px 12px 0;background:rgba(239,252,248,.92);color:#147867;font-size:17px;font-weight:800;line-height:1.35}.motion-signal{position:absolute;z-index:8;width:22px;height:22px;margin:-11px;border:4px solid #fff;border-radius:50%;background:var(--amber);box-shadow:0 0 0 8px rgba(231,139,25,.18),0 6px 16px rgba(126,72,10,.34);opacity:0}.visual-caption{bottom:18px;z-index:5}.grid-shell{padding:78px 66px 52px}.visual-grid{gap:24px}.grid-shell .visual-item{min-height:154px;padding:24px;border-radius:22px}.visual-comparison .visual-grid{grid-template-columns:1fr 68px 1fr}.code-panel,.formula-panel{margin-bottom:24px;padding:30px 34px}.formula-panel{font-size:42px}.layout-hero .scene-stage{inset:34px 130px 150px}.layout-hero .diagram-shell{padding-top:64px}.layout-hero .scene-principle{left:130px;right:130px}.layout-process_lane .scene-stage{inset:36px 0 146px}.layout-process_lane .visual-flow .diagram-node{width:205px}.layout-state_lab .scene-stage{inset:20px 64px 132px;border-color:#b8d5f4;background:linear-gradient(130deg,#fafdff,#f3f8ff)}.layout-state_lab .model-state-annotation{background:#e6f4ff;border-left-color:var(--blue)}.layout-system_map .scene-stage{inset:24px 36px 138px}.layout-comparison_board .scene-stage,.layout-formula_lab .scene-stage{inset:34px 74px 148px}.layout-recap .scene-stage{inset:32px 210px 156px}.layout-recap .grid-shell{padding:78px 70px 48px}.layout-recap .scene-principle{left:210px;right:210px}.caption{bottom:32px;left:300px;right:300px;min-height:72px;display:flex;align-items:flex-end;justify-content:center}.caption span{max-width:1240px;padding:13px 24px;border-radius:13px;background:#081830;font-size:21px;line-height:1.38}[data-slot="progress"]{height:6px}
'''


class CartoonCompiler:
    def compile(self, lesson: TeachingLesson, plan: CompositionPlan) -> str:
        if len(lesson.scenes) != len(plan.scenes):
            raise ValueError("lesson and composition scene counts differ")
        self._validate_plan(plan)
        return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1920, height=1080"><title>{html.escape(lesson.title, quote=True)}</title><style>{_CSS}</style></head><body><main id="root" data-composition-id="{COMPOSITION_ID}" data-start="0" data-duration="{_seconds(plan.total_duration_ms)}" data-width="1920" data-height="1080"><div class="composition-background" aria-hidden="true"></div>{"".join(_scene_html(scene, len(plan.scenes), lesson.course) for scene in plan.scenes)}{_captions_html(plan)}{_audio_html(plan)}<footer data-slot="progress"><span data-progress-fill></span></footer></main><script src="assets/vendor/gsap.min.js"></script><script>{_diagram_runtime(lesson)}{_motion_runtime()}window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});{_timeline(plan)}window.__timelines['{COMPOSITION_ID}']=tl;</script></body></html>'''

    def write(self, lesson: TeachingLesson, plan: CompositionPlan, output_dir: Path) -> Path:
        self._validate_audio_assets(
            plan,
            output_dir,
        )
        path = output_dir / "index.html"
        path.write_text(self.compile(lesson, plan), encoding="utf-8")
        return path

    @staticmethod
    def _validate_plan(plan: CompositionPlan) -> None:
        previous_scene_end = 0

        for expected_index, scene in enumerate(plan.scenes):
            if scene.index != expected_index:
                raise ValueError("composition scene indexes must be contiguous")

            if scene.start_ms < previous_scene_end:
                raise ValueError("composition scenes overlap")

            scene_end = scene.start_ms + scene.duration_ms
            previous_step_end = scene.start_ms

            for step in scene.steps:
                if step.scene_id != scene.scene.id:
                    raise ValueError("timed step belongs to a different scene")

                if step.start_ms < previous_step_end:
                    raise ValueError("composition steps overlap")

                step_end = step.start_ms + step.duration_ms
                if step.start_ms < scene.start_ms or step_end > scene_end:
                    raise ValueError("timed step escapes its scene")

                for motion in step.motions:
                    motion_end = motion.start_ms + motion.duration_ms
                    if motion.start_ms < step.start_ms or motion_end > step_end:
                        raise ValueError("timed motion escapes its teaching step")

                previous_step_end = step_end

            previous_scene_end = scene_end

        if previous_scene_end != plan.total_duration_ms:
            raise ValueError("composition duration does not match its final scene")

    @staticmethod
    def _validate_audio_assets(plan: CompositionPlan, output_dir: Path) -> None:
        root = output_dir.resolve()

        for scene in plan.scenes:
            for step in scene.steps:
                source = Path(step.audio_src)

                if source.is_absolute():
                    raise ValueError("audio source must be relative to the composition")

                resolved = (root / source).resolve()

                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise ValueError("audio source escapes the composition") from exc

                if not resolved.is_file() or resolved.stat().st_size <= 0:
                    raise ValueError(f"audio source is missing or empty: {source.as_posix()}")
