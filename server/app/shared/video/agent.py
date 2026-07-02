"""Public orchestration entry for shared teaching-video production."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.config import WORKPLACE_DIR
from app.shared.video.director import VideoDirectorAgent
from app.shared.video.material import VideoMaterialAgent
from app.shared.video.scene_writer import SceneWriterAgent
from app.shared.video.schemas import (
    RenderSettings,
    SceneContract,
    SceneDraft,
    VideoArtifact,
    VideoPlan,
    VideoRequest,
    VideoScene,
)
from app.shared.video.timeline import (
    VisualBeat,
    align_visual_cues,
    build_caption_chunks,
    build_scene_timing,
)
from app.shared.video.tts import VideoTtsService


def _render_settings(aspect_ratio: str) -> RenderSettings:
    dimensions = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
    }
    width, height = dimensions[aspect_ratio]
    return RenderSettings(width=width, height=height, fps=30)


def _public_asset_url(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(WORKPLACE_DIR.resolve())
    except ValueError as exc:
        raise ValueError("video assets must be written below WORKPLACE_DIR") from exc
    return f"/static/{relative.as_posix()}"


class VideoAgent:
    """Generate one fully rendered teaching video from source-neutral materials."""

    def __init__(
        self,
        *,
        material_agent: Any | None = None,
        director: Any | None = None,
        scene_writer: Any | None = None,
        tts: Any | None = None,
        renderer: Any | None = None,
        tail_padding_ms: int = 400,
        max_parallel_scenes: int = 4,
    ) -> None:
        self.material_agent = material_agent or VideoMaterialAgent()
        self.director = director or VideoDirectorAgent()
        self.scene_writer = scene_writer or SceneWriterAgent()
        self.tts = tts or VideoTtsService()
        if renderer is None:
            from app.shared.video.renderer import RemotionVideoRenderer

            renderer = RemotionVideoRenderer()
        self.renderer = renderer
        self.tail_padding_ms = tail_padding_ms
        self._scene_semaphore = asyncio.Semaphore(max_parallel_scenes)

    async def _write_and_synthesize(
        self,
        *,
        request: VideoRequest,
        digest: Any,
        style: Any,
        contract: SceneContract,
        audio_dir: Path,
    ) -> tuple[SceneContract, SceneDraft, Any]:
        async with self._scene_semaphore:
            draft = await self.scene_writer.write(
                request=request,
                digest=digest,
                contract=contract,
                style=style,
            )
            audio_path = audio_dir / f"{contract.scene_id}.mp3"
            synthesis = await self.tts.synthesize(
                draft.narration,
                audio_path,
                request.voice,
            )
            return contract, draft, synthesis

    async def generate(self, request: VideoRequest) -> VideoArtifact:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        audio_dir = request.output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        digest = await self.material_agent.extract(request)
        outline = await self.director.plan(request, digest)
        if len(outline.scenes) != request.scene_count:
            raise ValueError("video director returned an unexpected scene count")

        completed = await asyncio.gather(
            *[
                self._write_and_synthesize(
                    request=request,
                    digest=digest,
                    style=outline.style,
                    contract=contract,
                    audio_dir=audio_dir,
                )
                for contract in outline.scenes
            ]
        )
        completed.sort(key=lambda item: item[0].index)
        timings = build_scene_timing(
            [item[2].duration_ms for item in completed],
            tail_padding_ms=self.tail_padding_ms,
        )

        scenes: list[VideoScene] = []
        for (contract, draft, synthesis), timing in zip(
            completed,
            timings,
            strict=True,
        ):
            captions = (
                build_caption_chunks(
                    draft.narration,
                    synthesis.words,
                    synthesis.duration_ms,
                )
                if request.include_captions
                else []
            )
            beats = [
                VisualBeat.model_validate(beat.model_dump())
                for beat in draft.visual_beats
            ]
            visual_cues = align_visual_cues(
                beats,
                narration=draft.narration,
                caption_words=synthesis.words,
                caption_chunks=captions,
                audio_duration_ms=synthesis.duration_ms,
            )
            scenes.append(
                VideoScene(
                    scene_id=contract.scene_id,
                    index=contract.index,
                    role=contract.role,
                    title=draft.title,
                    learning_objective=contract.learning_objective,
                    visual_type=contract.visual_type,
                    visual=draft.visual,
                    narration=draft.narration,
                    audio_src=_public_asset_url(synthesis.path),
                    start_ms=timing.start_ms,
                    duration_ms=timing.duration_ms,
                    audio_duration_ms=timing.audio_duration_ms,
                    caption_words=(
                        synthesis.words if request.include_captions else []
                    ),
                    captions=captions,
                    visual_cues=visual_cues,
                )
            )

        plan = VideoPlan(
            title=outline.title,
            topic=outline.topic,
            language=request.language,
            aspect_ratio=request.aspect_ratio,
            style=outline.style,
            render=_render_settings(request.aspect_ratio),
            scenes=scenes,
            metadata={
                **request.metadata,
                "narrative": outline.narrative,
                "source_ids": [material.source_id for material in request.materials],
            },
        )
        return await self.renderer.render(plan, request.output_dir)
