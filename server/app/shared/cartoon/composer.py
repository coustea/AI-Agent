"""Compile semantic lesson data into a responsive HyperFrames composition."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from app.infra.logging import get_logger
from app.shared.cartoon.models import CartoonBundle, Lesson, TeachingScene, Timeline


logger = get_logger(__name__)
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
    """Own the teaching canvas; runtime owns measured geometry and motion."""

    def write(self, lesson: Lesson, timeline: Timeline, output_dir: Path) -> CartoonBundle:
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        shutil.copy2(_ASSET_DIR / "runtime.js", assets_dir / "runtime.js")
        shutil.copy2(_ASSET_DIR / "theme.css", assets_dir / "theme.css")

        payload = self._payload(lesson, timeline)
        self._validate_timeline(lesson, timeline)

        caption_path = output_dir / "captions.vtt"
        html_path = output_dir / "index.html"
        caption_path.write_text(self._captions_vtt(timeline), encoding="utf-8")
        html_path.write_text(self._html(lesson, timeline, payload), encoding="utf-8")
        logger.info("[CartoonComposer] 合成完成: scenes=%d beats=%d", len(lesson.scenes), len(timeline.beats))
        return CartoonBundle(
            html_path=html_path,
            caption_path=caption_path,
        )

    @staticmethod
    def _payload(lesson: Lesson, timeline: Timeline) -> dict[str, object]:
        timed_beats = [
            {**beat.model_dump(mode="json"), "end_ms": beat.end_ms}
            for beat in timeline.beats
        ]
        return {
            "composition_id": COMPOSITION_ID,
            "title": lesson.title,
            "duration_ms": timeline.duration_ms,
            "scenes": lesson.model_dump(mode="json")["scenes"],
            "beats": timed_beats,
            "captions": timeline.model_dump(mode="json")["captions"],
        }

    @staticmethod
    def _captions_vtt(timeline: Timeline) -> str:
        lines = ["WEBVTT", ""]
        for index, cue in enumerate(timeline.captions, start=1):
            lines.extend([str(index), f"{_vtt_time(cue.start_ms)} --> {_vtt_time(cue.end_ms)}", cue.text, ""])
        return "\n".join(lines)

    @staticmethod
    def _validate_timeline(lesson: Lesson, timeline: Timeline) -> None:
        scene_by_id = {scene.id: scene for scene in lesson.scenes}
        timed_scene_ids = {beat.scene_id for beat in timeline.beats}
        if timed_scene_ids != set(scene_by_id):
            raise ValueError(
                "timeline scene ids do not match lesson scenes: "
                f"missing={sorted(set(scene_by_id) - timed_scene_ids)}, "
                f"unknown={sorted(timed_scene_ids - set(scene_by_id))}"
            )
        beat_to_scene = {
            beat.id: scene.id
            for scene in lesson.scenes
            for beat in scene.program.beats
        }
        for timed in timeline.beats:
            if beat_to_scene.get(timed.beat_id) != timed.scene_id:
                raise ValueError(
                    f"timeline beat {timed.beat_id} does not belong to scene {timed.scene_id}"
                )

    def _html(self, lesson: Lesson, timeline: Timeline, payload: dict[str, object]) -> str:
        scenes = "\n".join(
            self._scene_html(index, scene)
            for index, scene in enumerate(lesson.scenes, start=1)
        )
        captions = "\n".join(
            f'<p id="caption-{index}" class="caption-cue" data-caption-index="{index}">{html.escape(cue.text)}</p>'
            for index, cue in enumerate(timeline.captions)
        )
        audio = "\n".join(
            f'<audio id="audio-{html.escape(beat.beat_id)}" data-start="{_seconds(beat.start_ms)}" '
            f'data-duration="{_seconds(beat.audio_duration_ms or beat.duration_ms)}" data-track-index="20" '
            f'data-volume="1" src="{html.escape(beat.audio_src)}"></audio>'
            for beat in timeline.beats
        )
        data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
        return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1920, height=1080">
	<title>{html.escape(lesson.title)}</title><link rel="stylesheet" href="assets/theme.css">
	<link rel="alternate" type="text/vtt" href="captions.vtt" hreflang="zh-CN"></head>
	<body><main id="root" data-composition-id="{COMPOSITION_ID}" data-start="0" data-duration="{_seconds(timeline.duration_ms)}" data-width="1920" data-height="1080">
	<div class="lesson-field" aria-hidden="true"></div>{scenes}
	<div id="caption-track" class="caption-track" aria-hidden="true">{captions}</div>
<div class="progress-rail" aria-hidden="true"><span id="progress-fill"></span></div>{audio}
</main><script src="assets/vendor/gsap.min.js"></script><script src="assets/runtime.js"></script>
<script>window.__timelines=window.__timelines||{{}};window.__timelines['{COMPOSITION_ID}']=window.CartoonRuntime.mount({data_json});</script></body></html>"""

    @staticmethod
    def _scene_html(index: int, scene: TeachingScene) -> str:
        scene_id = html.escape(scene.id)
        objects = scene.program.objects
        entities = "\n".join(
            f'''<div id="entity-{scene_id}-{html.escape(item.id)}" class="visual-entity role-{item.role.value}"
                  data-object-id="{html.escape(item.id)}" data-role="{item.role.value}">
                <span class="entity-label">{html.escape(item.label)}</span>
                <span class="entity-value"></span></div>'''
            for item in objects
        )
        relation_keys = {
            (relation.source_id, relation.target_id)
            for state in scene.program.states for relation in state.relations
        }
        relations = "\n".join(
            f'<g id="relation-{scene_id}-{number}" class="relation" data-relation-index="{number}"><line></line><circle class="relation-head" r="0.55"></circle></g>'
            for number, _ in enumerate(sorted(relation_keys))
        )
        mode_label = {"concept": "概念", "mechanism": "机制", "execution": "推演", "comparison": "比较", "evidence": "验证"}[scene.mode.value]
        return f'''<section id="scene-{scene_id}" class="teaching-scene mode-{scene.mode.value} topology-{scene.topology.value}"
                    data-scene-id="{scene_id}" data-mode="{scene.mode.value}" data-topology="{scene.topology.value}">
  <header class="scene-heading"><span class="scene-number">{index:02d}</span><div><span class="mode-label">{mode_label}</span><h1>{html.escape(scene.title)}</h1></div></header>
  <div class="visual-stage">
  <svg class="relation-layer" viewBox="0 0 100 100" preserveAspectRatio="none" data-layout-allow-overlap aria-hidden="true">{relations}</svg>
  <div class="entity-layer">{entities}</div></div></section>'''
