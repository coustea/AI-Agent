"""Remotion renderer for strict video/v2 teaching-video plans."""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from pathlib import Path

from app.config import (
    VIDEO_RENDER_CHROMIUM_GL,
    VIDEO_RENDER_CONCURRENCY,
    VIDEO_RENDER_TIMEOUT_SECONDS,
    WORKPLACE_DIR,
)
from app.infra.logging import get_logger
from app.shared.video.schemas import VideoArtifact, VideoPlan

logger = get_logger(__name__)

REPOSITORY_DIR = Path(__file__).resolve().parents[4]
REMOTION_DIR = REPOSITORY_DIR / "video-render"
ALLOWED_GL_BACKENDS = {"angle", "swiftshader", "egl"}


class VideoRenderError(RuntimeError):
    """Raised when Remotion fails or produces an invalid media artifact."""


async def _run_process(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int,
) -> tuple[int, str, str]:
    import platform
    cmd = command.copy()
    if cmd and not Path(cmd[0]).is_absolute():
        resolved = shutil.which(cmd[0])
        if resolved:
            cmd[0] = resolved
        elif platform.system() == "Windows" and cmd[0] == "npx":
            cmd[0] = "npx.cmd"

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


class RemotionVideoRenderer:
    def __init__(
        self,
        *,
        remotion_dir: Path = REMOTION_DIR,
        timeout_seconds: int = VIDEO_RENDER_TIMEOUT_SECONDS,
        concurrency: int = VIDEO_RENDER_CONCURRENCY,
        chromium_gl: str = VIDEO_RENDER_CHROMIUM_GL,
    ) -> None:
        if chromium_gl not in ALLOWED_GL_BACKENDS:
            raise ValueError(f"unsupported Chromium GL backend: {chromium_gl}")
        self.remotion_dir = remotion_dir
        self.timeout_seconds = timeout_seconds
        self.concurrency = concurrency
        self.chromium_gl = chromium_gl

    async def render(self, plan: VideoPlan, output_dir: Path) -> VideoArtifact:
        if not (self.remotion_dir / "package.json").is_file():
            raise VideoRenderError("video-render project is missing")

        output_dir.mkdir(parents=True, exist_ok=True)
        job_dir = output_dir / f".render-{uuid.uuid4().hex}"
        job_dir.mkdir(parents=True)
        public_asset_dir = (
            self.remotion_dir / "public" / "render-assets" / job_dir.name
        )
        public_asset_dir.mkdir(parents=True)
        plan_path = job_dir / "video-plan.json"
        temporary_output = job_dir / "output.mp4"
        final_output = output_dir / "video.mp4"
        render_payload = plan.model_dump(mode="json")
        for scene in render_payload["scenes"]:
            audio_src = str(scene["audio_src"])
            if not audio_src.startswith("/static/"):
                raise VideoRenderError(
                    f"scene audio must use a /static/ URL: {audio_src}"
                )
            source_audio = (
                WORKPLACE_DIR / audio_src.removeprefix("/static/")
            ).resolve()
            try:
                source_audio.relative_to(WORKPLACE_DIR.resolve())
            except ValueError as exc:
                raise VideoRenderError("scene audio escapes WORKPLACE_DIR") from exc
            if not source_audio.is_file():
                raise VideoRenderError(f"scene audio is missing: {source_audio}")
            staged_name = f"{scene['index']:02d}-{source_audio.name}"
            shutil.copy2(source_audio, public_asset_dir / staged_name)
            scene["audio_src"] = (
                f"/render-assets/{job_dir.name}/{staged_name}"
            )
        plan_path.write_text(
            json.dumps(render_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        import platform
        npx_cmd = "npx.cmd" if platform.system() == "Windows" else "npx"
        command = [
            npx_cmd,
            "tsx",
            str(self.remotion_dir / "scripts" / "render.ts"),
            "--input",
            str(plan_path),
            "--output",
            str(temporary_output),
            "--gl",
            self.chromium_gl,
            "--concurrency",
            str(self.concurrency),
        ]
        try:
            from app.shared.utils.proc_logger import run_process_with_logging
            code, stdout_text, stderr_text = await run_process_with_logging(
                command,
                cwd=self.remotion_dir,
                timeout_seconds=self.timeout_seconds,
                logger_name="app.shared.video.render",
            )
            if code != 0:
                raise VideoRenderError(
                    f"Remotion render failed: {stderr_text[-1200:].strip()}"
                )
            if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
                raise VideoRenderError("Remotion did not produce an MP4 file")

            streams = await self._probe_streams(temporary_output)
            stream_types = {stream.get("codec_type") for stream in streams}
            if "video" not in stream_types:
                raise VideoRenderError("rendered MP4 has no video stream")
            if "audio" not in stream_types:
                raise VideoRenderError("rendered MP4 has no audio stream")

            temporary_output.replace(final_output)
        except asyncio.TimeoutError as exc:
            raise VideoRenderError(
                f"Remotion render timed out after {self.timeout_seconds}s"
            ) from exc
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)
            shutil.rmtree(public_asset_dir, ignore_errors=True)

        relative = final_output.resolve().relative_to(WORKPLACE_DIR.resolve())
        return VideoArtifact(
            plan=plan,
            mp4_path=final_output,
            public_url=f"/static/{relative.as_posix()}",
            duration_ms=plan.duration_ms,
            width=plan.render.width,
            height=plan.render.height,
            size_bytes=final_output.stat().st_size,
            metadata={
                "schema_version": plan.schema_version,
                "video_codec": plan.render.video_codec,
                "audio_codec": plan.render.audio_codec,
            },
        )

    async def _probe_streams(self, path: Path) -> list[dict[str, object]]:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ]
        code, stdout, stderr = await _run_process(
            command,
            timeout_seconds=30,
        )
        if code != 0:
            raise VideoRenderError(f"ffprobe failed: {stderr[-600:].strip()}")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise VideoRenderError("ffprobe returned invalid JSON") from exc
        streams = payload.get("streams")
        if not isinstance(streams, list):
            raise VideoRenderError("ffprobe returned no stream list")
        return streams
