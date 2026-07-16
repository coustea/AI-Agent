"""Compile semantic lesson data into one deterministic HyperFrames composition."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from app.shared.cartoon.models import CartoonBundle, Lesson, Timeline


COMPOSITION_ID = "cartoon-teaching-video"
_ASSET_DIR = Path(__file__).with_name("assets")


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}".rstrip("0").rstrip(".")


def _vtt_time(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


class CartoonComposer:
    """Own HTML structure, layout runtime and the parent caption track."""

    def write(self, lesson: Lesson, timeline: Timeline, output_dir: Path) -> CartoonBundle:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        shutil.copy2(_ASSET_DIR / "runtime.js", assets_dir / "runtime.js")
        shutil.copy2(_ASSET_DIR / "theme.css", assets_dir / "theme.css")

        scene_data_path = output_dir / "scene-data.json"
        caption_path = output_dir / "captions.vtt"
        html_path = output_dir / "index.html"

        payload = self._payload(lesson, timeline)
        scene_data_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        caption_path.write_text(self._captions_vtt(timeline), encoding="utf-8")
        html_path.write_text(self._html(lesson, timeline, payload), encoding="utf-8")
        return CartoonBundle(
            output_dir=output_dir,
            html_path=html_path,
            scene_data_path=scene_data_path,
            caption_path=caption_path,
        )

    @staticmethod
    def _payload(lesson: Lesson, timeline: Timeline) -> dict[str, object]:
        scenes = lesson.model_dump(mode="json")["scenes"]
        beats = timeline.model_dump(mode="json")["beats"]
        captions = timeline.model_dump(mode="json")["captions"]
        return {
            "composition_id": COMPOSITION_ID,
            "title": lesson.title,
            "duration_ms": timeline.duration_ms,
            "scenes": scenes,
            "beats": beats,
            "captions": captions,
        }

    @staticmethod
    def _captions_vtt(timeline: Timeline) -> str:
        lines = ["WEBVTT", ""]
        for index, cue in enumerate(timeline.captions, start=1):
            lines.extend(
                [
                    str(index),
                    f"{_vtt_time(cue.start_ms)} --> {_vtt_time(cue.end_ms)}",
                    cue.text,
                    "",
                ]
            )
        return "\n".join(lines)

    def _html(
        self,
        lesson: Lesson,
        timeline: Timeline,
        payload: dict[str, object],
    ) -> str:
        scenes = "\n".join(
            self._scene_html(index, scene)
            for index, scene in enumerate(lesson.scenes, start=1)
        )
        captions = "\n".join(
            (
                f'<p id="caption-{index}" class="caption-cue" '
                f'data-caption-index="{index}">{html.escape(cue.text)}</p>'
            )
            for index, cue in enumerate(timeline.captions)
        )
        audio = "\n".join(
            (
                f'<audio id="audio-{html.escape(beat.beat_id)}" '
                f'data-start="{_seconds(beat.start_ms)}" '
                f'data-duration="{_seconds(beat.audio_duration_ms or beat.duration_ms)}" '
                'data-track-index="20" data-volume="1" '
                f'src="{html.escape(beat.audio_src)}"></audio>'
            )
            for beat in timeline.beats
        )
        data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>{html.escape(lesson.title)}</title>
  <link rel="stylesheet" href="assets/theme.css">
  <link rel="alternate" type="text/vtt" href="captions.vtt" hreflang="zh-CN">
</head>
<body>
  <main id="root" data-composition-id="{COMPOSITION_ID}" data-start="0"
        data-duration="{_seconds(timeline.duration_ms)}" data-width="1920" data-height="1080">
    <div class="lesson-field" aria-hidden="true"></div>
    {scenes}
    <div id="caption-track" class="caption-track" aria-hidden="true">
      {captions}
    </div>
    <div class="progress-rail" aria-hidden="true"><span id="progress-fill"></span></div>
    {audio}
  </main>
  <script src="assets/vendor/gsap.min.js"></script>
  <script src="assets/runtime.js"></script>
  <script>window.__timelines=window.__timelines||{{}};window.__timelines['{COMPOSITION_ID}']=window.CartoonRuntime.mount({data_json});</script>
</body>
</html>
"""

    @staticmethod
    def _scene_html(index: int, scene: object) -> str:
        scene_id = html.escape(scene.id)
        entities = "\n".join(
            f"""<div id="entity-{scene_id}-{html.escape(entity.id)}"
                 class="visual-entity kind-{entity.kind.value} tone-{entity.tone}"
                 data-entity-id="{html.escape(entity.id)}" data-kind="{entity.kind.value}">
              <span class="entity-label">{html.escape(entity.label)}</span>
              <span class="entity-detail">{html.escape(entity.detail)}</span>
              <span class="entity-value">{html.escape(entity.initial_value)}</span>
            </div>"""
            for entity in scene.entities
        )
        relation_keys = {
            (relation.source_id, relation.target_id, relation.label, relation.directed)
            for state in scene.states
            for relation in state.relations
        }
        relations = "\n".join(
            f"""<g id="relation-{scene_id}-{relation_index}" class="relation" data-relation-index="{relation_index}">
              <line></line><circle class="relation-head" r="0.55"></circle>
              <text>{html.escape(label)}</text>
            </g>"""
            for relation_index, (_source, _target, label, _directed) in enumerate(sorted(relation_keys))
        )
        grammar_label = {
            "concept": "概念",
            "model": "模型",
            "trace": "推演",
            "evidence": "证据",
        }[scene.grammar.value]
        return f"""<section id="scene-{scene_id}" class="teaching-scene grammar-{scene.grammar.value}"
                 data-scene-id="{scene_id}" data-grammar="{scene.grammar.value}">
          <header class="scene-heading">
            <span class="scene-number">{index:02d}</span>
            <div><span class="grammar-label">{grammar_label}</span><h1>{html.escape(scene.title)}</h1></div>
          </header>
          <div class="visual-stage">
            <svg class="relation-layer" viewBox="0 0 100 100" preserveAspectRatio="none"
                 data-layout-allow-overlap aria-hidden="true">
              {relations}
            </svg>
            <div class="entity-layer">{entities}</div>
            <div id="state-note-{scene_id}" class="state-note"></div>
          </div>
        </section>"""
