"""End-to-end HyperFrames teaching-video generation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.shared.cartoon.compiler import COMPOSITION_ID, CartoonCompiler
from app.shared.cartoon.planner import CartoonLessonPlanner
from app.shared.cartoon.renderer import CartoonVideoRenderer
from app.shared.cartoon.schemas import AudioSynthesis, CartoonBrief, CompositionPlan, TeachingLesson
from app.shared.cartoon.timeline import build_composition_plan
from app.shared.cartoon.tts import CartoonTtsService

logger = get_logger(__name__)


class CartoonGenerationError(RuntimeError):
    def __init__(self, message: str, *, stage: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.problems = list(problems or [])


@dataclass(frozen=True)
class CartoonGenerationResult:
    schema_version: str
    title: str
    duration_ms: int
    scene_count: int
    has_audio: bool
    output_dir: Path
    lesson_path: Path
    composition_path: Path
    html_path: Path
    video_path: Path
    manifest_path: Path
    audit_path: Path


class CartoonVideoAgent:
    def __init__(self, *, planner: Any | None = None, tts: Any | None = None, compiler: CartoonCompiler | None = None, renderer: CartoonVideoRenderer | None = None, gsap_source: Path | None = None, max_parallel_scenes: int = 3) -> None:
        self.planner = planner or CartoonLessonPlanner()
        self.tts = tts or CartoonTtsService(provider="edge")
        self.compiler = compiler or CartoonCompiler()
        self.renderer = renderer or CartoonVideoRenderer()
        self.gsap_source = gsap_source
        self._speech_semaphore = asyncio.Semaphore(max(1, max_parallel_scenes))

    async def generate(self, brief: CartoonBrief, output_dir: Path) -> CartoonGenerationResult:
        self._prepare_output_dir(output_dir)
        audit_path = output_dir / "audit.json"
        audit: dict[str, Any] = {"schema_version": "cartoon/audit-v2", "passed": False, "composition_id": COMPOSITION_ID, "stages": {}}
        try:
            lesson = await self._plan(brief)
            audit["stages"]["planning"] = {"passed": True, "scene_count": len(lesson.scenes)}
            audio = await self._synthesize_steps(brief, lesson, output_dir)
            audit["stages"]["speech"] = {"passed": True, "step_count": len(audio)}
            plan = build_composition_plan(lesson, self._relative_audio(audio, output_dir))
            audit["stages"]["timeline"] = {"passed": True, "duration_ms": plan.total_duration_ms}
            lesson_path, composition_path = self._write_semantics(lesson, plan, output_dir)
            self._copy_gsap(output_dir)
            html_path, template = self.compiler.write(lesson, plan, output_dir, brief.configuration.template_id)
            audit["stages"]["compile"] = {"passed": True, "template": {"id": template.id, "version": template.version}}
            lint = await self.renderer.lint(output_dir)
            audit["stages"]["lint"] = {"passed": lint.passed, "problems": list(lint.problems)}
            if not lint.passed:
                raise CartoonGenerationError("HyperFrames lint 失败", stage="lint", problems=list(lint.problems))
            render = await self.renderer.render(output_dir)
            if not await self.renderer.has_audio_stream(render.video_path):
                raise CartoonGenerationError("渲染完成但 MP4 没有音频轨", stage="media")
            audit["stages"]["render"] = {"passed": True, "width": render.width, "height": render.height, "fps": render.fps, "size_bytes": render.size_bytes, "has_audio": True}
            manifest_path = output_dir / "manifest.json"
            self._write_json(manifest_path, {
                "schema_version": "cartoon/artifact-v2", "title": lesson.title, "composition_id": COMPOSITION_ID,
                "template": {"id": template.id, "version": template.version}, "duration_ms": plan.total_duration_ms,
                "scene_count": len(plan.scenes), "has_audio": True,
                "files": {"lesson": lesson_path.name, "composition": composition_path.name, "html": html_path.name, "video": render.video_path.name, "audit": audit_path.name},
                "render": {"width": render.width, "height": render.height, "fps": render.fps, "size_bytes": render.size_bytes},
            })
            audit["passed"] = True
            self._write_json(audit_path, audit)
            return CartoonGenerationResult("cartoon/artifact-v2", lesson.title, plan.total_duration_ms, len(plan.scenes), True, output_dir, lesson_path, composition_path, html_path, render.video_path, manifest_path, audit_path)
        except CartoonGenerationError as exc:
            audit.update({"failed_stage": exc.stage, "error": str(exc), "problems": exc.problems})
            self._write_audit(audit_path, audit)
            raise
        except Exception as exc:
            audit.update({"failed_stage": "unknown", "error": str(exc)})
            self._write_audit(audit_path, audit)
            raise CartoonGenerationError(f"动画视频生成失败: {exc}", stage="unknown", problems=[str(exc)]) from exc

    async def _plan(self, brief: CartoonBrief) -> TeachingLesson:
        try:
            return await self.planner.plan(brief)
        except Exception as exc:
            raise CartoonGenerationError(f"教学动画规划失败: {exc}", stage="planning", problems=[str(exc)]) from exc

    async def _synthesize_steps(self, brief: CartoonBrief, lesson: TeachingLesson, output_dir: Path) -> dict[str, AudioSynthesis]:
        audio_dir = output_dir / "audio"
        audio_dir.mkdir()
        cache: dict[str, asyncio.Task[AudioSynthesis]] = {}
        step_tasks: dict[str, asyncio.Task[AudioSynthesis]] = {}
        for scene in lesson.scenes:
            for step in scene.steps:
                text = " ".join(step.narration.split())
                digest = hashlib.sha256(f"{brief.configuration.voice}:{text}".encode()).hexdigest()[:16]
                if digest not in cache:
                    cache[digest] = asyncio.create_task(self._synthesize_one(text, audio_dir / f"{digest}.mp3", brief.configuration.voice))
                step_tasks[f"{scene.id}:{step.id}"] = cache[digest]
        try:
            return {key: await task for key, task in step_tasks.items()}
        except Exception as exc:
            raise CartoonGenerationError(f"教学旁白合成失败: {exc}", stage="speech", problems=[str(exc)]) from exc

    async def _synthesize_one(self, text: str, output_path: Path, voice: str) -> AudioSynthesis:
        async with self._speech_semaphore:
            result = await self.tts.synthesize(text, output_path, voice)
        if not result.path.is_file() or result.path.stat().st_size <= 0 or result.duration_ms <= 0:
            raise RuntimeError("TTS 未生成有效音频")
        return result

    @staticmethod
    def _relative_audio(audio: dict[str, AudioSynthesis], output_dir: Path) -> dict[str, AudioSynthesis]:
        root = output_dir.resolve()
        return {key: item.model_copy(update={"path": item.path.resolve().relative_to(root)}) for key, item in audio.items()}

    @staticmethod
    def _write_semantics(lesson: TeachingLesson, plan: CompositionPlan, output_dir: Path) -> tuple[Path, Path]:
        lesson_path, composition_path = output_dir / "lesson.json", output_dir / "composition.json"
        lesson_path.write_text(lesson.model_dump_json(indent=2), encoding="utf-8")
        composition_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        return lesson_path, composition_path

    def _copy_gsap(self, output_dir: Path) -> None:
        source = self.gsap_source or self._discover_gsap_source()
        target = output_dir / "assets" / "vendor"
        target.mkdir(parents=True)
        shutil.copy2(source, target / "gsap.min.js")

    @staticmethod
    def _discover_gsap_source() -> Path:
        for root in (Path.cwd(), *Path(__file__).resolve().parents[:7]):
            for candidate in (root / "node_modules/gsap/dist/gsap.min.js", root / "frontend/node_modules/gsap/dist/gsap.min.js"):
                if candidate.is_file():
                    return candidate
        raise FileNotFoundError("缺少 GSAP 运行时")

    @staticmethod
    def _prepare_output_dir(output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        if any(output_dir.iterdir()):
            raise CartoonGenerationError(f"Agent output directory must be empty: {output_dir}", stage="workspace")

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def _write_audit(cls, path: Path, payload: dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            cls._write_json(path, payload)
        except Exception:
            logger.warning("Failed to write cartoon audit", exc_info=True)
