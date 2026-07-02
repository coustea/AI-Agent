"""Cartoon video generation pipeline — orchestrates the multi-agent flow with TTS integration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable

from app.shared.cartoon.author import HTMLAuthor
from app.shared.cartoon.director import VisualDirector
from app.shared.cartoon.planner import VideoPlanner
from app.shared.cartoon.renderer import CartoonVideoRenderer
from app.shared.cartoon.repair import RepairAgent
from app.shared.cartoon.schemas import (
    CaptionWord,
    CartoonVideoRequest,
    StaticAudit,
    StyleDecision,
    VideoBrief,
)
from app.shared.cartoon.validator import CartoonCliValidator
from app.shared.cartoon.tts import CartoonTtsService

ProgressCallback = Callable[[str, int], Awaitable[None]]


class CartoonGenerationError(RuntimeError):
    def __init__(self, message: str, *, audit: StaticAudit):
        super().__init__(message)
        self.audit = audit


class CartoonArtifact:
    """Result of a successful cartoon generation."""

    def __init__(
        self,
        *,
        html: str,
        brief: VideoBrief,
        style: StyleDecision,
        scene_count: int,
        repaired: bool,
        video_path: Path,
    ):
        self.html = html
        self.brief = brief
        self.style = style
        self.scene_count = scene_count
        self.repaired = repaired
        self.video_path = video_path


class CartoonPipeline:
    """Multi-agent cartoon video generation pipeline."""

    def __init__(
        self,
        *,
        planner: VideoPlanner | None = None,
        director: VisualDirector | None = None,
        author: HTMLAuthor | None = None,
        validator: CartoonCliValidator | None = None,
        repairer: RepairAgent | None = None,
        tts: CartoonTtsService | None = None,
        renderer: CartoonVideoRenderer | None = None,
    ):
        self.planner = planner or VideoPlanner()
        self.director = director or VisualDirector()
        self.author = author or HTMLAuthor()
        self.validator = validator or CartoonCliValidator()
        self.repairer = repairer or RepairAgent()
        self.tts = tts or CartoonTtsService()
        self.renderer = renderer or CartoonVideoRenderer()

    async def generate(
        self,
        request: CartoonVideoRequest,
        *,
        progress: ProgressCallback | None = None,
    ) -> CartoonArtifact:
        # Create output directories
        output_dir = request.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # 1. Plan scene timeline & narrative
        await self._progress(progress, "正在规划动画场景与叙事节奏...", 15)
        brief = await self.planner.plan(request)

        # 2. Parallel TTS Synthesis & Timestamp Extraction
        await self._progress(progress, "正在生成场景 TTS 语音与词级时间戳...", 40)

        async def _synthesize_scene_tts(scene, index: int):
            audio_file = audio_dir / f"scene_{index}.mp3"
            duration_ms, words = await self.tts.synthesize(
                text=scene.narration,
                output_path=audio_file,
                voice=request.voice,
            )
            # Update scene values
            scene.audio_path = f"audio/scene_{index}.mp3"
            # duration = audio length (seconds) + 0.4s padding
            scene.duration = (duration_ms / 1000.0) + 0.4
            scene.words = words

        # Execute TTS in parallel
        await asyncio.gather(
            *[_synthesize_scene_tts(scene, i) for i, scene in enumerate(brief.scenes)]
        )

        # 3. Recalculate timeline starts and total duration
        current_time = 0.0
        for scene in brief.scenes:
            scene.start_time = round(current_time, 3)
            current_time += scene.duration
        brief.total_duration = round(current_time, 3)

        # 4. Choose visual style
        await self._progress(progress, "正在选择视觉风格与动画策略...", 55)
        style = await self.director.direct(brief, request)

        # 5. Generate HyperFrames HTML (in parallel inside HTMLAuthor)
        await self._progress(progress, "正在创作 HyperFrames 动画 HTML...", 75)
        html = await self.author.author(
            request=request,
            brief=brief,
            style=style,
        )

        # Write base file
        html_file = output_dir / "index.html"
        html_file.write_text(html, encoding="utf-8")

        # 6. Validate using HyperFrames CLI
        await self._progress(progress, "正在校验 HTML 结构与 GSAP 语法...", 85)
        audit = await self.validator.validate(output_dir)
        repaired = False

        # 7. Repair if needed
        if not audit.passed:
            repaired = True
            await self._progress(progress, "正在根据校验结果修复 HTML...", 90)
            html = await self.repairer.repair(
                html=html,
                brief=brief,
                style=style,
                audit=audit,
            )
            # Write repaired file
            html_file.write_text(html, encoding="utf-8")
            audit = await self.validator.validate(output_dir)

        if not audit.passed:
            raise CartoonGenerationError(
                "cartoon HTML failed validation after one repair",
                audit=audit,
            )

        # 8. Render final video using HyperFrames CLI
        await self._progress(progress, "正在通过 HyperFrames 渲染最终视频...", 95)
        video_path = await self.renderer.render(output_dir)

        await self._progress(progress, "动画与语音生成及视频渲染完成", 100)
        return CartoonArtifact(
            html=html,
            brief=brief,
            style=style,
            scene_count=audit.scene_count,
            repaired=repaired,
            video_path=video_path,
        )

    @staticmethod
    async def _progress(
        callback: ProgressCallback | None,
        message: str,
        percent: int,
    ) -> None:
        if callback is not None:
            await callback(message, percent)
