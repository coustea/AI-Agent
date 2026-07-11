"""Compile structured teaching scenes into a validated template composition."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from app.shared.cartoon.layouts import layout_scene
from app.shared.cartoon.schemas import CompositionPlan, TeachingLesson, TeachingScene, TeachingStep
from app.shared.cartoon.templates import CartoonTemplate, CartoonTemplateCatalog


COMPOSITION_ID = "cartoon-teaching-video"


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}".rstrip("0").rstrip(".")


def _js(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _stage_nodes(scene: TeachingScene):
    """Return each node that may appear, preserving its state at creation time."""
    nodes = {node.id: node for node in scene.visual_model.nodes}
    for step in scene.steps:
        for patch in step.patches:
            if patch.op == "add_node" and patch.node is not None:
                nodes.setdefault(patch.node.id, patch.node)
    return nodes


def _stage_edges(scene: TeachingScene):
    """Return each edge that may appear so runtime patches can reveal or hide it."""
    edges = {(edge.source_id, edge.target_id, edge.kind, edge.label): edge for edge in scene.visual_model.edges}
    for step in scene.steps:
        for patch in step.patches:
            if patch.edge is not None:
                edge = patch.edge
                edges.setdefault((edge.source_id, edge.target_id, edge.kind, edge.label), edge)
    return list(edges.values())


def _stage_html(scene: TeachingScene) -> str:
    positions = layout_scene(scene)
    initial_nodes = {node.id: node for node in scene.visual_model.nodes}
    initial_edge_keys = {
        (edge.source_id, edge.target_id, edge.kind, edge.label)
        for edge in scene.visual_model.edges
    }
    nodes = _stage_nodes(scene)
    edges = _stage_edges(scene)
    items: list[str] = [f'<svg class="visual-edges" aria-hidden="true">']
    for edge in edges:
        edge_key = (edge.source_id, edge.target_id, edge.kind, edge.label)
        future = " is-future" if edge_key not in initial_edge_keys else ""
        items.append(
            f'<line class="{future.strip()}" data-edge="{html.escape(edge.source_id, quote=True)}:{html.escape(edge.target_id, quote=True)}" '
            f'data-source="{html.escape(edge.source_id, quote=True)}" data-target="{html.escape(edge.target_id, quote=True)}"></line>'
        )
    items.append("</svg>")
    for node_id, node in nodes.items():
        position = positions[node_id]
        initial = initial_nodes.get(node_id)
        display = initial or node
        future = " is-future" if initial is None else ""
        items.append(
            f'<article class="visual-node{future}" data-node="{html.escape(node_id, quote=True)}" data-state="{html.escape(display.state, quote=True)}" '
            f'style="--node-x:{position.x:.2f}%;--node-y:{position.y:.2f}%">'
            f'<strong>{html.escape(display.label, quote=True)}</strong>'
            f'<small>{html.escape(display.detail, quote=True)}</small></article>'
        )
    return "".join(items)


def _scene_html(timed_scene, total_scenes: int, course: str) -> str:
    scene = timed_scene.scene
    chips = "".join(f'<span data-step-chip="{index}">{index + 1:02d}</span>' for index in range(len(scene.steps)))
    return (
        f'<section id="scene-{html.escape(scene.id, quote=True)}" class="teaching-scene clip" data-scene="{html.escape(scene.id, quote=True)}" data-scene-kind="{scene.mode}" '
        f'data-start="{_seconds(timed_scene.start_ms)}" data-duration="{_seconds(timed_scene.duration_ms)}">'
        f'<header data-slot="header"><div class="title-copy"><p>{html.escape(scene.tag or scene.mode, quote=True)}</p><h1>{html.escape(scene.title, quote=True)}</h1><span>{html.escape(scene.objective, quote=True)}</span></div>'
        f'<div class="scene-meta"><b>{timed_scene.index + 1:02d}/{total_scenes:02d}</b><span>{html.escape(course, quote=True)}</span></div></header>'
        f'<div data-slot="stage" data-visual="{scene.visual_model.kind}"><div class="visual-canvas">{_stage_html(scene)}</div></div>'
        f'<aside data-slot="state-rail"><span>步骤</span><div data-step-track>{chips}</div></aside>'
        f'</section>'
    )


def _audio_html(plan: CompositionPlan) -> str:
    result: list[str] = []
    for timed_scene in plan.scenes:
        for timed in timed_scene.steps:
            result.append(f'<audio id="audio-{timed.scene_id}-{timed.step.id}" data-start="{_seconds(timed.start_ms)}" data-duration="{_seconds(timed.audio_duration_ms)}" data-track-index="10" src="{html.escape(timed.audio_src, quote=True)}"></audio>')
    return "".join(result)


def _caption_html(plan: CompositionPlan) -> str:
    result: list[str] = []
    for timed_scene in plan.scenes:
        for timed in timed_scene.steps:
            result.append(f'<div id="caption-{timed.scene_id}-{timed.step.id}" class="caption clip" data-caption="{timed.scene_id}:{timed.step.id}" data-start="{_seconds(timed.start_ms)}" data-duration="{_seconds(timed.duration_ms)}" data-track-index="20"><span>{html.escape(timed.step.narration, quote=True)}</span></div>')
    return "".join(result)


def _timeline(plan: CompositionPlan) -> str:
    lines = ["Runtime.prepare();", f"Runtime.progress(tl, '[data-progress-fill]', 0, {_seconds(plan.total_duration_ms)});"]
    for timed_scene in plan.scenes:
        scene_selector = f'[data-scene="{timed_scene.scene.id}"]'
        lines.append(f"Runtime.sceneIn(tl, {_js(scene_selector)}, {_seconds(timed_scene.start_ms)}, .32);")
        for index, timed in enumerate(timed_scene.steps):
            start = _seconds(timed.start_ms)
            lines.append(f"Runtime.step(tl, {_js(scene_selector)}, {index}, {start});")
            lines.append(f"Runtime.caption(tl, {_js(f'[data-caption=\"{timed.scene_id}:{timed.step.id}\"]')}, {start}, {_seconds(timed.duration_ms)});")
            for action in timed.step.actions:
                payload = {"kind": action.kind, "targets": action.target_ids, "source": action.source_id, "destination": action.destination_id, "duration": action.duration_ms / 1000}
                lines.append(f"Runtime.action(tl, {_js(scene_selector)}, {_js(payload)}, {start});")
            for patch in timed.step.patches:
                lines.append(f"Runtime.patch(tl, {_js(scene_selector)}, {_js(patch.model_dump(mode='json', exclude_none=True))}, {start});")
        lines.append(f"Runtime.sceneOut(tl, {_js(scene_selector)}, {_seconds(timed_scene.start_ms + timed_scene.duration_ms - 260)}, .24);")
    return "\n    ".join(lines)


class CartoonCompiler:
    def __init__(self, *, catalog: CartoonTemplateCatalog | None = None) -> None:
        self.catalog = catalog or CartoonTemplateCatalog()

    def compile(self, lesson: TeachingLesson, plan: CompositionPlan, template: CartoonTemplate) -> str:
        self.catalog.validate_lesson(template, lesson)
        if len(lesson.scenes) != len(plan.scenes):
            raise ValueError("lesson and composition scene counts differ")
        content = template.composition.read_text(encoding="utf-8")
        replacements = {
            "{{ composition_id }}": COMPOSITION_ID,
            "{{ title }}": html.escape(lesson.title, quote=True),
            "{{ duration }}": _seconds(plan.total_duration_ms),
            "{{ scenes_html }}": "".join(_scene_html(scene, len(plan.scenes), lesson.course) for scene in plan.scenes),
            "{{ audio_html }}": _audio_html(plan),
            "{{ captions_html }}": _caption_html(plan),
            "{{ timeline_js }}": _timeline(plan),
        }
        for marker, value in replacements.items():
            content = content.replace(marker, value)
        if re.search(r"\{\{\s*[a-z_]+\s*\}\}", content):
            raise ValueError("template contains unresolved markers")
        return content

    def write(self, lesson: TeachingLesson, plan: CompositionPlan, output_dir: Path, template_id: str) -> tuple[Path, CartoonTemplate]:
        template = self.catalog.get(template_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / "index.html"
        html_path.write_text(self.compile(lesson, plan, template), encoding="utf-8")
        for source in (template.tokens, template.layout, template.motion):
            shutil.copy2(source, output_dir / source.name)
        return html_path, template
