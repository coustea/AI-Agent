"""Public orchestration entry for shared teaching-video production."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable

from app.infra.logging import get_logger
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


logger = get_logger(__name__)


# 根据宽高比解析出渲染分辨率与帧率设置
def _render_settings(aspect_ratio: str) -> RenderSettings:
    dimensions = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
    }
    width, height = dimensions[aspect_ratio]
    return RenderSettings(width=width, height=height, fps=30)


# 将 WORKPLACE_DIR 下的产物路径转换为对外的 /static/ URL
def _public_asset_url(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(WORKPLACE_DIR.resolve())
    except ValueError as exc:
        raise ValueError("video assets must be written below WORKPLACE_DIR") from exc
    return f"/static/{relative.as_posix()}"


# 教学视频编排入口：串联素材提取、场景规划、编写、合成与渲染
class VideoAgent:
    """Generate one fully rendered teaching video from source-neutral materials."""

    # 初始化各子 Agent、TTS 与渲染器，并配置并发限制
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
        progress_callback: Callable[[str, int], None] | None = None,
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
        self._progress_callback = progress_callback

    # 通过回调上报进度（若已配置）
    def _report_progress(self, message: str, percent: int) -> None:
        """Report progress to callback if available."""
        if self._progress_callback:
            self._progress_callback(message, percent)

    # 单个场景：编写脚本并用 TTS 合成旁白音频（受并发信号量限制）
    async def _write_and_synthesize(
        self,
        *,
        request: VideoRequest,
        digest: Any,
        style: Any,
        contract: SceneContract,
        audio_dir: Path,
    ) -> tuple[SceneContract, SceneDraft, Any]:
        # 并发控制：最多同时处理 max_parallel_scenes 个场景
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

    # 主流程：执行完整视频生成管线并返回产物
    async def generate(self, request: VideoRequest) -> VideoArtifact:
        pipeline_started = time.perf_counter()
        logger.info(
            "Video 管线开始: topic=%s style=%s scene_count=%d",
            request.topic[:50], request.scene_count, request.scene_count,
        )
        request.output_dir.mkdir(parents=True, exist_ok=True)
        audio_dir = request.output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        self._report_progress("正在提取教学素材...", 25)
        stage_started = time.perf_counter()
        # 阶段一：从素材中抽取核心概念、事实等教学内容
        digest = await self.material_agent.extract(request)
        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Video 素材提取完成: elapsed_ms=%d → core_concepts=%d facts=%d",
            stage_elapsed, len(digest.core_concepts), len(digest.facts),
        )

        self._report_progress("正在规划场景结构与叙事节奏...", 40)
        stage_started = time.perf_counter()
        # 阶段二：导演 Agent 规划场景大纲与叙事
        outline = await self.director.plan(request, digest)
        actual_scene_count = len(outline.scenes)
        # scene_count 是目标值而非硬性契约：导演返回的场景已由 Pydantic 校验结构，
        # 下游（场景编写、时间轴、字幕）全部基于 outline.scenes 实际值，不依赖精确匹配。
        # LLM 偶尔返回 ±1 个场景属正常，不应据此废弃整段视频。
        # 场景数量与请求不一致时仅告警，不中断流程
        if actual_scene_count != request.scene_count:
            logger.warning(
                "Video 导演返回场景数与请求不一致，按实际数量继续: requested=%d actual=%d",
                request.scene_count, actual_scene_count,
            )
        # 场景过少无法构成完整教学视频，直接报错终止
        if actual_scene_count < 2:
            raise ValueError(
                f"video director returned too few scenes: {actual_scene_count}"
            )
        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Video 场景规划完成: scenes=%d narrative=%s elapsed_ms=%d",
            len(outline.scenes), outline.narrative, stage_elapsed,
        )

        self._report_progress(f"正在编写 {len(outline.scenes)} 个场景脚本...", 55)
        stage_started = time.perf_counter()
        # 阶段三：并发编写所有场景脚本并合成旁白
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
        # 按场景顺序排序，保证后续时间轴与渲染的正确顺序
        completed.sort(key=lambda item: item[0].index)
        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Video 场景编写完成: scenes=%d elapsed_ms=%d",
            len(completed), stage_elapsed,
        )
        # 根据每个场景实测音频时长计算连续场景时间轴（含尾部留白）
        timings = build_scene_timing(
            [item[2].duration_ms for item in completed],
            tail_padding_ms=self.tail_padding_ms,
        )

        self._report_progress("正在合成字幕与视觉对齐...", 75)
        stage_started = time.perf_counter()
        # 阶段四：为每个场景构建字幕片段与视觉线索，组装 VideoScene
        scenes: list[VideoScene] = []
        for (contract, draft, synthesis), timing in zip(
            completed,
            timings,
            strict=True,
        ):
            # 按是否需要字幕生成字幕片段
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
            # 将视觉节拍对齐到旁白时间轴，得到带时段的视觉线索
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

        # 汇总生成完整视频计划（含渲染设置与元数据）
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
        self._report_progress("正在渲染视频...", 85)
        # 阶段五：调用渲染器产出最终 MP4
        render_result = await self.renderer.render(plan, request.output_dir)
        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Video 渲染完成: size_bytes=%d elapsed_ms=%d",
            render_result.size_bytes, stage_elapsed,
        )

        total_elapsed = int((time.perf_counter() - pipeline_started) * 1000)
        logger.info(
            "Video 管线完成: scenes=%d duration_ms=%d total_elapsed_ms=%d",
            len(scenes), plan.duration_ms, total_elapsed,
        )
        return render_result
