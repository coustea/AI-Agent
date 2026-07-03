"""Compile a structured teaching storyboard into deterministic HyperFrames HTML."""

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
}


def _object_id(scene_index: int, object_id: str) -> str:
    return f"s{scene_index}-{object_id}"


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
    value = (
        f'<strong class="object-value">{_escape(element.value)}</strong>'
        if element.value
        else ""
    )
    detail = (
        f'<p class="object-detail">{_escape(element.detail)}</p>'
        if element.detail
        else ""
    )
    return (
        f'<article id="{_object_id(scene_index, element.id)}" '
        f'class="visual-object kind-{element.kind}" data-object="{_escape(element.id)}">'
        '<div class="object-heading">'
        f'<span class="object-kind">{_escape(element.kind.replace("_", " "))}</span>'
        f"{value}"
        "</div>"
        f'<h3 class="object-label">{_escape(element.label)}</h3>'
        f"{detail}{_render_items(element)}"
        "</article>"
    )


def _render_flow(scene: SceneBrief, scene_index: int) -> str:
    parts: list[str] = []
    labels = {
        (connection.source, connection.target): connection.label
        for connection in scene.connections
    }
    for index, element in enumerate(scene.elements):
        parts.append(_render_element(element, scene_index))
        if index < len(scene.elements) - 1:
            next_element = scene.elements[index + 1]
            label = labels.get((element.id, next_element.id), "")
            parts.append(
                '<div class="flow-connector" aria-hidden="true">'
                f'<span>{_escape(label)}</span><i></i>'
                "</div>"
            )
    return f'<div class="visual-stage flow-stage">{"".join(parts)}</div>'


