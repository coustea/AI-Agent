"""HyperFrames lint and MP4 rendering for compiled cartoon compositions."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.infra.logging import get_logger
from app.shared.cartoon.compiler import COMPOSITION_ID

logger = get_logger(__name__)


@dataclass(frozen=True)
class RenderAudit:
    passed: bool
    problems: tuple[str, ...] = ()


@dataclass(frozen=True)
class CartoonVideoRenderResult:
    video_path: Path
    duration_seconds: float
    width: int
    height: int
    fps: int
    size_bytes: int


class CartoonVideoRenderer:
    """Validate and render one already-compiled local composition."""

    def __init__(
        self,
        *,
        output_name: str = "video.mp4",
        timeout_seconds: int = 900,
        lint_timeout_seconds: int = 120,
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive"
            )

        if lint_timeout_seconds <= 0:
            raise ValueError(
                "lint_timeout_seconds must be positive"
            )

        if fps <= 0:
            raise ValueError(
                "fps must be positive"
            )

        if width <= 0 or height <= 0:
            raise ValueError(
                "renderer dimensions must be positive"
            )

        if (
            Path(output_name).name != output_name
            or not output_name.endswith(".mp4")
        ):
            raise ValueError(
                "output_name must be a local .mp4 filename"
            )

        self.output_name = output_name
        self.timeout_seconds = timeout_seconds
        self.lint_timeout_seconds = lint_timeout_seconds
        self.fps = fps
        self.width = width
        self.height = height

    @staticmethod
    def _npx_path() -> str:
        npx_path = shutil.which("npx")

        if not npx_path:
            raise RuntimeError(
                "npx 未安装或不在 PATH 中，无法调用 HyperFrames"
            )

        return npx_path

    async def lint(
        self,
        output_dir: Path,
    ) -> RenderAudit:
        html_path = output_dir / "index.html"

        if not html_path.is_file():
            return RenderAudit(
                passed=False,
                problems=(
                    f"HTML 文件不存在: {html_path}",
                ),
            )

        try:
            npx_path = self._npx_path()
        except RuntimeError as exc:
            return RenderAudit(
                passed=False,
                problems=(str(exc),),
            )

        command = [
            npx_path,
            "hyperframes",
            "lint",
            ".",
            "--json",
        ]

        try:
            from app.shared.utils.proc_logger import (
                run_process_with_logging,
            )

            return_code, stdout_str, stderr_str = (
                await run_process_with_logging(
                    command,
                    cwd=output_dir,
                    timeout_seconds=self.lint_timeout_seconds,
                    logger_name="app.shared.cartoon.lint",
                )
            )
        except Exception as exc:
            return RenderAudit(
                passed=False,
                problems=(
                    f"HyperFrames lint 执行失败: {exc}",
                ),
            )

        if return_code == 0:
            return RenderAudit(
                passed=True,
            )

        problems = self._parse_lint_problems(
            stdout_str,
            stderr_str,
        )

        return RenderAudit(
            passed=False,
            problems=tuple(problems[:12]),
        )

    async def render(
        self,
        output_dir: Path,
    ) -> CartoonVideoRenderResult:
        html_path = output_dir / "index.html"

        if not html_path.is_file():
            raise FileNotFoundError(
                f"index.html 不存在: {html_path}"
            )

        duration_seconds = self._read_duration(
            html_path
        )

        if duration_seconds <= 0:
            raise RuntimeError(
                "无法从 index.html 读取有效的视频总时长"
            )

        video_path = output_dir / self.output_name

        command = [
            self._npx_path(),
            "hyperframes",
            "render",
            ".",
            "--output",
            str(video_path),
            "--fps",
            str(self.fps),
        ]

        logger.info(
            (
                "Cartoon render start: "
                "cwd=%s composition=%s duration=%.3fs output=%s"
            ),
            output_dir,
            COMPOSITION_ID,
            duration_seconds,
            video_path,
        )

        try:
            from app.shared.utils.proc_logger import (
                run_process_with_logging,
            )

            return_code, stdout_str, stderr_str = (
                await run_process_with_logging(
                    command,
                    cwd=output_dir,
                    timeout_seconds=self.timeout_seconds,
                    logger_name="app.shared.cartoon.render",
                )
            )
        except Exception as exc:
            raise RuntimeError(
                f"HyperFrames 渲染进程执行失败: {exc}"
            ) from exc

        if return_code != 0:
            message = (
                stderr_str
                or stdout_str
                or "HyperFrames render 返回非零退出码"
            ).strip()

            raise RuntimeError(
                message[:2000]
            )

        if not video_path.is_file():
            raise RuntimeError(
                f"HyperFrames 渲染结束但未生成目标文件: {video_path}"
            )

        size_bytes = video_path.stat().st_size

        if size_bytes <= 0:
            raise RuntimeError(
                "HyperFrames 生成了空 MP4 文件"
            )

        logger.info(
            "Cartoon render complete: path=%s size=%d",
            video_path,
            size_bytes,
        )

        return CartoonVideoRenderResult(
            video_path=video_path,
            duration_seconds=duration_seconds,
            width=self.width,
            height=self.height,
            fps=self.fps,
            size_bytes=size_bytes,
        )

    async def has_audio_stream(self, video_path: Path) -> bool:
        """Require a real audio stream before an MP4 can be published."""
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe 未安装，无法验证 MP4 音轨")
        process = await asyncio.create_subprocess_exec(
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            str(video_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"ffprobe 音轨检查失败: {stderr.decode(errors='replace')[:500]}")
        payload = json.loads(stdout.decode("utf-8"))
        return bool(payload.get("streams"))

    @staticmethod
    def _parse_lint_problems(
        stdout_str: str,
        stderr_str: str,
    ) -> list[str]:
        problems: list[str] = []

        for line in stdout_str.strip().splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(payload, dict):
                continue

            errors = payload.get("errors")

            if isinstance(errors, list):
                for item in errors:
                    if isinstance(item, dict):
                        problems.append(
                            str(
                                item.get("message")
                                or item
                            )
                        )
                    else:
                        problems.append(
                            str(item)
                        )

            message = payload.get("message")

            if message:
                problems.append(
                    str(message)
                )

        if not problems:
            fallback = (
                stderr_str.strip()
                or stdout_str.strip()
                or "HyperFrames lint 失败"
            )

            problems.append(
                fallback[:1200]
            )

        return problems

    @staticmethod
    def _read_duration(
        html_path: Path,
    ) -> float:
        content = html_path.read_text(
            encoding="utf-8"
        )

        main_match = re.search(
            r"<main\b[^>]*>",
            content,
            re.IGNORECASE,
        )

        if not main_match:
            return 0.0

        duration_match = re.search(
            r'data-duration\s*=\s*["\']([^"\']+)["\']',
            main_match.group(0),
            re.IGNORECASE,
        )

        if not duration_match:
            return 0.0

        try:
            return float(
                duration_match.group(1)
            )
        except ValueError:
            return 0.0
