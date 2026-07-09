"""Render HyperFrames HTML composition to MP4.

renderer 只负责渲染和 lint，不参与内容生成。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.infra.logging import get_logger
from app.shared.cartoon.cartoon_agent import AuditResult

logger = get_logger(__name__)


@dataclass(frozen=True)
class CartoonRenderResult:
    video_path: Path
    duration: float
    width: int
    height: int
    fps: int


class CartoonVideoRenderer:
    """Render HyperFrames HTML composition to MP4 using npx hyperframes."""

    def __init__(
        self,
        *,
        output_name: str = "output.mp4",
        timeout_seconds: int = 600,
        fps: int = 30,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        self.output_name = output_name
        self.timeout_seconds = timeout_seconds
        self.fps = fps
        self.width = width
        self.height = height

    async def lint(self, output_dir: Path) -> AuditResult:
        """Run HyperFrames lint on the output directory."""
        html_path = output_dir / "index.html"
        if not html_path.is_file():
            return AuditResult(
                passed=False,
                problems=[f"HTML 文件不存在: {html_path}"],
            )

        npx_path = shutil.which("npx")
        if not npx_path:
            return AuditResult(
                passed=False,
                problems=["npx 未安装或不在 PATH 中，无法运行 HyperFrames CLI"],
            )

        command = [npx_path, "--no-install", "hyperframes", "lint", ".", "--json"]

        try:
            from app.shared.utils.proc_logger import run_process_with_logging

            return_code, stdout_str, stderr_str = await run_process_with_logging(
                command,
                cwd=output_dir,
                timeout_seconds=90,
                logger_name="app.shared.cartoon.lint",
            )
        except Exception as exc:
            return AuditResult(
                passed=False,
                problems=[f"HyperFrames lint 执行失败: {exc}"],
            )

        if return_code == 0:
            return AuditResult(passed=True, problems=[])

        # Parse lint errors from JSON output
        problems: list[str] = []
        for line in stdout_str.strip().splitlines():
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    errors = payload.get("errors", [])
                    for item in errors if isinstance(errors, list) else []:
                        msg = item.get("message", str(item)) if isinstance(item, dict) else str(item)
                        problems.append(str(msg))
                    if payload.get("message"):
                        problems.append(str(payload["message"]))
            except json.JSONDecodeError:
                continue

        if not problems:
            problems.append(
                (stderr_str.strip() or stdout_str.strip() or "HyperFrames lint 返回非零退出码")[:600]
            )

        return AuditResult(passed=False, problems=problems[:10])

    async def render(self, output_dir: Path) -> CartoonRenderResult:
        """Render HyperFrames composition to MP4."""
        html_path = output_dir / "index.html"
        if not html_path.is_file():
            raise FileNotFoundError(f"index.html 不存在: {html_path}")

        duration = self._read_duration(html_path)
        video_path = output_dir / self.output_name

        npx_path = shutil.which("npx")
        if not npx_path:
            raise RuntimeError("npx 未安装或不在 PATH 中，无法调用 HyperFrames 渲染")

        command = [
            npx_path,
            "--no-install",
            "hyperframes",
            "render",
            ".",
            "--composition",
            "cartoon-explainer",
            "--output",
            str(video_path),
            "--fps",
            str(self.fps),
            "--width",
            str(self.width),
            "--height",
            str(self.height),
        ]

        logger.info(
            "Cartoon 渲染开始: cwd=%s duration=%.1fs output=%s",
            output_dir,
            duration,
            video_path,
        )

        try:
            from app.shared.utils.proc_logger import run_process_with_logging

            return_code, stdout_str, stderr_str = await run_process_with_logging(
                command,
                cwd=output_dir,
                timeout_seconds=self.timeout_seconds,
                logger_name="app.shared.cartoon.render",
            )
        except Exception as exc:
            logger.exception("HyperFrames 渲染进程启动失败")
            raise RuntimeError(f"HyperFrames 渲染失败: {exc}") from exc

        if return_code != 0:
            message = (stderr_str or stdout_str or "HyperFrames render 返回非零退出码").strip()
            raise RuntimeError(message[:1600])

        if not video_path.is_file():
            candidates = sorted(output_dir.rglob("*.mp4"))
            if candidates:
                video_path = candidates[0]
            else:
                raise RuntimeError("HyperFrames 渲染完成但未找到 MP4 文件")

        logger.info("Cartoon 渲染完成: %s", video_path)

        return CartoonRenderResult(
            video_path=video_path,
            duration=duration,
            width=self.width,
            height=self.height,
            fps=self.fps,
        )

    @staticmethod
    def _read_duration(html_path: Path) -> float:
        """Read data-duration from the HTML composition root."""
        content = html_path.read_text(encoding="utf-8")
        match = re.search(r'data-duration="([^"]+)"', content)
        if not match:
            return 0.0
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
