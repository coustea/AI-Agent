"""Fast deterministic pipeline: storyboard → Edge TTS → HTML → MP4."""

from __future__ import annotations

import asyncio
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from app.infra.logging import get_logger
from app.shared.cartoon.compiler import CartoonCompiler
from app.shared.cartoon.planner import VideoPlanner
from app.shared.cartoon.renderer import CartoonRenderProfile, CartoonVideoRenderer
from app.shared.cartoon.schemas import CartoonVideoRequest, StaticAudit, VideoBrief
from app.shared.cartoon.tts import CartoonTtsService
from app.shared.cartoon.validator import CartoonCliValidator

logger = get_logger(__name__)

ProgressCallback = Callable[[str, int], Awaitable[None]]


class CartoonGenerationError(RuntimeError):
    def __init__(self, message: str, *, audit: StaticAudit | None = None) -> None:
        super().__init__(message)
        self.audit = audit


@dataclass(frozen=True)
class CartoonArtifact:
    html: str
    brief: VideoBrief
    theme: str
    scene_count: int
    video_path: Path
    render_profile: CartoonRenderProfile


class CartoonPipeline:
    """Generate a complete MP4 with deterministic authoring.

    Main stages:
        1. theory-mechanism storyboard planning
        2. Edge TTS synthesis with word-boundary metadata
        3. HyperFrames-compatible HTML compilation
        4. static + CLI validation
        5. MP4 rendering
    """

    def __init__(
        self,
        *,
        planner: VideoPlanner | None = None,
        compiler: CartoonCompiler | None = None,
        validator: CartoonCliValidator | None = None,
        tts: CartoonTtsService | None = None,
        renderer: CartoonVideoRenderer | None = None,
        tts_concurrency: int = 4,
    ) -> None:
        self.planner = planner or VideoPlanner()
        self.compiler = compiler or CartoonCompiler()
        self.validator = validator or CartoonCliValidator()
        self.tts = tts or CartoonTtsService()
        self.renderer = renderer or CartoonVideoRenderer()
        self.tts_concurrency = max(1, min(tts_concurrency, 8))

    async def generate(
        self,
        request: CartoonVideoRequest,
        *,
        progress: ProgressCallback | None = None,
    ) -> CartoonArtifact:
        pipeline_started = time.perf_counter()
        logger.info(
            "Cartoon 管线开始: learning_need=%s style=%s depth=%s",
            request.learning_need[:50],
            request.style,
            request.depth,
        )

        output_dir = request.output_dir
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # ── 分镜规划 ──
        await self._progress(progress, "正在规划计算机理论机制动画分镜...", 12)
        stage_started = time.perf_counter()
        logger.info("Cartoon 分镜规划开始")
        try:
            brief = await self.planner.plan(request)
        except Exception as exc:
            logger.error("Cartoon 分镜规划失败: error=%s", exc)
            raise CartoonGenerationError(f"教学分镜生成失败: {exc}") from exc

        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Cartoon 分镜规划完成: scenes=%d subject=%s total_duration=%.1fs elapsed_ms=%d",
            len(brief.scenes),
            brief.subject,
            brief.total_duration,
            stage_elapsed,
        )
        logger.info(
            "Cartoon 分镜内容: scenes=%s",
            [(s.role, s.title, s.layout) for s in brief.scenes],
        )

        # ── 配音合成 ──
        await self._progress(progress, "正在合成配音与词级时间轴...", 30)
        stage_started = time.perf_counter()
        logger.info(
            "Cartoon 配音合成开始: scenes=%d concurrency=%d",
            len(brief.scenes),
            self.tts_concurrency,
        )
        semaphore = asyncio.Semaphore(self.tts_concurrency)

        async def synthesize_scene(index: int) -> tuple[int, list]:
            async with semaphore:
                return await self.tts.synthesize(
                    text=brief.scenes[index].narration,
                    output_path=audio_dir / f"scene_{index}.mp3",
                    voice="zh-CN-XiaoxiaoNeural",
                )

        try:
            tts_results = await asyncio.gather(
                *(synthesize_scene(index) for index in range(len(brief.scenes)))
            )
        except Exception as exc:
            logger.error("Cartoon 配音合成失败: error=%s", exc)
            raise CartoonGenerationError(f"Edge TTS 配音生成失败: {exc}") from exc

        current_time = 0.0
        for index, (scene, (duration_ms, words)) in enumerate(
            zip(brief.scenes, tts_results)
        ):
            scene.audio_path = f"audio/scene_{index}.mp3"
            scene.words = words
            scene.start_time = round(current_time, 3)
            scene.duration = round(max(1.0, duration_ms / 1000 + 0.35), 3)
            current_time += scene.duration
        brief.total_duration = round(current_time, 3)

        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Cartoon 配音合成完成: scenes=%d total_duration=%.1fs elapsed_ms=%d",
            len(brief.scenes),
            brief.total_duration,
            stage_elapsed,
        )

        # ── HTML 编译 ──
        await self._progress(progress, "正在编译理论机制图形、字幕与同步动画...", 58)
        stage_started = time.perf_counter()
        logger.info(
            "Cartoon HTML 编译开始: scenes=%d style=%s",
            len(brief.scenes),
            request.style,
        )
        try:
            self._copy_vendor_assets(output_dir)
            html = self.compiler.compile(request, brief)
            html_file = output_dir / "index.html"
            html_file.write_text(html, encoding="utf-8")
        except Exception as exc:
            logger.error("Cartoon HTML 编译失败: error=%s", exc)
            raise CartoonGenerationError(f"动画 HTML 编译失败: {exc}") from exc

        html_size = len(html)
        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Cartoon HTML 编译完成: html_size=%d elapsed_ms=%d",
            html_size,
            stage_elapsed,
        )

        # ── 结构校验 ──
        await self._progress(progress, "正在快速检查 HyperFrames 合成结构...", 72)
        stage_started = time.perf_counter()
        logger.info("Cartoon 结构校验开始")
        audit = await self.validator.validate(output_dir)
        if audit.scene_count != len(brief.scenes):
            audit.passed = False
            audit.problems.append(
                f"场景数量不匹配: 期望 {len(brief.scenes)}，实际 {audit.scene_count}"
            )
        if not audit.passed:
            details = "；".join(audit.problems[:6])
            logger.error("Cartoon 结构校验失败: problems=%s", details)
            raise CartoonGenerationError(
                f"HyperFrames 合成检查失败: {details}",
                audit=audit,
            )

        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        logger.info(
            "Cartoon 结构校验完成: passed=%s scene_count=%d elapsed_ms=%d",
            audit.passed,
            audit.scene_count,
            stage_elapsed,
        )

        # ── MP4 渲染 ──
        await self._progress(progress, "正在渲染最终 MP4 视频...", 78)
        stage_started = time.perf_counter()
        logger.info("Cartoon MP4 渲染开始")
        try:
            render_result = await self.renderer.render(output_dir)
        except Exception as exc:
            logger.error("Cartoon MP4 渲染失败: error=%s", exc)
            raise CartoonGenerationError(f"MP4 渲染失败: {exc}") from exc

        stage_elapsed = int((time.perf_counter() - stage_started) * 1000)
        video_size = (
            render_result.video_path.stat().st_size
            if render_result.video_path.exists()
            else 0
        )
        logger.info(
            "Cartoon MP4 渲染完成: size_bytes=%d elapsed_ms=%d",
            video_size,
            stage_elapsed,
        )

        await self._progress(progress, "动画讲解视频已生成", 100)
        total_elapsed = int((time.perf_counter() - pipeline_started) * 1000)
        logger.info(
            "Cartoon 管线完成: scenes=%d duration=%.1fs total_elapsed_ms=%d",
            audit.scene_count,
            brief.total_duration,
            total_elapsed,
        )
        return CartoonArtifact(
            html=html,
            brief=brief,
            theme=self.compiler.theme_name(request.style),
            scene_count=audit.scene_count,
            video_path=render_result.video_path,
            render_profile=render_result.profile,
        )

    @staticmethod
    async def _progress(
        callback: ProgressCallback | None,
        message: str,
        percent: int,
    ) -> None:
        if callback is not None:
            await callback(message, percent)

    @staticmethod
    def _copy_vendor_assets(output_dir: Path) -> None:
        """Copy local GSAP vendor assets into the render directory when present.

        The generated HTML uses local assets first:
            ./assets/vendor/gsap.min.js
            ./assets/vendor/MotionPathPlugin.min.js

        If the project has not provided these files yet, compilation still works
        because compiler.py includes a CDN fallback.
        """
        source_dir = Path(__file__).resolve().parent / "assets" / "vendor"
        if not source_dir.is_dir():
            return

        target_dir = output_dir / "assets" / "vendor"
        target_dir.mkdir(parents=True, exist_ok=True)

        for filename in ("gsap.min.js", "MotionPathPlugin.min.js"):
            source = source_dir / filename
            if source.is_file():
                shutil.copy2(source, target_dir / filename)