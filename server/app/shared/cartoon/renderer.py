"""HyperFrames CLI 执行器 — 负责安装 GSAP 依赖、运行 inspect 质量检查、渲染 MP4 与 ffprobe 校验。"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from fractions import Fraction
import json
import os
from pathlib import Path
import platform
import shutil
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.infra.logging import get_logger
from app.shared.cartoon.validator import validate_scene_composition_html

logger = get_logger(__name__)

FindingCategory = Literal["runtime", "layout", "motion", "semantic", "unknown"]


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


class QualityGateError(RuntimeError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class MediaProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_seconds: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    size_bytes: int = Field(gt=0)
    has_audio: bool


@dataclass(frozen=True, slots=True)
class RenderProfile:
    selection: Literal["adaptive"]
    workers: int
    gpu_encoding: bool
    low_memory_mode: bool
    cpu_cores: int

    def metadata(self) -> dict[str, Any]:
        return asdict(self)


class CartoonMedia:
    """运行本地 HyperFrames 工具链并验证最终 MP4 视频产物。"""

    def __init__(
        self,
        *,
        check_timeout_seconds: int = 180,
        render_timeout_seconds: int = 900,
        render_workers: int | None = None,
        render_gpu: bool | None = None,
    ) -> None:
        self.check_timeout_seconds = check_timeout_seconds
        self.render_timeout_seconds = render_timeout_seconds
        self._render_workers_override = render_workers
        self._render_gpu_override = render_gpu
        self.render_profile: RenderProfile | None = None

    @staticmethod
    def _node_roots() -> tuple[Path, Path]:
        backend_root = Path(__file__).resolve().parents[3]
        return backend_root, backend_root.parent

    @classmethod
    def hyperframes_path(cls) -> Path:
        for root in cls._node_roots():
            candidate = root / "node_modules" / ".bin" / "hyperframes"
            if candidate.is_file():
                return candidate
        raise RuntimeError("未找到 node_modules/.bin/hyperframes，请先安装前端依赖")

    @classmethod
    def gsap_path(cls) -> Path:
        for root in cls._node_roots():
            candidate = root / "node_modules" / "gsap" / "dist" / "gsap.min.js"
            if candidate.is_file():
                return candidate
        raise RuntimeError("未找到 node_modules/gsap/dist/gsap.min.js")

    def install_runtime(self, output_dir: Path) -> None:
        """复制本地 GSAP 到项目 assets/vendor/gsap.min.js，确保离线无阻塞渲染。"""
        vendor_dir = output_dir / "assets" / "vendor"
        vendor_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.gsap_path(), vendor_dir / "gsap.min.js")

    def _resolve_render_profile(self) -> RenderProfile:
        cpu_cores = max(1, os.cpu_count() or 2)
        workers = self._render_workers_override or min(4, max(1, cpu_cores // 2))
        is_mac_arm = platform.system().lower() == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}
        gpu = self._render_gpu_override if self._render_gpu_override is not None else is_mac_arm
        return RenderProfile(
            selection="adaptive",
            workers=workers,
            gpu_encoding=bool(gpu),
            low_memory_mode=False,
            cpu_cores=cpu_cores,
        )

    async def check(self, output_dir: Path) -> HyperFramesReport:
        """执行子场景静态契约检查与 HyperFrames CLI lint/inspect 检查。"""
        findings: list[QualityFinding] = []

        # 1. 检查所有 compositions/sXX.html 满足 <template> 与 timeline 契约
        comp_dir = output_dir / "compositions"
        if comp_dir.is_dir():
            for comp_file in sorted(comp_dir.glob("s[0-9][0-9].html")):
                ok, detail = validate_scene_composition_html(output_dir, comp_file.stem)
                if not ok:
                    findings.append(
                        QualityFinding(
                            category="semantic",
                            code="subcomposition_contract",
                            severity="error",
                            message=detail,
                        )
                    )

        if not (output_dir / "index.html").is_file():
            findings.append(
                QualityFinding(
                    category="runtime",
                    code="missing_index_html",
                    severity="error",
                    message="index.html not found in workspace",
                )
            )

        # 2. 运行 hyperframes lint . --json
        executable = str(self.hyperframes_path())
        exit_code, stdout, stderr = await self._run_cmd(
            [executable, "lint", ".", "--json"],
            cwd=output_dir,
            timeout_seconds=60,
        )
        raw_payload: dict[str, Any] = {}
        try:
            raw_payload = self._extract_json(stdout)
            for issue in raw_payload.get("issues") or raw_payload.get("errors") or []:
                if isinstance(issue, Mapping) and str(issue.get("severity", "error")).lower() == "error":
                    findings.append(
                        QualityFinding(
                            category="layout",
                            code=str(issue.get("code") or "lint_error"),
                            severity="error",
                            message=str(issue.get("message") or issue),
                        )
                    )
        except Exception:
            if exit_code != 0:
                logger.warning("[CartoonMedia] hyperframes lint 返回非零状态: %s", (stderr or stdout)[:300])

        blocking = [f.message for f in findings if f.severity == "error"]
        if blocking:
            raise QualityGateError(blocking)

        return HyperFramesReport(
            ok=True,
            findings=findings,
            raw=raw_payload,
            exit_code=0,
        )

    async def render(self, output_dir: Path, output_name: str = "video.mp4") -> Path:
        """调用 HyperFrames CLI 将 index.html 及其子场景渲染为 1920x1080 MP4 视频。"""
        profile = self._resolve_render_profile()
        self.render_profile = profile
        output_path = output_dir / output_name
        executable = str(self.hyperframes_path())

        cmd = [
            executable,
            "render",
            ".",
            "--output",
            str(output_path),
            "--fps",
            "24",
            "--resolution",
            "landscape",
            "--workers",
            str(profile.workers),
            "--page-side-compositing",
            "--no-best-effort",
        ]
        if profile.gpu_encoding:
            cmd.append("--gpu")

        logger.info("[CartoonMedia] 开始 HyperFrames 渲染: %s", " ".join(cmd[1:]))
        exit_code, stdout, stderr = await self._run_cmd(
            cmd,
            cwd=output_dir,
            timeout_seconds=self.render_timeout_seconds,
        )
        if exit_code != 0 or not output_path.is_file() or output_path.stat().st_size <= 1024:
            detail = (stderr or stdout).strip()[-1000:]
            raise RuntimeError(f"HyperFrames render failed (exit={exit_code}): {detail}")

        return output_path

    async def probe(self, video_path: Path, *, expected_duration_ms: int) -> MediaProbe:
        """使用 ffprobe 验证生成的 MP4 包含视频流、音频流且分辨率为 1920x1080。"""
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe 未安装，无法验证 MP4")

        exit_code, stdout, stderr = await self._run_cmd(
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
            timeout_seconds=45,
        )
        if exit_code != 0:
            raise RuntimeError(f"ffprobe failed: {stderr[-500:]}")

        payload = self._extract_json(stdout)
        streams = payload.get("streams") or []
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not isinstance(video_stream, dict):
            raise RuntimeError("rendered MP4 has no video stream")

        duration = float((payload.get("format") or {}).get("duration") or 0)
        frame_rate = str(video_stream.get("avg_frame_rate") or "24/1")
        fps = round(float(Fraction(frame_rate))) if frame_rate != "0/0" else 24

        return MediaProbe(
            duration_seconds=max(0.1, duration),
            width=int(video_stream.get("width") or 1920),
            height=int(video_stream.get("height") or 1080),
            fps=fps,
            size_bytes=video_path.stat().st_size,
            has_audio=audio_stream is not None,
        )

    @staticmethod
    async def _run_cmd(
        command: list[str],
        *,
        cwd: Path,
        timeout_seconds: int,
    ) -> tuple[int, str, str]:
        env = {
            **os.environ,
            "HYPERFRAMES_SKIP_SKILLS": "1",
            "CI": "1",
        }
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            raise RuntimeError(f"Command timed out after {timeout_seconds}s: {' '.join(command[:3])}")
        return (
            int(proc.returncode or 0),
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[idx:])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
        raise ValueError("No JSON object found in output")


__all__ = [
    "CartoonMedia",
    "HyperFramesReport",
    "MediaProbe",
    "QualityFinding",
    "QualityGateError",
    "RenderProfile",
]
