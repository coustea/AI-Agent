"""Compile semantic lesson data into one deterministic HyperFrames composition."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from app.shared.cartoon.models import CartoonBundle, Lesson, TeachingScene, Timeline


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
        compositions_dir = output_dir / "compositions"
        compositions_dir.mkdir(exist_ok=True)

        payload = self._payload(lesson, timeline)
        scene_windows = self._scene_windows(lesson, timeline)
        scene_paths = [
            compositions_dir / f"{scene.id}.html"
            for scene in lesson.scenes
        ]
        for index, (scene, path) in enumerate(zip(lesson.scenes, scene_paths, strict=True), start=1):
            path.write_text(self._scene_document(index, scene), encoding="utf-8")
        scene_data_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        caption_path.write_text(self._captions_vtt(timeline), encoding="utf-8")
        html_path.write_text(
            self._html(lesson, timeline, payload, scene_windows),
            encoding="utf-8",
        )
        return CartoonBundle(
            output_dir=output_dir,
            html_path=html_path,
            scene_data_path=scene_data_path,
            caption_path=caption_path,
            scene_paths=scene_paths,
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

    @staticmethod
    def _scene_windows(lesson: Lesson, timeline: Timeline) -> dict[str, tuple[int, int]]:
        windows: dict[str, tuple[int, int]] = {}
        known_scene_ids = {scene.id for scene in lesson.scenes}
        for beat in timeline.beats:
            if beat.scene_id not in known_scene_ids:
                continue
            start_ms, end_ms = windows.get(
                beat.scene_id,
                (beat.start_ms, beat.start_ms),
            )
            windows[beat.scene_id] = (
                min(start_ms, beat.start_ms),
                max(end_ms, beat.start_ms + beat.duration_ms),
            )
        missing = known_scene_ids - set(windows)
        if missing:
            raise ValueError(f"timeline is missing scene windows: {sorted(missing)}")
        return windows

    def _html(
        self,
        lesson: Lesson,
        timeline: Timeline,
        payload: dict[str, object],
        scene_windows: dict[str, tuple[int, int]],
    ) -> str:
        scenes = "\n".join(
            self._scene_mount(scene, scene_windows[scene.id])
            for scene in lesson.scenes
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
    def _scene_mount(scene: TeachingScene, window: tuple[int, int]) -> str:
        start_ms, end_ms = window
        scene_id = html.escape(scene.id)
        return (
            f'<div id="scene-mount-{scene_id}" data-composition-id="{scene_id}" '
            f'data-composition-src="compositions/{scene_id}.html" '
            f'data-start="{_seconds(start_ms)}" '
            f'data-duration="{_seconds(end_ms - start_ms)}" '
            'data-track-index="1"></div>'
        )

    @staticmethod
    def _scene_document(index: int, scene: TeachingScene) -> str:
        scene_id = html.escape(scene.id)
        return f"""<!doctype html>
<html lang="zh-CN">
<body>
  <template>
    <div data-composition-id="{scene_id}" data-width="1920" data-height="1080"
         data-layout-allow-overlap>
      {CartoonComposer._scene_html(index, scene)}
    </div>
  </template>
</body>
</html>
"""

    @staticmethod
    def _scene_html(index: int, scene: TeachingScene) -> str:
        scene_id = html.escape(scene.id)
        entities = "\n".join(
            f"""<div id="entity-{scene_id}-{html.escape(entity.id)}"
                 class="visual-entity kind-{entity.kind.value} tone-{('primary', 'secondary', 'accent', 'warning')[index % 4]}"
                 data-entity-id="{html.escape(entity.id)}" data-kind="{entity.kind.value}">
              <span class="entity-label">{html.escape(entity.label)}</span>
              <span class="entity-value"></span>
            </div>"""
            for index, entity in enumerate(scene.entities)
        )
        relation_keys = {
            (relation.source_id, relation.target_id, relation.label)
            for state in scene.states
            for relation in state.relations
        }
        relations = "\n".join(
            f"""<g id="relation-{scene_id}-{relation_index}" class="relation" data-relation-index="{relation_index}">
              <line></line><circle class="relation-head" r="0.55"></circle>
            </g>"""
            for relation_index, _relation in enumerate(sorted(relation_keys))
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
          </div>
        </section>"""
