"""Fast deterministic pipeline: storyboard → Edge TTS → HTML → MP4."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from app.shared.cartoon.compiler import CartoonCompiler
from app.shared.cartoon.planner import VideoPlanner
from app.shared.cartoon.renderer import CartoonRenderProfile, CartoonVideoRenderer
from app.shared.cartoon.schemas import CartoonVideoRequest, StaticAudit, VideoBrief
from app.shared.cartoon.tts import CartoonTtsService
from app.shared.cartoon.validator import CartoonCliValidator

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
    """Generate a complete MP4 with one LLM call and deterministic authoring."""

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
        output_dir = request.output_dir
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        await self._progress(progress, "正在规划教学分镜与语义动画...", 12)
        try:
            brief = await self.planner.plan(request)
        except Exception as exc:
            raise CartoonGenerationError(f"教学分镜生成失败: {exc}") from exc

        await self._progress(progress, "正在使用 Edge TTS 合成配音与词级时间轴...", 30)
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

        await self._progress(progress, "正在编译教学图形、字幕与同步动画...", 58)
        try:
            html = self.compiler.compile(request, brief)
            html_file = output_dir / "index.html"
            html_file.write_text(html, encoding="utf-8")
        except Exception as exc:
            raise CartoonGenerationError(f"动画 HTML 编译失败: {exc}") from exc

        await self._progress(progress, "正在快速检查 HyperFrames 合成结构...", 72)
        audit = await self.validator.validate(output_dir)
        if audit.scene_count != len(brief.scenes):
            audit.passed = False
            audit.problems.append(
                f"场景数量不匹配: 期望 {len(brief.scenes)}，实际 {audit.scene_count}"
            )
        if not audit.passed:
            details = "；".join(audit.problems[:6])
            raise CartoonGenerationError(
                f"HyperFrames 合成检查失败: {details}",
                audit=audit,
            )

        await self._progress(progress, "正在渲染最终 MP4 视频...", 78)
        try:
            render_result = await self.renderer.render(output_dir)
        except Exception as exc:
            raise CartoonGenerationError(f"MP4 渲染失败: {exc}") from exc

        await self._progress(progress, "动画讲解视频已生成", 100)
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
