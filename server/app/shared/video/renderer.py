"""Remotion renderer for strict video/v2 teaching-video plans."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import subprocess
import uuid
from functools import lru_cache
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


# ---------------------------------------------------------------------------
# GPU 自动检测 — 与 cartoon 渲染器保持一致的检测逻辑
# ---------------------------------------------------------------------------


# 探测本机 FFmpeg 支持的编码器列表（小写）
def _ffmpeg_encoders() -> str:
    """探测本机 FFmpeg 支持的编码器列表（小写）。"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return ""
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return f"{result.stdout}\n{result.stderr}".lower()


# 判断 Linux/Windows 是否存在可用的 NVIDIA GPU 与 NVENC 编码器
def _nvidia_gpu_available(encoders: str) -> bool:
    """判断 Linux/Windows 是否存在可用的 NVIDIA GPU 与 NVENC 编码器。"""
    system = platform.system()
    if system not in {"Linux", "Windows"} or "h264_nvenc" not in encoders:
        return False

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None and system == "Windows":
        default_path = Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe")
        if default_path.is_file():
            nvidia_smi = str(default_path)

    if nvidia_smi is None:
        return False
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


# 探测 GPU 并选择最合适的 Chromium GL 后端（Ubuntu Linux 优先）
@lru_cache(maxsize=1)
def detect_chromium_gl_backend(configured: str | None = None) -> str:
    """探测 GPU 并选择最合适的 Chromium GL 后端（针对 Ubuntu Linux 优化）。

    Remotion 官方文档在 GPU 渲染场景下统一推荐 ``angle`` 后端
    (webgl2-context / shaders / three / skia / html-in-canvas 等），
    ANGLE 在 Linux NVIDIA 上经由 Vulkan/OpenGL 后端访问 GPU，兼容性最佳。
    参考: https://www.remotion.dev/docs/troubleshooting/webgl2-context

    优先级（Ubuntu 优先）：
    1. 显式配置（config.yaml 中 chromium_gl 非默认值）始终生效
    2. 检测到 NVIDIA GPU（NVENC + nvidia-smi）→ angle（Remotion 推荐的 GPU 后端）
    3. 无 GPU → swiftshader（纯软件渲染，确保 headless 下也能出帧）

    Args:
        configured: 来自 config.yaml 的显式配置值，为 None 时读取全局配置。

    Returns:
        合法的 GL 后端名称，必定属于 ALLOWED_GL_BACKENDS。
    """
    # 显式配置优先（用户在 config.yaml 中手动设置时尊重其选择）
    # 配置值非法时回退到 angle
    explicit = configured if configured is not None else VIDEO_RENDER_CHROMIUM_GL
    if explicit not in ALLOWED_GL_BACKENDS:
        explicit = "angle"

    encoders = _ffmpeg_encoders()
    has_gpu = _nvidia_gpu_available(encoders)

    # Ubuntu Linux + NVIDIA GPU：使用 Remotion 官方推荐的 angle 后端
    # 无 GPU 时退回 swiftshader，保证 headless 环境也能完成渲染
    # 依据 GPU 检测结果选择最终 GL 后端
    chosen = "angle" if has_gpu else "swiftshader"

    logger.info(
        "Chromium GL 后端选择 (Ubuntu 优先): configured=%s, gpu_detected=%s, chosen=%s",
        explicit,
        has_gpu,
        chosen,
    )
    return chosen


# 渲染失败时抛出的异常类型
class VideoRenderError(RuntimeError):
    """Raised when Remotion fails or produces an invalid media artifact."""


# 通用子进程运行封装：解析命令、设置超时并返回标准输出/错误
async def _run_process(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int,
) -> tuple[int, str, str]:
    import platform
    cmd = command.copy()
    # 解析相对命令路径，Windows 下 npx 需使用 npx.cmd
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
    # 等待子进程完成，超时则强制终止
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    # 超时处理：杀掉进程并向上抛出
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


