"""HyperFrames renderer for the cartoon video generation pipeline.

Executes the HyperFrames CLI (via npx) to render the HTML composition
(with programmatically injected audio elements) into a final MP4 video.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.infra.logging import get_logger

logger = get_logger(__name__)


class CartoonRenderError(RuntimeError):
    """Raised when HyperFrames rendering fails or outputs an invalid artifact."""
    pass


class CartoonVideoRenderer:
    """Invokes the HyperFrames CLI to render HTML & audio compositions to MP4."""

    def __init__(self, timeout_seconds: int = 300, workers: int = 4) -> None:
        self.timeout_seconds = timeout_seconds
        self.workers = workers

    async def render(self, output_dir: Path) -> Path:
        """Render the index.html inside output_dir into video.mp4.

        Args:
            output_dir: The directory containing index.html and audio/*.mp3.

        Returns:
            The Path to the final rendered video.mp4.
        """
        html_file = output_dir / "index.html"
        if not html_file.is_file():
            raise CartoonRenderError(f"Composition HTML is missing: {html_file}")

        final_output = output_dir / "video.mp4"
        
        # Build rendering command: npx hyperframes render index.html -o video.mp4 --workers 4
        command = [
            "npx",
            "hyperframes",
            "render",
            "index.html",
            "-o",
            "video.mp4",
            "--workers",
            str(self.workers),
        ]

        logger.info(
            "Starting HyperFrames rendering in %s: %s",
            output_dir,
            " ".join(command),
        )

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(output_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise CartoonRenderError(
                f"HyperFrames render timed out after {self.timeout_seconds} seconds"
            ) from exc

        return_code = process.returncode or 0
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if return_code != 0:
            logger.error("HyperFrames render failed. Stderr: %s", stderr_str)
            raise CartoonRenderError(
                f"HyperFrames rendering process failed with code {return_code}: {stderr_str}"
            )

        if not final_output.is_file() or final_output.stat().st_size == 0:
            raise CartoonRenderError("HyperFrames CLI completed but did not produce a valid video.mp4")

        logger.info(
            "HyperFrames rendering complete! Generated: %s (Size: %d bytes)",
            final_output,
            final_output.stat().st_size,
        )
        return final_output
