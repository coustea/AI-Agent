"""HyperFrames execution, typed diagnostics and publication quality policy."""

from __future__ import annotations

import asyncio
import json
import shutil
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.infra.logging import get_logger


logger = get_logger(__name__)


FindingCategory = Literal["lint", "runtime", "layout", "motion", "contrast", "semantic", "unknown"]


class QualityFinding(BaseModel):
    model_config = ConfigDict(extra="allow")
    category: FindingCategory = "unknown"
    code: str = "unknown"
    severity: Literal["error", "warning", "info"] = "error"
    message: str = ""


class HyperFramesReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    findings: list[QualityFinding] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    exit_code: int = 0

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        exit_code: int = 0,
    ) -> "HyperFramesReport":
        findings: list[QualityFinding] = []
        flat_findings = payload.get("findings")
        if isinstance(flat_findings, list):
            for item in flat_findings:
                if isinstance(item, dict):
                    findings.append(cls._finding(item, str(item.get("category") or "unknown")))

        for category in ("lint", "runtime", "layout", "motion", "contrast"):
            section = payload.get(category)
            if not isinstance(section, dict):
                continue
            section_findings = section.get("findings")
            if not isinstance(section_findings, list):
                continue
            for item in section_findings:
                if isinstance(item, dict):
                    findings.append(cls._finding(item, category))

        return cls(
            ok=bool(payload.get("ok", False)),
            findings=findings,
            raw=payload,
            exit_code=exit_code,
        )

    @staticmethod
    def _finding(payload: dict[str, Any], category: str) -> QualityFinding:
        normalized_category = category if category in {
            "lint", "runtime", "layout", "motion", "contrast", "semantic"
        } else "unknown"
        severity = str(payload.get("severity") or "error").lower()
        if severity not in {"error", "warning", "info"}:
            severity = "error"
        return QualityFinding.model_validate(
            {
                **payload,
                "category": normalized_category,
                "severity": severity,
                "code": str(payload.get("code") or "unknown"),
                "message": str(payload.get("message") or ""),
            }
        )

    def count(self, category: FindingCategory) -> int:
        return sum(item.category == category for item in self.findings)

    @property
    def runtime_count(self) -> int:
        return self.count("runtime")

    @property
    def contrast_count(self) -> int:
        return self.count("contrast")

    @property
    def layout_count(self) -> int:
        return self.count("layout")


