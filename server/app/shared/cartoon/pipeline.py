"""One deep interface for planning, speech, composition and verified rendering."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.infra.logging import get_logger
from app.shared.cartoon.composer import COMPOSITION_ID, CartoonComposer
from app.shared.cartoon.media import CartoonMedia, QualityGateError
from app.shared.cartoon.models import (
    CartoonArtifact,
    CartoonBrief,
    CartoonGenerationError,
)
from app.shared.cartoon.planner import CartoonPlanner, CartoonPlanningError
from app.shared.cartoon.tts import CartoonSpeech


logger = get_logger(__name__)
_PUBLISH_LOCKS: dict[str, asyncio.Lock] = {}
_PUBLISH_LOCKS_GUARD = asyncio.Lock()


class CartoonPipeline:
    """Hide the complete generation workflow behind one validated artifact."""

    def __init__(
        self,
        *,
        planner: Any | None = None,
        speech: Any | None = None,
        composer: Any | None = None,
        media: Any | None = None,
    ) -> None:
        self.planner = planner or CartoonPlanner()
        self.speech = speech or CartoonSpeech()
        self.composer = composer or CartoonComposer()
        self.media = media or CartoonMedia()

    async def generate(self, brief: CartoonBrief, output_dir: Path) -> CartoonArtifact:
        logger.info(
            "[Cartoon] 开始生成: learning_need=%s depth=%s voice=%s output_dir=%s",
            brief.learning_need,
            brief.configuration.lesson_depth.value,
            brief.configuration.voice,
            output_dir,
        )
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        workspace = output_dir.parent / f".{output_dir.name}.work-{uuid4().hex}"
        workspace.mkdir(parents=False, exist_ok=False)
        logger.info("[Cartoon] 工作目录已创建: workspace=%s", workspace)
        try:
            artifact = await self._generate_workspace(brief, workspace)
            relative_paths = {
                field: getattr(artifact, field).relative_to(workspace)
                for field in (
                    "html_path",
                    "video_path",
                    "caption_path",
                    "lesson_path",
                    "timeline_path",
                    "audit_path",
                )
            }
            await self._publish(workspace, output_dir)
            logger.info(
                "[Cartoon] 生成完成: title=%s duration_ms=%s scene_count=%s video=%s",
                artifact.title,
                artifact.duration_ms,
                artifact.scene_count,
                artifact.video_path,
            )
            return artifact.model_copy(
                update={
                    "output_dir": output_dir,
                    **{
                        field: output_dir / relative_path
                        for field, relative_path in relative_paths.items()
                    },
                }
            )
        except Exception:
            logger.exception("[Cartoon] 生成失败，保留诊断目录: workspace=%s", workspace)
            self._preserve_failure_workspace(workspace)
            raise

    @staticmethod
    def _preserve_failure_workspace(workspace: Path) -> None:
        """Keep private diagnostics for a failed quality gate instead of deleting evidence."""

        if not workspace.exists():
            return
        diagnostics_root = Path(__file__).resolve().parents[3] / "storage" / "cartoon-failures"
        diagnostics_root.mkdir(parents=True, exist_ok=True)
        destination = diagnostics_root / f"{workspace.name.lstrip('.')}-{uuid4().hex}"
        try:
            shutil.move(str(workspace), str(destination))
            logger.error("Cartoon failure workspace preserved at %s", destination)
        except Exception:
            logger.exception("Unable to preserve failed Cartoon workspace %s", workspace)
            shutil.rmtree(workspace, ignore_errors=True)

    async def _generate_workspace(self, brief: CartoonBrief, output_dir: Path) -> CartoonArtifact:

        audit_path = output_dir / "audit.json"
        audit: dict[str, Any] = {
            "schema_version": "cartoon/audit-v8",
            "composition_id": COMPOSITION_ID,
            "passed": False,
            "stages": {},
        }
        stage = "planning"
        pipeline_start = asyncio.get_event_loop().time()
        try:
            logger.info("[Cartoon] 阶段 planning: 开始生成分镜...")
            t0 = asyncio.get_event_loop().time()
            lesson = await self.planner.plan(brief)
            planning_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            lesson_path = output_dir / "lesson.json"
            lesson_path.write_text(
                json.dumps(lesson.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            audit["stages"]["planning"] = {
                "passed": True,
                "scene_count": len(lesson.scenes),
                "beat_count": sum(len(scene.beats) for scene in lesson.scenes),
                "grammars": sorted({scene.grammar.value for scene in lesson.scenes}),
                "elapsed_ms": planning_ms,
            }
            logger.info(
                "[Cartoon] 阶段 planning: 完成 scenes=%s beats=%s grammars=%s elapsed_ms=%d",
                len(lesson.scenes),
                sum(len(s.beats) for s in lesson.scenes),
                sorted({s.grammar.value for s in lesson.scenes}),
                planning_ms,
            )

            stage = "speech"
            logger.info("[Cartoon] 阶段 speech: 开始旁白合成...")
            t0 = asyncio.get_event_loop().time()
            timeline = await self.speech.synthesize(
                lesson,
                output_dir,
                voice=brief.configuration.voice,
                pace=brief.configuration.pace,
            )
            speech_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            timeline_path = output_dir / "timeline.json"
            timeline_path.write_text(
                json.dumps(timeline.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            audit["stages"]["speech"] = {
                "passed": True,
                "beat_count": len(timeline.beats),
                "caption_count": len(timeline.captions),
                "duration_ms": timeline.duration_ms,
                "elapsed_ms": speech_ms,
            }
            logger.info(
                "[Cartoon] 阶段 speech: 完成 beats=%s captions=%s duration_ms=%s elapsed_ms=%d",
                len(timeline.beats),
                len(timeline.captions),
                timeline.duration_ms,
                speech_ms,
            )

            stage = "compose"
            logger.info("[Cartoon] 阶段 compose: 开始动画合成...")
            t0 = asyncio.get_event_loop().time()
            bundle = self.composer.write(lesson, timeline, output_dir)
            compose_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            self.media.install_runtime(output_dir)
            required_files = [
                bundle.html_path,
                bundle.scene_data_path,
                bundle.caption_path,
                *bundle.scene_paths,
                output_dir / "assets" / "runtime.js",
                output_dir / "assets" / "theme.css",
                output_dir / "assets" / "vendor" / "gsap.min.js",
            ]
            missing = [str(path) for path in required_files if not path.is_file()]
            if missing:
                logger.error("[Cartoon] 阶段 compose: 缺少必要文件: %s", missing)
                raise CartoonGenerationError(
                    "动画合成缺少必要文件",
                    stage="compose",
                    problems=missing,
                )
            html_size = bundle.html_path.stat().st_size if bundle.html_path.is_file() else 0
            audit["stages"]["compose"] = {
                "passed": True,
                "engine": "hyperframes-html-v8",
                "caption_artifact": bundle.caption_path.name,
                "caption_mode": "burned-in+vtt",
                "html_size_bytes": html_size,
                "scene_count": len(bundle.scene_paths),
                "elapsed_ms": compose_ms,
            }
            logger.info(
                "[Cartoon] 阶段 compose: 完成 html=%s scenes=%s html_size=%d elapsed_ms=%d",
                bundle.html_path,
                len(bundle.scene_paths),
                html_size,
                compose_ms,
            )

            stage = "quality"
            logger.info("[Cartoon] 阶段 quality: 开始质量检查...")
            t0 = asyncio.get_event_loop().time()
            report = await self.media.check(output_dir)
            quality_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            audit["stages"]["quality"] = {
                "passed": True,
                "hyperframes_ok": report.ok,
                "exit_code": report.exit_code,
                "finding_counts": {
                    category: report.count(category)
                    for category in ("lint", "runtime", "layout", "motion", "contrast", "semantic", "unknown")
                },
                "findings": [item.model_dump(mode="json") for item in report.findings],
                "elapsed_ms": quality_ms,
            }
            logger.info(
                "[Cartoon] 阶段 quality: 完成 ok=%s findings=%s elapsed_ms=%d",
                report.ok,
                {cat: report.count(cat) for cat in ("lint", "runtime", "layout", "motion", "contrast", "semantic", "unknown")},
                quality_ms,
            )

            stage = "render"
            logger.info("[Cartoon] 阶段 render: 开始视频渲染...")
            t0 = asyncio.get_event_loop().time()
            video_path = await self.media.render(output_dir)
            render_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            probe = await self.media.probe(
                video_path,
                expected_duration_ms=timeline.duration_ms,
            )
            audit["stages"]["render"] = {
                "passed": True,
                "elapsed_ms": render_ms,
                **probe.model_dump(mode="json"),
            }
            audit["passed"] = True
            self._write_audit(audit_path, audit)
            total_ms = round((asyncio.get_event_loop().time() - pipeline_start) * 1000)
            logger.info(
                "[Cartoon] 阶段 render: 完成 video=%s duration=%.1fs resolution=%sx%s has_audio=%s elapsed_ms=%d",
                video_path,
                probe.duration_seconds,
                probe.width,
                probe.height,
                probe.has_audio,
                render_ms,
            )
            logger.info(
                "[Cartoon] 全流程完成: total_ms=%d planning=%d speech=%d compose=%d quality=%d render=%d",
                total_ms, planning_ms, speech_ms, compose_ms, quality_ms, render_ms,
            )
            return CartoonArtifact(
                title=lesson.title,
                duration_ms=timeline.duration_ms,
                scene_count=len(lesson.scenes),
                output_dir=output_dir,
                html_path=bundle.html_path,
                video_path=video_path,
                caption_path=bundle.caption_path,
                lesson_path=lesson_path,
                timeline_path=timeline_path,
                audit_path=audit_path,
            )
        except CartoonGenerationError as exc:
            self._record_failure(audit, audit_path, exc.stage, str(exc), exc.problems)
            raise
        except CartoonPlanningError as exc:
            wrapped = CartoonGenerationError(
                str(exc),
                stage="planning",
                problems=[str(exc)],
            )
            self._record_failure(audit, audit_path, wrapped.stage, str(wrapped), wrapped.problems)
            raise wrapped from exc
        except QualityGateError as exc:
            wrapped = CartoonGenerationError(
                "动画未通过发布质量门: " + str(exc),
                stage="quality",
                problems=exc.problems,
            )
            self._record_failure(audit, audit_path, wrapped.stage, str(wrapped), wrapped.problems)
            raise wrapped from exc
        except Exception as exc:
            logger.exception("Cartoon pipeline failed at stage=%s", stage)
            wrapped = CartoonGenerationError(
                f"动画生成在 {stage} 阶段失败: {exc}",
                stage=stage,
                problems=[str(exc)],
            )
            self._record_failure(audit, audit_path, wrapped.stage, str(wrapped), wrapped.problems)
            raise wrapped from exc

    @staticmethod
    async def _publish(workspace: Path, output_dir: Path) -> None:
        logger.info("[Cartoon] 发布: workspace=%s -> output_dir=%s", workspace, output_dir)
        key = str(output_dir.resolve())
        async with _PUBLISH_LOCKS_GUARD:
            lock = _PUBLISH_LOCKS.setdefault(key, asyncio.Lock())
        async with lock:
            backup = output_dir.parent / f".{output_dir.name}.backup-{uuid4().hex}"
            moved_previous = False
            try:
                if output_dir.exists():
                    output_dir.rename(backup)
                    moved_previous = True
                workspace.rename(output_dir)
            except Exception:
                if output_dir.exists() and not workspace.exists():
                    shutil.rmtree(output_dir, ignore_errors=True)
                if moved_previous and backup.exists() and not output_dir.exists():
                    backup.rename(output_dir)
                raise
            else:
                if backup.exists():
                    shutil.rmtree(backup, ignore_errors=True)
        logger.info("[Cartoon] 发布完成: output_dir=%s", output_dir)

    @staticmethod
    def _record_failure(
        audit: dict[str, Any],
        path: Path,
        stage: str,
        message: str,
        problems: list[str],
    ) -> None:
        audit["passed"] = False
        audit["failure"] = {
            "stage": stage,
            "message": message,
            "problems": problems,
        }
        CartoonPipeline._write_audit(path, audit)

    @staticmethod
    def _write_audit(path: Path, audit: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
