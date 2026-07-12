"""HyperFrames lint and deterministic MP4 rendering."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from app.infra.logging import get_logger
from app.shared.cartoon.compiler import (
    COMPOSITION_ID,
)

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
        probe_timeout_seconds: int = 30,
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds "
                "must be positive"
            )

        if lint_timeout_seconds <= 0:
            raise ValueError(
                "lint_timeout_seconds "
                "must be positive"
            )

        if probe_timeout_seconds <= 0:
            raise ValueError(
                "probe_timeout_seconds "
                "must be positive"
            )

        if fps <= 0:
            raise ValueError(
                "fps must be positive"
            )

        if (
            width <= 0
            or height <= 0
        ):
            raise ValueError(
                "renderer dimensions "
                "must be positive"
            )

        if (
            Path(output_name).name
            != output_name
            or not output_name.endswith(
                ".mp4"
            )
        ):
            raise ValueError(
                "output_name must be "
                "a local .mp4 filename"
            )

        self.output_name = (
            output_name
        )

        self.timeout_seconds = (
            timeout_seconds
        )

        self.lint_timeout_seconds = (
            lint_timeout_seconds
        )

        self.probe_timeout_seconds = (
            probe_timeout_seconds
        )

        self.fps = fps
        self.width = width
        self.height = height

    @staticmethod
    def _npx_path() -> str:
        npx_path = shutil.which(
            "npx"
        )

        if not npx_path:
            raise RuntimeError(
                "npx 未安装或不在 PATH 中，"
                "无法调用 HyperFrames"
            )

        return npx_path

    async def lint(
        self,
        output_dir: Path,
    ) -> RenderAudit:
        html_path = (
            output_dir
            / "index.html"
        )

        if not html_path.is_file():
            return RenderAudit(
                False,
                (
                    f"HTML 文件不存在: "
                    f"{html_path}",
                ),
            )

        try:
            command = [
                self._npx_path(),
                "hyperframes",
                "lint",
                ".",
                "--json",
            ]

        except RuntimeError as exc:
            return RenderAudit(
                False,
                (
                    str(exc),
                ),
            )

        try:
            from app.shared.utils.proc_logger import (
                run_process_with_logging,
            )

            (
                return_code,
                stdout_str,
                stderr_str,
            ) = await run_process_with_logging(
                command,
                cwd=output_dir,
                timeout_seconds=(
                    self.lint_timeout_seconds
                ),
                logger_name=(
                    "app.shared.cartoon.lint"
                ),
            )

        except Exception as exc:
            return RenderAudit(
                False,
                (
                    "HyperFrames lint "
                    f"执行失败: {exc}",
                ),
            )

        if return_code == 0:
            return RenderAudit(
                True
            )

        return RenderAudit(
            False,
            tuple(
                self._parse_lint_problems(
                    stdout_str,
                    stderr_str,
                )[:12]
            ),
        )

    async def render(
        self,
        output_dir: Path,
    ) -> CartoonVideoRenderResult:
        html_path = (
            output_dir
            / "index.html"
        )

        if not html_path.is_file():
            raise FileNotFoundError(
                "index.html 不存在: "
                f"{html_path}"
            )

        expected_duration = (
            self._read_duration(
                html_path
            )
        )

        if expected_duration <= 0:
            raise RuntimeError(
                "无法从 index.html 读取"
                "有效的视频总时长"
            )

        video_path = (
            output_dir
            / self.output_name
        )

        temporary_path = (
            output_dir
            / (
                f".{video_path.stem}"
                ".rendering.mp4"
            )
        )

        temporary_path.unlink(
            missing_ok=True
        )

        video_path.unlink(
            missing_ok=True
        )

        command = self._render_command(
            temporary_path
        )

        logger.info(
            (
                "Cartoon render start: "
                "cwd=%s composition=%s "
                "duration=%.3fs output=%s"
            ),
            output_dir,
            COMPOSITION_ID,
            expected_duration,
            video_path,
        )

        try:
            from app.shared.utils.proc_logger import (
                run_process_with_logging,
            )

            (
                return_code,
                stdout_str,
                stderr_str,
            ) = await run_process_with_logging(
                command,
                cwd=output_dir,
                timeout_seconds=max(
                    self.timeout_seconds,
                    round(
                        expected_duration
                        * 8
                    ),
                ),
                logger_name=(
                    "app.shared.cartoon.render"
                ),
            )

        except Exception as exc:
            temporary_path.unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "HyperFrames 渲染进程"
                f"执行失败: {exc}"
            ) from exc

        if return_code != 0:
            temporary_path.unlink(
                missing_ok=True
            )

            message = (
                stderr_str
                or stdout_str
                or (
                    "HyperFrames render "
                    "返回非零退出码"
                )
            ).strip()

            raise RuntimeError(
                message[:2000]
            )

        if not temporary_path.is_file():
            raise RuntimeError(
                "HyperFrames 渲染结束但"
                "未生成目标文件: "
                f"{temporary_path}"
            )

        if (
            temporary_path.stat().st_size
            <= 1024
        ):
            temporary_path.unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "HyperFrames 生成的 "
                "MP4 文件异常为空"
            )

        temporary_path.replace(
            video_path
        )

        media = await self._probe_media(
            video_path
        )

        streams = media.get(
            "streams",
            [],
        )

        video_stream = next(
            (
                stream
                for stream in streams
                if stream.get(
                    "codec_type"
                )
                == "video"
            ),
            None,
        )

        if not video_stream:
            raise RuntimeError(
                "ffprobe 未检测到视频轨"
            )

        width = int(
            video_stream.get(
                "width"
            )
            or 0
        )

        height = int(
            video_stream.get(
                "height"
            )
            or 0
        )

        fps = self._parse_fps(
            video_stream.get(
                "avg_frame_rate"
            )
        )

        duration = float(
            (
                media.get("format")
                or {}
            ).get(
                "duration"
            )
            or 0
        )

        if (
            width != self.width
            or height != self.height
        ):
            raise RuntimeError(
                "渲染分辨率异常: "
                f"expected="
                f"{self.width}x{self.height}, "
                f"actual={width}x{height}"
            )

        if (
            fps is None
            or abs(
                fps
                - self.fps
            )
            > 1
        ):
            raise RuntimeError(
                "渲染帧率异常: "
                f"expected={self.fps}, "
                f"actual={fps}"
            )

        if duration <= 0:
            raise RuntimeError(
                "ffprobe 未读取到"
                "有效视频时长"
            )

        duration_tolerance = max(
            1.2,
            expected_duration
            * 0.05,
        )

        if abs(
            duration
            - expected_duration
        ) > duration_tolerance:
            raise RuntimeError(
                "渲染时长与 composition "
                "不一致: "
                f"expected="
                f"{expected_duration:.3f}s, "
                f"actual={duration:.3f}s"
            )

        size_bytes = (
            video_path.stat().st_size
        )

        logger.info(
            (
                "Cartoon render complete: "
                "path=%s size=%d "
                "duration=%.3f "
                "width=%d height=%d fps=%d"
            ),
            video_path,
            size_bytes,
            duration,
            width,
            height,
            fps,
        )

        return CartoonVideoRenderResult(
            video_path=video_path,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            size_bytes=size_bytes,
        )

    async def has_audio_stream(
        self,
        video_path: Path,
    ) -> bool:
        media = await self._probe_media(
            video_path
        )

        return any(
            stream.get(
                "codec_type"
            )
            == "audio"
            for stream
            in media.get(
                "streams",
                [],
            )
        )

    def _render_command(
        self,
        output_path: Path,
    ) -> list[str]:
        command = [
            self._npx_path(),
            "hyperframes",
            "render",
            ".",
            "--output",
            str(
                output_path
            ),
            "--fps",
            str(
                self.fps
            ),
        ]

        resolution = (
            self._resolution_preset()
        )

        if resolution:
            command.extend(
                [
                    "--resolution",
                    resolution,
                ]
            )

        return command

    def _resolution_preset(
        self,
    ) -> str | None:
        presets = {
            (1920, 1080): "landscape",
            (3840, 2160): "landscape-4k",
            (1080, 1920): "portrait",
            (2160, 3840): "portrait-4k",
            (1080, 1080): "square",
            (2160, 2160): "square-4k",
        }

        return presets.get(
            (
                self.width,
                self.height,
            )
        )

    async def _probe_media(
        self,
        video_path: Path,
    ) -> dict:
        ffprobe = shutil.which(
            "ffprobe"
        )

        if not ffprobe:
            raise RuntimeError(
                "ffprobe 未安装，"
                "无法验证 MP4"
            )

        process = (
            await asyncio.create_subprocess_exec(
                ffprobe,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(
                    video_path
                ),
                stdout=(
                    asyncio.subprocess.PIPE
                ),
                stderr=(
                    asyncio.subprocess.PIPE
                ),
            )
        )

        try:
            stdout, stderr = (
                await asyncio.wait_for(
                    process.communicate(),
                    timeout=(
                        self.probe_timeout_seconds
                    ),
                )
            )

        except TimeoutError as exc:
            process.kill()

            await process.communicate()

            raise RuntimeError(
                "ffprobe 检查超时"
            ) from exc

        if process.returncode != 0:
            raise RuntimeError(
                "ffprobe 检查失败: "
                f"{stderr.decode(errors='replace')[:500]}"
            )

        try:
            payload = json.loads(
                stdout.decode(
                    "utf-8"
                )
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "ffprobe 返回了无效 JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                "ffprobe 返回结果格式无效"
            )

        return payload

    @staticmethod
    def _parse_fps(
        value: object,
    ) -> int | None:
        if (
            not value
            or not isinstance(
                value,
                str,
            )
            or value == "0/0"
        ):
            return None

        try:
            return round(
                float(
                    Fraction(
                        value
                    )
                )
            )

        except (
            ValueError,
            ZeroDivisionError,
        ):
            return None

    @staticmethod
    def _parse_lint_problems(
        stdout_str: str,
        stderr_str: str,
    ) -> list[str]:
        def extract(
            payload: object,
        ) -> list[str]:
            if not isinstance(
                payload,
                dict,
            ):
                return []

            messages: list[str] = []

            for field in (
                "errors",
                "findings",
            ):
                findings = payload.get(
                    field
                )

                if not isinstance(
                    findings,
                    list,
                ):
                    continue

                for item in findings:
                    if not isinstance(
                        item,
                        dict,
                    ):
                        messages.append(
                            str(item)
                        )
                        continue

                    if (
                        field == "findings"
                        and item.get(
                            "severity"
                        )
                        not in {
                            "error",
                            "fatal",
                        }
                    ):
                        continue

                    messages.append(
                        str(
                            item.get(
                                "message"
                            )
                            or item
                        )
                    )

            if payload.get(
                "message"
            ):
                messages.append(
                    str(
                        payload[
                            "message"
                        ]
                    )
                )

            return messages

        try:
            problems = extract(
                json.loads(
                    stdout_str
                )
            )

        except json.JSONDecodeError:
            problems = []

        if problems:
            return problems

        problems = []

        for line in (
            stdout_str
            .strip()
            .splitlines()
        ):
            try:
                payload = json.loads(
                    line
                )

            except json.JSONDecodeError:
                continue

            problems.extend(
                extract(
                    payload
                )
            )

        if not problems:
            problems.append(
                (
                    stderr_str.strip()
                    or stdout_str.strip()
                    or "HyperFrames lint 失败"
                )[:1200]
            )

        return problems

    @staticmethod
    def _read_duration(
        html_path: Path,
    ) -> float:
        content = (
            html_path.read_text(
                encoding="utf-8"
            )
        )

        main_match = re.search(
            r"<main\b[^>]*>",
            content,
            re.IGNORECASE,
        )

        if not main_match:
            return 0.0

        duration_match = re.search(
            (
                r'data-duration\s*=\s*'
                r'["\']([^"\']+)["\']'
            ),
            main_match.group(0),
            re.IGNORECASE,
        )

        if not duration_match:
            return 0.0

        try:
            return float(
                duration_match.group(
                    1
                )
            )

        except ValueError:
            return 0.0