# Remotion 渲染器：将视频计划交给 render.ts 渲染为 MP4
class RemotionVideoRenderer:
    def __init__(
        self,
        *,
        remotion_dir: Path = REMOTION_DIR,
        timeout_seconds: int = VIDEO_RENDER_TIMEOUT_SECONDS,
        concurrency: int = VIDEO_RENDER_CONCURRENCY,
        chromium_gl: str | None = None,
        auto_detect_gl: bool = True,
    ) -> None:
        """初始化 Remotion 渲染器。

        Args:
            remotion_dir: video-render 项目根目录。
            timeout_seconds: 单次渲染最大超时（秒）。
            concurrency: Remotion 并发数。
            chromium_gl: 显式指定 Chromium GL 后端。None 表示由配置或自动检测决定。
            auto_detect_gl: 是否在渲染时自动探测 GPU 选择最优 GL 后端。
                当 chromium_gl 显式指定时，自动检测不再覆盖该值。
        """
        self.remotion_dir = remotion_dir
        self.timeout_seconds = timeout_seconds
        self.concurrency = concurrency
        self._explicit_gl = chromium_gl
        self.auto_detect_gl = auto_detect_gl
        # 初始值：优先显式参数，其次配置默认值；运行时可能被自动检测覆盖
        # 校验显式 GL 后端合法性，非法则报错
        initial_gl = chromium_gl or VIDEO_RENDER_CHROMIUM_GL
        if initial_gl not in ALLOWED_GL_BACKENDS:
            raise ValueError(f"unsupported Chromium GL backend: {initial_gl}")
        self.chromium_gl = initial_gl

    # 渲染主流程：校验环境、准备音频清单、调用 Remotion 并校验产物
    async def render(self, plan: VideoPlan, output_dir: Path) -> VideoArtifact:
        # 检查 video-render 项目是否就绪
        if not (self.remotion_dir / "package.json").is_file():
            raise VideoRenderError("video-render project is missing")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Remotion render.ts 使用 build/cached_bundle/ 作为 serve 根目录
        # （缓存复用模式），音频资源必须放到 bundle 目录下才能被 serve 到。
        #
        # 架构：renderer.py 写 audio manifest（清单），render.ts 在 bundle 就绪后
        # 再复制音频到 bundle/public/。这从根本上避免了 render.ts 的
        # fs.rmSync(cached_bundle) 清除已暂存音频的竞态条件。
        # 创建本次渲染的临时作业目录
        job_dir = output_dir / f".render-{uuid.uuid4().hex}"
        job_dir.mkdir(parents=True)
        plan_path = job_dir / "video-plan.json"
        manifest_path = job_dir / "audio-manifest.json"
        temporary_output = job_dir / "output.mp4"
        final_output = output_dir / "video.mp4"
        render_payload = plan.model_dump(mode="json")
        # 构建音频清单：校验每个场景音频 URL 合法性并映射到 bundle 目录
        audio_manifest: list[dict[str, str]] = []
        for scene in render_payload["scenes"]:
            audio_src = str(scene["audio_src"])
            # 音频必须使用 /static/ URL，否则视为非法
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
            # 音频文件缺失时直接报错
            if not source_audio.is_file():
                raise VideoRenderError(f"scene audio is missing: {source_audio}")
            # 构造重命名后的暂存文件名
            staged_name = f"{scene['index']:02d}-{source_audio.name}"
            # dest 是相对于 bundle public/ 的路径，render.ts 会复制到该位置
            dest = f"render-assets/{job_dir.name}/{staged_name}"
            audio_manifest.append({"src": str(source_audio), "dest": dest})
            scene["audio_src"] = f"/render-assets/{job_dir.name}/{staged_name}"
        manifest_path.write_text(
            json.dumps(audio_manifest, ensure_ascii=False),
            encoding="utf-8",
        )
        plan_path.write_text(
            json.dumps(render_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        import platform
        npx_cmd = shutil.which("npx") or ("npx.cmd" if platform.system() == "Windows" else "npx")

        # 运行时探测 GPU 并选择最优 GL 后端（除非显式指定）
        # 与 cartoon 渲染器保持一致的 GPU 检测逻辑
        # 未显式指定时自动探测 GPU 选择 GL 后端
        if self.auto_detect_gl and self._explicit_gl is None:
            self.chromium_gl = await asyncio.to_thread(detect_chromium_gl_backend)

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
            "--audio-manifest",
            str(manifest_path),
        ]
        # 调用 Remotion 渲染脚本，失败时记录截断的报错信息
        try:
            from app.shared.utils.proc_logger import run_process_with_logging
            code, stdout_text, stderr_text = await run_process_with_logging(
                command,
                cwd=self.remotion_dir,
                timeout_seconds=self.timeout_seconds,
                logger_name="app.shared.video.render",
            )
            # 非零退出码表示渲染失败，收集错误信息后抛异常
            if code != 0:
                # 截断 stderr 避免异常消息过长
                err_summary = stderr_text[-800:].strip()
                if len(stderr_text) > 800:
                    err_summary = "…" + err_summary
                raise VideoRenderError(
                    f"Remotion render failed: {err_summary}"
                )
            # 产物缺失或为空时直接报错
            if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
                raise VideoRenderError("Remotion did not produce an MP4 file")

            # 探测音视频流，确保产物包含视频与音频轨道
            streams = await self._probe_streams(temporary_output)
            stream_types = {stream.get("codec_type") for stream in streams}
            # 缺少视频或音频轨道均视为渲染失败
            if "video" not in stream_types:
                raise VideoRenderError("rendered MP4 has no video stream")
            if "audio" not in stream_types:
                raise VideoRenderError("rendered MP4 has no audio stream")

            # 渲染成功，将临时文件替换为最终输出
            temporary_output.replace(final_output)
        # 渲染超时时转换为可读的渲染超时错误
        except asyncio.TimeoutError as exc:
            raise VideoRenderError(
                f"Remotion render timed out after {self.timeout_seconds}s"
            ) from exc
        # 无论成功失败都清理临时作业目录
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)

        # 计算对外的静态资源 URL 并返回视频产物描述
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

    # 使用 ffprobe 探测媒体文件的音视频流信息
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
        # ffprobe 失败或返回非法 JSON 时抛出渲染错误
        if code != 0:
            raise VideoRenderError(f"ffprobe failed: {stderr[-600:].strip()}")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise VideoRenderError("ffprobe returned invalid JSON") from exc
        # 校验并返回流列表
        streams = payload.get("streams")
        if not isinstance(streams, list):
            raise VideoRenderError("ffprobe returned no stream list")
        return streams