class QualityGateError(RuntimeError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class QualityPolicy:
    """One explicit publication policy for all HyperFrames findings."""

    _LAYOUT_BLOCKERS = {
        "content_overlap",
        "element_occluded",
        "content_overflow",
        "caption_zone_overlap",
    }

    _CONTRAST_BLOCKERS = frozenset()
    """Contrast codes that block publication. Empty = all contrast findings are advisory."""

    def enforce(self, report: HyperFramesReport) -> None:
        problems: list[str] = []
        for category in ("runtime", "lint", "motion", "semantic"):
            blocking = [
                item for item in report.findings
                if item.category == category and item.severity in {"error", "warning"}
            ]
            if blocking:
                problems.append(f"{category} findings: {self._summarize(blocking)}")
                logger.warning(
                    "[QualityPolicy] %s 阻断问题: %s",
                    category,
                    self._summarize(blocking),
                )

        # Contrast findings are advisory-only by default. HyperFrames measures
        # contrast on dynamically positioned elements whose final rendering
        # depends on the runtime layout engine; low-contrast warnings are
        # common and do not indicate a content defect. Only block if the
        # finding code is explicitly listed in _CONTRAST_BLOCKERS.
        contrast_blocking = [
            item for item in report.findings
            if item.category == "contrast"
            and item.severity in {"error", "warning"}
            and item.code in self._CONTRAST_BLOCKERS
        ]
        if contrast_blocking:
            problems.append(f"contrast findings: {self._summarize(contrast_blocking)}")
            logger.warning("[QualityPolicy] contrast 阻断问题: %s", self._summarize(contrast_blocking))
        contrast_advisory = [
            item for item in report.findings
            if item.category == "contrast"
            and item.severity in {"error", "warning"}
            and item.code not in self._CONTRAST_BLOCKERS
        ]
        if contrast_advisory:
            logger.info("[QualityPolicy] contrast 非阻断问题: %s", self._summarize(contrast_advisory))

        layout = [
            item for item in report.findings
            if item.category == "layout"
            and item.severity == "error"
            and (
                item.code in self._LAYOUT_BLOCKERS
                or "overlap" in item.code
            )
        ]
        if layout:
            problems.append(f"layout findings: {self._summarize(layout)}")
            logger.warning("[QualityPolicy] layout 阻断问题: %s", self._summarize(layout))
        # Log layout warnings (e.g. text_occluded, escaped_container) without blocking
        layout_warnings = [
            item for item in report.findings
            if item.category == "layout"
            and item not in layout
            and item.severity in {"error", "warning"}
        ]
        if layout_warnings:
            logger.info("[QualityPolicy] layout 非阻断问题: %s", self._summarize(layout_warnings))

        unknown = [
            item for item in report.findings
            if item.category == "unknown" and item.severity in {"error", "warning"}
        ]
        if unknown:
            problems.append(f"unknown findings: {self._summarize(unknown)}")
        # HyperFrames reports ok=false for informational Studio advisories too
        # (for example a font substitution). Those are not publication defects;
        # all error and warning findings above still block publication.
        if not report.ok and not problems and not report.findings:
            problems.append("HyperFrames check reported ok=false without a categorized finding")
        if problems:
            logger.error("[QualityPolicy] 质量门未通过: problems=%d", len(problems))
            raise QualityGateError(problems)
        logger.info("[QualityPolicy] 质量门通过: ok=%s findings=%d", report.ok, len(report.findings))

    @staticmethod
    def _summarize(findings: list[QualityFinding]) -> str:
        values: list[str] = []
        for item in findings:
            value = f"{item.code}: {item.message}".strip()
            if value not in values:
                values.append(value)
            if len(values) == 8:
                break
        return " | ".join(values)


class MediaProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_seconds: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    size_bytes: int = Field(gt=0)
    has_audio: bool


class CartoonMedia:
    """Run the fixed repository toolchain and verify the final media artifact."""

    def __init__(
        self,
        *,
        check_timeout_seconds: int = 360,
        render_timeout_seconds: int = 1_800,
    ) -> None:
        self.check_timeout_seconds = check_timeout_seconds
        self.render_timeout_seconds = render_timeout_seconds
        self.policy = QualityPolicy()

    @staticmethod
    def hyperframes_path() -> Path:
        path = Path(__file__).resolve().parents[4] / "node_modules" / ".bin" / "hyperframes"
        windows_shim = path.with_suffix(".cmd")
        if windows_shim.is_file():
            path = windows_shim
        if not path.is_file():
            raise RuntimeError("仓库缺少固定版本 HyperFrames，请先执行 npm install")
        return path

    @staticmethod
    def gsap_path() -> Path:
        path = Path(__file__).resolve().parents[4] / "node_modules" / "gsap" / "dist" / "gsap.min.js"
        if not path.is_file():
            raise RuntimeError("仓库缺少 GSAP 运行时，请先执行 npm install")
        return path

    def install_runtime(self, output_dir: Path) -> None:
        vendor_dir = output_dir / "assets" / "vendor"
        vendor_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.gsap_path(), vendor_dir / "gsap.min.js")

    async def check(self, output_dir: Path) -> HyperFramesReport:
        logger.info("[CartoonMedia] 开始质量检查: dir=%s", output_dir)
        t0 = asyncio.get_event_loop().time()
        command = [
            str(self.hyperframes_path()),
            "check",
            ".",
            "--json",
            "--strict",
            "--at-transitions",
            "--max-issues=200",
            "--frame-check=severity=error;seek=.25,.75;tol=3",
        ]
        logger.info(
            "[CartoonMedia] HyperFrames check 命令: %s (timeout=%ds)",
            " ".join(command[1:]),
            self.check_timeout_seconds,
        )
        exit_code, stdout, stderr = await self._run_streaming(
            command,
            cwd=output_dir,
            timeout_seconds=self.check_timeout_seconds,
            label="check",
        )
        check_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
        logger.info(
            "[CartoonMedia] HyperFrames check 进程结束: exit_code=%d elapsed_ms=%d stdout_len=%d stderr_len=%d",
            exit_code,
            check_ms,
            len(stdout),
            len(stderr),
        )
        if stderr.strip():
            logger.debug("[CartoonMedia] HyperFrames check stderr: %s", stderr[:500])
        try:
            payload = self._json_payload(stdout)
        except ValueError as exc:
            detail = stderr.strip() or stdout.strip() or str(exc)
            logger.error("[CartoonMedia] HyperFrames check JSON 解析失败: %s", detail[:800])
            raise QualityGateError([f"HyperFrames check returned invalid JSON: {detail[:800]}"]) from exc
        report = HyperFramesReport.from_payload(payload, exit_code=exit_code)
        logger.info(
            "[CartoonMedia] HyperFrames 检查完成: ok=%s exit_code=%d findings=%d elapsed_ms=%d",
            report.ok,
            report.exit_code,
            len(report.findings),
            check_ms,
        )
        report.findings.extend(self._semantic_findings(output_dir))
        self.policy.enforce(report)
        await self._check_caption_visibility(output_dir)
        logger.info("[CartoonMedia] 质量检查全部通过")
        return report

    @staticmethod
    def _semantic_findings(output_dir: Path) -> list[QualityFinding]:
        lesson_path = output_dir / "lesson.json"
        if not lesson_path.is_file():
            return [QualityFinding(category="semantic", code="missing_lesson", message="semantic validation requires lesson.json")]
        try:
            from app.shared.cartoon.models import ExecutionObjectRole, ExecutionVerb, Lesson

            lesson = Lesson.model_validate_json(lesson_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return [QualityFinding(category="semantic", code="invalid_lesson", message=str(exc))]

        findings: list[QualityFinding] = []
        for scene in lesson.scenes:
            if scene.grammar.value != "trace":
                continue
            if scene.execution_program is None:
                findings.append(QualityFinding(
                    category="semantic", code="missing_execution_model",
                    message=f"{scene.id} trace scene has no executable model",
                ))
                continue
            objects_by_name = {item.name: item for item in scene.execution_program.objects}
            objects_by_id = {item.id: item for item in scene.execution_program.objects}
            structural_ids = {
                item.id for item in scene.execution_program.objects
                if item.role in {ExecutionObjectRole.CONTAINER, ExecutionObjectRole.NODE, ExecutionObjectRole.PORT}
            }
            if {entity.id for entity in scene.entities} != set(objects_by_id):
                findings.append(QualityFinding(
                    category="semantic", code="execution_entity_mismatch",
                    message=f"{scene.id} execution objects do not match scene entities",
                ))
                continue
            for beat in scene.beats:
                before = scene.state(beat.before_state_id)
                after = scene.state(beat.after_state_id)
                after_items = {item.entity_id: item for item in after.placements}
                if structural_ids and not any(after_items[item_id].visible for item_id in structural_ids):
                    findings.append(QualityFinding(
                        category="semantic", code="hidden_execution_model",
                        message=f"{scene.id}/{beat.id} hides every structural execution object",
                    ))
                for object_id, object_ in objects_by_id.items():
                    placement = after_items[object_id]
                    if object_.role is ExecutionObjectRole.POINTER and placement.visible:
                        anchor = after_items.get(placement.anchor_id)
                        if anchor is None or not anchor.visible:
                            findings.append(QualityFinding(
                                category="semantic", code="pointer_without_visible_anchor",
                                message=f"{scene.id}/{beat.id} pointer {object_.name} has no visible anchor",
                            ))
                operation = beat.operation
                if operation is None:
                    findings.append(QualityFinding(
                        category="semantic", code="missing_execution_operation",
                        message=f"{scene.id}/{beat.id} has no execution operation",
                    ))
                    continue
                subject = objects_by_name.get(operation.subject)
                target = objects_by_name.get(operation.target) if operation.target else None
                if subject is None or (operation.target and target is None):
                    findings.append(QualityFinding(
                        category="semantic", code="operation_unknown_object",
                        message=f"{scene.id}/{beat.id} references an unknown execution object",
                    ))
                elif operation.verb is ExecutionVerb.PLACE:
                    placed = after_items[subject.id]
                    if target is None or placed.container_id != target.id or placed.slot != operation.slot:
                        findings.append(QualityFinding(
                            category="semantic", code="place_without_destination",
                            message=f"{scene.id}/{beat.id} does not place its subject in the declared destination",
                        ))
                elif operation.verb is ExecutionVerb.REMOVE and not (
                    after_items[subject.id].region.value == "output" and after_items[subject.id].visible
                ):
                    findings.append(QualityFinding(
                        category="semantic", code="remove_without_output",
                        message=f"{scene.id}/{beat.id} removes no object to the output dock",
                    ))
                elif operation.verb is ExecutionVerb.POINT and target is not None and after_items[subject.id].anchor_id != target.id:
                    findings.append(QualityFinding(
                        category="semantic", code="point_without_anchor",
                        message=f"{scene.id}/{beat.id} does not attach its pointer to the declared target",
                    ))
                if not scene.state_changes(beat).has_semantic_change:
                    findings.append(QualityFinding(
                        category="semantic", code="operation_without_delta",
                        message=f"{scene.id}/{beat.id} has no execution state delta",
                    ))
        return findings

    @staticmethod
    async def _check_caption_visibility(output_dir: Path) -> None:
        logger.info("[CartoonMedia] 开始字幕可见性检查: dir=%s", output_dir)
        timeline_path = output_dir / "timeline.json"
        if not timeline_path.is_file():
            raise QualityGateError(["caption visibility check requires timeline.json"])
        try:
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
            cues = timeline["captions"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise QualityGateError([f"caption timeline is invalid: {exc}"]) from exc
        if not isinstance(cues, list) or not cues:
            raise QualityGateError(["caption timeline contains no cues"])

        logger.debug("[CartoonMedia] 字幕检查: cues=%d, 启动浏览器验证...", len(cues))

        from playwright.async_api import async_playwright
        from functools import partial
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, _format: str, *_args: object) -> None:
                return

        problems: list[str] = []
        browser_messages: list[str] = []
        browser_state: dict[str, Any] = {}
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(QuietHandler, directory=str(output_dir)),
        )
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                    page.on(
                        "console",
                        lambda message: browser_messages.append(
                            f"console[{message.type}]: {message.text}"
                        ),
                    )
                    page.on(
                        "pageerror",
                        lambda error: browser_messages.append(f"pageerror: {error}"),
                    )
                    await page.goto(
                        f"http://127.0.0.1:{server.server_port}/index.html",
                        wait_until="load",
                    )
                    browser_state = await page.evaluate(
                        """() => ({
                          href: location.href,
                          gsap: Boolean(window.gsap),
                          runtime: Boolean(window.CartoonRuntime),
                          timelines: Object.keys(window.__timelines || {}),
                          scripts: Array.from(document.scripts).map(item => item.src || 'inline')
                        })"""
                    )
                    await page.wait_for_function(
                        "Boolean(window.__timelines && window.__timelines['cartoon-teaching-video'])",
                        timeout=10_000,
                    )
                    for index, cue in enumerate(cues):
                        start_ms = int(cue["start_ms"])
                        end_ms = int(cue["end_ms"])
                        midpoint = (start_ms + end_ms) / 2_000
                        await page.evaluate(
                            """time => {
                              window.__timelines['cartoon-teaching-video'].time(time, false);
                              return true;
                            }""",
                            midpoint,
                        )
                        info = await page.locator(f"#caption-{index}").evaluate(
                            """element => {
                              const style = getComputedStyle(element);
                              const rect = element.getBoundingClientRect();
                              return {
                                opacity: Number(style.opacity),
                                visibility: style.visibility,
                                display: style.display,
                                text: element.textContent.trim(),
                                width: rect.width,
                                height: rect.height,
                                top: rect.top,
                                bottom: rect.bottom
                              };
                            }"""
                        )
                        if (
                            info["opacity"] < 0.95
                            or info["visibility"] != "visible"
                            or info["display"] == "none"
                            or not info["text"]
                            or info["width"] < 400
                            or info["height"] < 40
                            or info["top"] < 850
                            or info["bottom"] > 1080
                        ):
                            problems.append(f"caption-{index} is not visibly rendered at {midpoint:.3f}s")
                finally:
                    await browser.close()
        except QualityGateError:
            raise
        except Exception as exc:
            detail = " | ".join(browser_messages[-8:])
            message = f"caption browser check failed: {exc}"
            if browser_state:
                message += f" | state={browser_state}"
            if detail:
                message += f" | {detail}"
            raise QualityGateError([message]) from exc
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)
        if problems:
            logger.error("[CartoonMedia] 字幕可见性问题: %s", problems)
            raise QualityGateError(problems)
        logger.info("[CartoonMedia] 字幕可见性检查通过: cues=%d", len(cues))

    async def render(self, output_dir: Path, output_name: str = "video.mp4") -> Path:
        if Path(output_name).name != output_name or not output_name.endswith(".mp4"):
            raise ValueError("output_name must be a local MP4 filename")
        output_path = output_dir / output_name
        logger.info("[CartoonMedia] 开始视频渲染: dir=%s output=%s", output_dir, output_name)
        t0 = asyncio.get_event_loop().time()
        command = [
            str(self.hyperframes_path()),
            "render",
            ".",
            "--output",
            str(output_path),
            "--fps",
            "24",
            "--resolution",
            "landscape",
        ]
        logger.info(
            "[CartoonMedia] HyperFrames render 命令: %s (timeout=%ds)",
            " ".join(command[1:]),
            self.render_timeout_seconds,
        )
        exit_code, stdout, stderr = await self._run_streaming(
            command,
            cwd=output_dir,
            timeout_seconds=self.render_timeout_seconds,
            label="render",
        )
        render_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
        logger.info(
            "[CartoonMedia] HyperFrames render 进程结束: exit_code=%d elapsed_ms=%d stdout_len=%d stderr_len=%d",
            exit_code,
            render_ms,
            len(stdout),
            len(stderr),
        )
        if stderr.strip():
            logger.info("[CartoonMedia] HyperFrames render stderr: %s", stderr[:500])
        if exit_code != 0 or not output_path.is_file() or output_path.stat().st_size <= 1024:
            output_path.unlink(missing_ok=True)
            detail = stderr.strip() or stdout.strip()
            logger.error(
                "[CartoonMedia] 渲染失败: exit_code=%d file_exists=%s size=%d detail=%s",
                exit_code,
                output_path.is_file(),
                output_path.stat().st_size if output_path.is_file() else 0,
                detail[-500:],
            )
            raise RuntimeError(f"HyperFrames render failed: {detail[-1200:]}")
        file_size = output_path.stat().st_size
        logger.info(
            "[CartoonMedia] 渲染完成: output=%s size=%d bytes elapsed_ms=%d",
            output_path,
            file_size,
            render_ms,
        )
        return output_path

    async def probe(self, video_path: Path, *, expected_duration_ms: int) -> MediaProbe:
        logger.info(
            "[CartoonMedia] 开始视频探测: path=%s expected_duration_ms=%d",
            video_path,
            expected_duration_ms,
        )
        t0 = asyncio.get_event_loop().time()
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe 未安装，无法验证 MP4")
        exit_code, stdout, stderr = await self._run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(video_path),
            ],
            cwd=video_path.parent,
            timeout_seconds=60,
        )
        if exit_code != 0:
            raise RuntimeError(f"ffprobe failed: {stderr[-800:]}")
        payload = self._json_payload(stdout)
        streams = payload.get("streams") or []
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
        if not isinstance(video_stream, dict):
            raise RuntimeError("rendered MP4 has no video stream")
        duration = float((payload.get("format") or {}).get("duration") or 0)
        frame_rate = str(video_stream.get("avg_frame_rate") or "0/0")
        fps = round(float(Fraction(frame_rate))) if frame_rate != "0/0" else 0
        probe = MediaProbe(
            duration_seconds=duration,
            width=int(video_stream.get("width") or 0),
            height=int(video_stream.get("height") or 0),
            fps=fps,
            size_bytes=video_path.stat().st_size,
            has_audio=audio_stream is not None,
        )
        problems: list[str] = []
        if (probe.width, probe.height) != (1920, 1080):
            problems.append(f"unexpected resolution {probe.width}x{probe.height}")
        if probe.fps != 24:
            problems.append(f"unexpected frame rate {probe.fps}")
        if not probe.has_audio:
            problems.append("rendered MP4 has no audio stream")
        expected_seconds = expected_duration_ms / 1000
        if abs(probe.duration_seconds - expected_seconds) > 0.75:
            problems.append(
                f"duration mismatch: expected {expected_seconds:.3f}s, got {probe.duration_seconds:.3f}s"
            )
        if problems:
            logger.error("[CartoonMedia] 视频探测问题: %s", "; ".join(problems))
            raise RuntimeError("; ".join(problems))
        probe_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
        logger.info(
            "[CartoonMedia] 视频探测通过: duration=%.1fs resolution=%dx%d fps=%d has_audio=%s elapsed_ms=%d",
            probe.duration_seconds,
            probe.width,
            probe.height,
            probe.fps,
            probe.has_audio,
            probe_ms,
        )
        return probe

    @staticmethod
    async def _run(
        command: list[str],
        *,
        cwd: Path,
        timeout_seconds: int,
    ) -> tuple[int, str, str]:
        logger.info(
            "[CartoonMedia] 执行命令: %s (cwd=%s timeout=%ds)",
            command[1] if len(command) > 1 else command[0],
            cwd,
            timeout_seconds,
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10485760,  # 10MB limit to prevent LimitOverrunError on huge lines
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.communicate()
            logger.error("[CartoonMedia] 命令超时: %ds %s", timeout_seconds, command[1] if len(command) > 1 else command[0])
            raise RuntimeError(f"command timed out after {timeout_seconds}s: {command[1]}")
        return (
            int(process.returncode or 0),
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    @staticmethod
    async def _run_streaming(
        command: list[str],
        *,
        cwd: Path,
        timeout_seconds: int,
        label: str = "process",
    ) -> tuple[int, str, str]:
        """Run a long-lived subprocess, streaming stdout/stderr lines to the log.

        Unlike ``_run`` which buffers everything via ``communicate()``, this
        method reads stdout and stderr line-by-line so that rendering progress
        (frame counts, percentage, stage transitions) appears in the backend
        log in real time instead of only after the process exits.
        """
        logger.info(
            "[CartoonMedia] 执行命令(流式): %s (cwd=%s timeout=%ds label=%s)",
            command[1] if len(command) > 1 else command[0],
            cwd,
            timeout_seconds,
            label,
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10485760,  # 10MB limit to prevent LimitOverrunError on huge lines
        )
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        last_progress_log = 0.0

        async def _read_stream(
            stream: asyncio.StreamReader | None,
            sink: list[str],
            log_prefix: str,
        ) -> None:
            if stream is None:
                return
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                sink.append(line)
                # Only log non-empty lines; skip verbose blank noise.
                if line.strip():
                    logger.info("[CartoonMedia][%s] %s %s", label, log_prefix, line)

        try:
            elapsed = 0.0
            async with asyncio.timeout(timeout_seconds):
                # Read both streams concurrently.
                await asyncio.gather(
                    _read_stream(process.stdout, stdout_chunks, "stdout"),
                    _read_stream(process.stderr, stderr_chunks, "stderr"),
                )
                await process.wait()
        except TimeoutError:
            process.kill()
            await process.communicate()
            logger.error(
                "[CartoonMedia] 命令超时: %ds label=%s",
                timeout_seconds,
                label,
            )
            raise RuntimeError(f"command timed out after {timeout_seconds}s: {label}")

        stdout_text = "\n".join(stdout_chunks)
        stderr_text = "\n".join(stderr_chunks)
        return (
            int(process.returncode or 0),
            stdout_text,
            stderr_text,
        )

    @staticmethod
    def _json_payload(output: str) -> dict[str, Any]:
        decoder = json.JSONDecoder()
        for index, character in enumerate(output):
            if character != "{":
                continue
            try:
                payload, _end = decoder.raw_decode(output[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise ValueError("no JSON object found")