def _render_compare(scene: SceneBrief, scene_index: int) -> str:
    midpoint = max(1, (len(scene.elements) + 1) // 2)
    left = "".join(
        _render_element(element, scene_index)
        for element in scene.elements[:midpoint]
    )
    right = "".join(
        _render_element(element, scene_index)
        for element in scene.elements[midpoint:]
    )
    return (
        '<div class="visual-stage compare-stage">'
        f'<section class="compare-column"><span class="column-index">A</span>{left}</section>'
        '<div class="versus">VS</div>'
        f'<section class="compare-column"><span class="column-index">B</span>{right}</section>'
        "</div>"
    )


def _render_tree(scene: SceneBrief, scene_index: int) -> str:
    nodes = "".join(
        _render_element(element, scene_index)
        for element in scene.elements
    )
    edges = "".join(
        '<div class="relation-chip">'
        f'<b>{_escape(connection.source)}</b><i>→</i>'
        f'<b>{_escape(connection.target)}</b>'
        f'<span>{_escape(connection.label)}</span>'
        "</div>"
        for connection in scene.connections
    )
    return (
        '<div class="visual-stage tree-stage">'
        f'<div class="tree-nodes">{nodes}</div>'
        f'<div class="relation-row">{edges}</div>'
        "</div>"
    )


def _render_standard(scene: SceneBrief, scene_index: int) -> str:
    objects = "".join(
        _render_element(element, scene_index)
        for element in scene.elements
    )
    return (
        f'<div class="visual-stage {scene.layout}-stage">{objects}</div>'
    )


def _render_stage(scene: SceneBrief, scene_index: int) -> str:
    if scene.layout == "flow":
        return _render_flow(scene, scene_index)
    if scene.layout == "compare":
        return _render_compare(scene, scene_index)
    if scene.layout == "tree":
        return _render_tree(scene, scene_index)
    return _render_standard(scene, scene_index)


def _caption_groups(scene: SceneBrief) -> list[list[tuple[int, object]]]:
    groups: list[list[tuple[int, object]]] = []
    current: list[tuple[int, object]] = []
    punctuation = set("，。！？；：,.!?;:")
    for index, word in enumerate(scene.words):
        current.append((index, word))
        char_count = sum(len(item.text) for _, item in current)
        elapsed_ms = current[-1][1].end_ms - current[0][1].start_ms
        if word.text[-1:] in punctuation or char_count >= 18 or elapsed_ms >= 2600:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _render_captions(scene: SceneBrief, scene_index: int) -> str:
    cues: list[str] = []
    for cue_index, group in enumerate(_caption_groups(scene)):
        words = "".join(
            f'<span id="caption-{scene_index}-{word_index}" class="caption-word">'
            f"{_escape(word.text)}</span>"
            for word_index, word in group
        )
        cues.append(
            f'<div id="caption-cue-{scene_index}-{cue_index}" '
            f'class="caption-cue">{words}</div>'
        )
    return f'<div class="captions" aria-hidden="true">{"".join(cues)}</div>'


def _render_scene(scene: SceneBrief, scene_index: int, scene_count: int) -> str:
    callout = (
        f'<aside class="scene-callout"><span>关键结论</span>'
        f'<strong>{_escape(scene.callout)}</strong></aside>'
        if scene.callout
        else ""
    )
    progress = round((scene_index + 1) / scene_count * 100, 2)
    transfer_assets = "".join(
        f'<i id="transfer-{scene_index}-{cue_index}" class="transfer-pulse"></i>'
        for cue_index, cue in enumerate(scene.cues)
        if cue.action == "transfer"
    )
    return (
        f'<section id="scene-{scene_index}" class="scene clip layout-{scene.layout}" '
        f'data-start="{_seconds(scene.start_time)}" '
        f'data-duration="{_seconds(scene.duration)}" data-track-index="0">'
        '<div class="scene-shell">'
        '<header class="scene-header">'
        f'<div><span class="scene-role">{_escape(scene.role)}</span>'
        f'<h2 id="scene-title-{scene_index}">{_escape(scene.title)}</h2></div>'
        f'<span class="scene-number">{scene_index + 1:02d} / {scene_count:02d}</span>'
        "</header>"
        f"{_render_stage(scene, scene_index)}"
        f"{callout}{transfer_assets}"
        '<footer class="scene-footer">'
        '<span>ANIMATED EXPLAINER</span>'
        f'<div class="progress-track"><i style="width:{progress}%"></i></div>'
        "</footer>"
        f"{_render_captions(scene, scene_index)}"
        "</div></section>"
    )


def _render_audio(scene: SceneBrief, scene_index: int) -> str:
    if not scene.audio_path:
        return ""
    audio_duration = max(0.1, scene.duration - 0.35)
    return (
        f'<audio id="scene-audio-{scene_index}" '
        f'data-start="{_seconds(scene.start_time)}" '
        f'data-duration="{_seconds(audio_duration)}" data-track-index="1" '
        f'data-volume="1" src="{_escape(scene.audio_path)}"></audio>'
    )


def _find_keyword_time(scene: SceneBrief, keyword: str) -> float | None:
    normalized_keyword = "".join(keyword.split())
    if not normalized_keyword or not scene.words:
        return None
    joined = ""
    offsets: list[tuple[int, int, int]] = []
    for word in scene.words:
        normalized_word = "".join(word.text.split())
        start = len(joined)
        joined += normalized_word
        offsets.append((start, len(joined), word.start_ms))
    position = joined.find(normalized_keyword)
    if position < 0:
        return None
    for start, end, start_ms in offsets:
        if start <= position < end:
            return start_ms / 1000
    return None


def _cue_time(scene: SceneBrief, cue: AnimationCue, index: int) -> float:
    keyword_time = _find_keyword_time(scene, cue.keyword)
    if keyword_time is not None:
        return scene.start_time + max(0.25, keyword_time)
    usable = max(0.8, scene.duration - 1.0)
    return scene.start_time + 0.45 + usable * (index + 1) / (len(scene.cues) + 1)


def _selectors(scene_index: int, cue: AnimationCue) -> str:
    return ", ".join(
        f'"#{_object_id(scene_index, target)}"'
        for target in cue.targets
    )


def _cue_timeline(scene: SceneBrief, scene_index: int) -> list[str]:
    lines: list[str] = []
    for cue_index, cue in enumerate(scene.cues):
        at = _seconds(_cue_time(scene, cue, cue_index))
        selectors = _selectors(scene_index, cue)
        if cue.action == "reveal":
            lines.append(
                f"tl.fromTo([{selectors}], "
                '{autoAlpha:0,y:36,scale:.94}, '
                '{autoAlpha:1,y:0,scale:1,duration:.55,stagger:.12,ease:"power3.out"}, '
                f"{at});"
            )
        elif cue.action == "focus":
            lines.extend(
                [
                    f"tl.to([{selectors}], "
                    '{scale:1.06,borderColor:"var(--accent)",'
                    'boxShadow:"0 0 0 4px var(--accent-soft)",duration:.28}, '
                    f"{at});",
                    f"tl.to([{selectors}], "
                    '{scale:1,boxShadow:"0 0 0 0 transparent",duration:.4}, '
                    f"{_seconds(float(at) + 0.75)});",
                ]
            )
        elif cue.action == "transfer":
            pulse = f"#transfer-{scene_index}-{cue_index}"
            lines.extend(
                [
                    f'tl.fromTo("{pulse}", '
                    '{autoAlpha:0,xPercent:-220,scale:.5}, '
                    '{autoAlpha:1,xPercent:220,scale:1,duration:.75,ease:"power2.inOut"}, '
                    f"{at});",
                    f"tl.to([{selectors}], "
                    '{borderColor:"var(--accent)",duration:.18,stagger:.18}, '
                    f"{at});",
                ]
            )
        elif cue.action == "compare":
            lines.append(
                f"tl.fromTo([{selectors}], "
                '{y:18,filter:"saturate(.45)"}, '
                '{y:0,filter:"saturate(1)",borderColor:"var(--accent-two)",'
                'duration:.45,stagger:.15}, '
                f"{at});"
            )
        elif cue.action == "swap":
            lines.extend(
                [
                    f"tl.to([{selectors}], "
                    '{x:(i)=>i%2===0?110:-110,y:-18,duration:.45,ease:"power2.inOut"}, '
                    f"{at});",
                    f"tl.to([{selectors}], "
                    '{x:0,y:0,duration:.4,ease:"power2.out"}, '
                    f"{_seconds(float(at) + 0.46)});",
                ]
            )
        elif cue.action == "traverse":
            lines.append(
                f"tl.fromTo([{selectors}], "
                '{backgroundColor:"var(--surface)"}, '
                '{backgroundColor:"var(--accent-soft)",borderColor:"var(--accent)",'
                'duration:.34,stagger:.24}, '
                f"{at});"
            )
        elif cue.action == "branch":
            lines.append(
                f"tl.fromTo([{selectors}], "
                '{autoAlpha:0,scale:.7,transformOrigin:"50% 0%"}, '
                '{autoAlpha:1,scale:1,duration:.5,stagger:.16,ease:"back.out(1.4)"}, '
                f"{at});"
            )
        elif cue.action == "state_change":
            lines.append(
                f"tl.to([{selectors}], "
                '{backgroundColor:"var(--accent-soft)",color:"var(--fg)",'
                'borderColor:"var(--accent)",duration:.45}, '
                f"{at});"
            )
        elif cue.action == "count":
            lines.append(
                f"tl.fromTo([{selectors}], "
                '{scale:.82,autoAlpha:.5}, '
                '{scale:1,autoAlpha:1,duration:.65,ease:"back.out(1.7)"}, '
                f"{at});"
            )
    return lines


def _caption_timeline(scene: SceneBrief, scene_index: int) -> list[str]:
    lines: list[str] = []
    for cue_index, group in enumerate(_caption_groups(scene)):
        first_word = group[0][1]
        last_word = group[-1][1]
        start = scene.start_time + first_word.start_ms / 1000
        end = min(
            scene.start_time + scene.duration - 0.08,
            scene.start_time + last_word.end_ms / 1000 + 0.12,
        )
        cue_selector = f"#caption-cue-{scene_index}-{cue_index}"
        lines.append(
            f'tl.fromTo("{cue_selector}", {{autoAlpha:0,y:14}}, '
            f'{{autoAlpha:1,y:0,duration:.14}}, {_seconds(start)});'
        )
        for word_index, word in group:
            trigger = scene.start_time + word.start_ms / 1000
            lines.append(
                f'tl.to("#caption-{scene_index}-{word_index}", '
                '{color:"var(--caption-active-fg)",'
                'backgroundColor:"var(--accent)",scale:1.06,duration:.1}, '
                f"{_seconds(trigger)});"
            )
        lines.append(
            f'tl.to("{cue_selector}", {{autoAlpha:0,y:-10,duration:.12}}, '
            f"{_seconds(end)});"
        )
    return lines


def _build_timeline(brief: VideoBrief) -> str:
    lines = [
        'const tl = gsap.timeline({paused:true});',
        'window.__timelines = window.__timelines || {};',
    ]
    for scene_index, scene in enumerate(brief.scenes):
        start = _seconds(scene.start_time + 0.12)
        lines.append(
            f'tl.fromTo("#scene-title-{scene_index}", '
            '{autoAlpha:0,y:-22},'
            '{autoAlpha:1,y:0,duration:.48,ease:"power3.out"},'
            f"{start});"
        )
        if not any(cue.action == "reveal" for cue in scene.cues):
            object_selectors = ", ".join(
                f'"#{_object_id(scene_index, element.id)}"'
                for element in scene.elements
            )
            lines.append(
                f"tl.fromTo([{object_selectors}], "
                '{autoAlpha:0,y:28},'
                '{autoAlpha:1,y:0,duration:.5,stagger:.1,ease:"power2.out"},'
                f"{_seconds(scene.start_time + 0.35)});"
            )
        lines.extend(_cue_timeline(scene, scene_index))
        lines.extend(_caption_timeline(scene, scene_index))
    lines.append('window.__timelines["cartoon-explainer"] = tl;')
    return "\n    ".join(lines)


_CSS = """
    :root {
      --bg: THEME_BACKGROUND;
      --surface: THEME_SURFACE;
      --surface-strong: THEME_SURFACE_STRONG;
      --fg: THEME_FOREGROUND;
      --muted: THEME_MUTED;
      --accent: THEME_ACCENT;
      --accent-two: THEME_ACCENT_TWO;
      --line: THEME_LINE;
      --accent-soft: color-mix(in srgb, var(--accent) 17%, transparent);
      --caption-active-fg: THEME_BACKGROUND;
    }
    * { box-sizing: border-box; }
    html, body {
      width: 100%; height: 100%; margin: 0; overflow: hidden;
      background: var(--bg); color: var(--fg);
      font-family: Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    [data-composition-id] {
      position: relative; width: 1920px; height: 1080px; overflow: hidden;
      background:
        linear-gradient(var(--line) 1px, transparent 1px),
        linear-gradient(90deg, var(--line) 1px, transparent 1px),
        var(--bg);
      background-size: 64px 64px;
    }
    .scene { position: absolute; inset: 0; padding: 54px 72px; }
    .scene-shell {
      position: relative; width: 100%; height: 100%; padding: 42px 48px 174px;
      border: 1px solid var(--line); border-radius: 30px; overflow: hidden;
      background: color-mix(in srgb, var(--bg) 88%, transparent);
    }
    .scene-shell::before {
      content: ""; position: absolute; width: 520px; height: 520px;
      right: -210px; top: -240px; border-radius: 50%;
      border: 90px solid var(--accent-soft); pointer-events: none;
    }
    .scene-header {
      position: relative; z-index: 3; display: flex; justify-content: space-between;
      align-items: flex-start; margin-bottom: 34px;
    }
    .scene-role, .scene-number, .object-kind, .scene-footer {
      font-size: 18px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase;
    }
    .scene-role { color: var(--accent); }
    .scene-header h2 {
      max-width: 1350px; margin: 10px 0 0; font-size: 54px; line-height: 1.08;
      letter-spacing: -.035em;
    }
    .scene-number { color: var(--muted); }
    .visual-stage {
      position: relative; z-index: 2; display: grid; gap: 22px; min-height: 555px;
      align-content: center;
    }
    .visual-object {
      position: relative; min-width: 0; padding: 24px 26px;
      border: 2px solid var(--line); border-radius: 20px;
      background: var(--surface); box-shadow: 0 16px 40px color-mix(in srgb, var(--fg) 8%, transparent);
    }
    .object-heading { display: flex; justify-content: space-between; gap: 16px; }
    .object-kind { color: var(--muted); font-size: 14px; }
    .object-value { color: var(--accent); font-size: 28px; line-height: 1; }
    .object-label { margin: 14px 0 0; font-size: 28px; line-height: 1.15; }
    .object-detail { margin: 10px 0 0; color: var(--muted); font-size: 20px; line-height: 1.45; }
    .object-items { display: flex; gap: 8px; margin-top: 18px; }
    .object-items.vertical { flex-direction: column-reverse; }
    .object-items.code-lines { flex-direction: column; font-family: "SFMono-Regular", Consolas, monospace; }
    .object-item {
      flex: 1; min-width: 0; padding: 10px 12px; border-radius: 10px;
      background: var(--surface-strong); text-align: center; font-size: 18px; font-weight: 750;
    }
    .object-items.code-lines .object-item { text-align: left; color: var(--accent); }
    .flow-stage { grid-template-columns: repeat(11, auto); align-items: center; }
    .flow-stage .visual-object { min-width: 220px; }
    .flow-connector { min-width: 72px; display: grid; place-items: center; gap: 7px; color: var(--muted); }
    .flow-connector span { min-height: 22px; font-size: 14px; white-space: nowrap; }
    .flow-connector i { position: relative; width: 100%; height: 3px; background: var(--accent); }
    .flow-connector i::after {
      content: ""; position: absolute; right: -1px; top: -5px; width: 10px; height: 10px;
      border-top: 3px solid var(--accent); border-right: 3px solid var(--accent); transform: rotate(45deg);
    }
    .compare-stage { grid-template-columns: 1fr 84px 1fr; align-items: stretch; }
    .compare-column {
      position: relative; display: grid; gap: 18px; align-content: center;
      padding: 26px; border: 1px solid var(--line); border-radius: 24px;
      background: color-mix(in srgb, var(--surface) 68%, transparent);
    }
    .column-index {
      position: absolute; top: -20px; left: 26px; display: grid; place-items: center;
      width: 48px; height: 48px; border-radius: 50%; background: var(--accent);
      color: var(--caption-active-fg); font-weight: 900;
    }
    .versus { align-self: center; text-align: center; color: var(--accent-two); font-size: 28px; font-weight: 950; }
    .stack-stage { grid-template-columns: 1fr; max-width: 1180px; width: 100%; margin: auto; }
    .stack-stage .visual-object { padding: 18px 28px; }
    .tree-nodes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; align-items: start; }
    .tree-nodes .visual-object:first-child { grid-column: 2; }
    .relation-row { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin-top: 18px; }
    .relation-chip {
      display: flex; align-items: center; gap: 9px; padding: 9px 14px; border-radius: 999px;
      border: 1px solid var(--line); background: var(--surface); color: var(--muted);
    }
    .relation-chip i { color: var(--accent); font-style: normal; }
    .relation-chip span { padding-left: 6px; border-left: 1px solid var(--line); }
    .code-stage { grid-template-columns: minmax(0, 1.4fr) minmax(300px, .6fr); }
    .grid-stage, .recap-stage { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .hero-stage { grid-template-columns: minmax(0, 1.4fr) minmax(280px, .6fr); }
    .hero-stage .visual-object:first-child {
      padding: 46px; border-color: var(--accent);
      background: linear-gradient(135deg, var(--surface), var(--accent-soft));
    }
    .hero-stage .visual-object:first-child .object-label { font-size: 44px; }
    .kind-metric .object-value, .kind-formula .object-label { font-size: 40px; color: var(--accent); }
    .kind-code { font-family: "SFMono-Regular", Consolas, monospace; }
    .scene-callout {
      position: absolute; z-index: 4; right: 48px; bottom: 118px; max-width: 690px;
      display: flex; align-items: center; gap: 16px; padding: 14px 20px;
      border-left: 5px solid var(--accent-two); background: var(--surface); border-radius: 10px;
    }
    .scene-callout span { color: var(--accent-two); font-size: 14px; font-weight: 850; }
    .scene-callout strong { font-size: 20px; }
    .scene-footer {
      position: absolute; z-index: 4; left: 48px; right: 48px; bottom: 72px;
      display: flex; align-items: center; gap: 24px; color: var(--muted); font-size: 13px;
    }
    .progress-track { flex: 1; height: 4px; overflow: hidden; border-radius: 999px; background: var(--line); }
    .progress-track i { display: block; height: 100%; background: var(--accent); }
    .captions {
      position: absolute; z-index: 20; left: 50%; bottom: 12px; width: 1550px;
      height: 58px; transform: translateX(-50%); text-align: center; pointer-events: none;
    }
    .caption-cue {
      position: absolute; left: 50%; bottom: 0; transform: translateX(-50%);
      padding: 10px 22px; border: 1px solid var(--line); border-radius: 12px;
      background: color-mix(in srgb, var(--bg) 92%, transparent);
      color: var(--fg); font-size: 30px; font-weight: 800; line-height: 1.3;
      white-space: nowrap; opacity: 0;
    }
    .caption-word { display: inline-block; padding: 0 .08em; border-radius: .2em; }
    .transfer-pulse {
      position: absolute; z-index: 8; left: 50%; top: 52%; width: 20px; height: 20px;
      border: 5px solid var(--bg); border-radius: 50%; background: var(--accent);
      box-shadow: 0 0 0 12px var(--accent-soft); opacity: 0;
    }
  """


class CartoonCompiler:
    """Deterministically compile validated semantic objects into one composition."""

    def compile(self, request: CartoonVideoRequest, brief: VideoBrief) -> str:
        theme = _THEMES[request.style]
        css = (
            _CSS.replace("THEME_BACKGROUND", theme.background)
            .replace("THEME_SURFACE_STRONG", theme.surface_strong)
            .replace("THEME_SURFACE", theme.surface)
            .replace("THEME_FOREGROUND", theme.foreground)
            .replace("THEME_MUTED", theme.muted)
            .replace("THEME_ACCENT_TWO", theme.accent_two)
            .replace("THEME_ACCENT", theme.accent)
            .replace("THEME_LINE", theme.line)
        )
        scenes = "\n    ".join(
            _render_scene(scene, index, len(brief.scenes))
            for index, scene in enumerate(brief.scenes)
        )
        audio = "\n    ".join(
            _render_audio(scene, index)
            for index, scene in enumerate(brief.scenes)
            if scene.audio_path
        )
        timeline = _build_timeline(brief)
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(brief.title)}</title>
  <style>{css}</style>
</head>
<body>
  <main data-composition-id="cartoon-explainer" data-start="0"
    data-duration="{_seconds(brief.total_duration)}" data-width="1920"
    data-height="1080" data-fps="30">
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
        return _THEMES[style].name
