"""Environment-aware HyperFrames rendering for animated teaching videos."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from pathlib import Path

from app.infra.logging import get_logger

logger = get_logger(__name__)

_GIB = 1024**3
_HARDWARE_ENCODERS = (
    ("h264_nvenc", "nvenc"),
    ("h264_videotoolbox", "videotoolbox"),
    ("h264_qsv", "qsv"),
    ("h264_vaapi", "vaapi"),
    ("h264_amf", "amf"),
)


class CartoonRenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class CartoonRenderProfile:
    """The concrete render settings selected for the current host."""

    platform: str
    logical_cpus: int
    physical_cores: int
    total_memory_gb: float
    available_memory_gb: float
    workers: int
    fps: int = 30
    quality: str = "high"
    gpu_detected: bool = False
    gpu_vendors: tuple[str, ...] = ()
    browser_gpu: bool = False
    gpu_encoding: bool = False
    hardware_encoder: str | None = None
    low_memory_mode: bool = False
    cpu_fallback: bool = False

    def as_metadata(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CartoonRenderResult:
    video_path: Path
    profile: CartoonRenderProfile


def _memory_bytes() -> tuple[int, int]:
    """Return total and currently available memory without third-party packages."""
    if platform.system() == "Darwin":
        try:
            total_result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            vm_result = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            total = int(total_result.stdout.strip())
            page_size = 4096
            available_pages = 0
            for line in vm_result.stdout.splitlines():
                if "page size of" in line:
                    page_size = int(line.split("page size of", 1)[1].split()[0])
                    continue
                key, _, raw_value = line.partition(":")
                if key in {"Pages free", "Pages inactive", "Pages speculative"}:
                    available_pages += int(raw_value.strip().rstrip("."))
            available = available_pages * page_size
            if total > 0:
                return total, available or total // 4
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, raw_value = line.partition(":")
            if raw_value:
                values[key] = int(raw_value.strip().split()[0]) * 1024
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", values.get("MemFree", 0))
        if total > 0:
            return total, available or total

    try:
        total = int(os.sysconf("SC_PHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE"))
        available = int(os.sysconf("SC_AVPHYS_PAGES")) * int(
            os.sysconf("SC_PAGE_SIZE")
        )
        if total > 0 and available > 0:
            return total, available
    except (AttributeError, OSError, TypeError, ValueError):
        pass

    return 8 * _GIB, 4 * _GIB


def _physical_core_count(logical_cpus: int) -> int:
    system = platform.system()
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"],
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            return max(1, int(result.stdout.strip()))
        except (OSError, subprocess.SubprocessError, ValueError):
            return logical_cpus

    if system == "Linux":
        topology_root = Path("/sys/devices/system/cpu")
        cores: set[tuple[str, str]] = set()
        for cpu_dir in topology_root.glob("cpu[0-9]*"):
            topology = cpu_dir / "topology"
            try:
                package_id = (topology / "physical_package_id").read_text().strip()
                core_id = (topology / "core_id").read_text().strip()
            except OSError:
                continue
            cores.add((package_id, core_id))
        if cores:
            return len(cores)

    return logical_cpus


def _ffmpeg_encoders() -> str:
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


def _linux_gpu_vendors() -> set[str]:
    vendor_ids = {
        "0x10de": "nvidia",
        "0x1002": "amd",
        "0x8086": "intel",
    }
    vendors: set[str] = set()
    drm_root = Path("/sys/class/drm")
    for vendor_file in drm_root.glob("card[0-9]*/device/vendor"):
        try:
            vendor_id = vendor_file.read_text(encoding="utf-8").strip().lower()
        except OSError:
            continue
        vendors.add(vendor_ids.get(vendor_id, "unknown"))
    if vendors:
        return vendors

    lspci = shutil.which("lspci")
    if lspci is None:
        return set()
    try:
        result = subprocess.run(
            [lspci],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    for line in result.stdout.lower().splitlines():
        if not any(
            label in line
            for label in ("vga compatible", "3d controller", "display controller")
        ):
            continue
        if "nvidia" in line:
            vendors.add("nvidia")
        elif "amd" in line or "ati" in line:
            vendors.add("amd")
        elif "intel" in line:
            vendors.add("intel")
        else:
            vendors.add("unknown")
    return vendors


def _gpu_vendors(encoders: str) -> set[str]:
    system = platform.system()
    if system == "Darwin":
        return {"apple"} if "videotoolbox" in encoders else set()
    if system == "Linux":
        return _linux_gpu_vendors()
    if system == "Windows":
        return (
            {"unknown"}
            if any(name in encoders for name, _ in _HARDWARE_ENCODERS)
            else set()
        )
    return set()


def _hardware_encoder(encoders: str, gpu_vendors: set[str]) -> str | None:
    if not gpu_vendors:
        return None

    system = platform.system()
    candidates = _HARDWARE_ENCODERS
    if system == "Darwin":
        candidates = (("h264_videotoolbox", "videotoolbox"),)
    elif system == "Linux":
        candidates = ()
        if "nvidia" in gpu_vendors:
            candidates += (("h264_nvenc", "nvenc"),)
        if "amd" in gpu_vendors:
            candidates += (
                ("h264_vaapi", "vaapi"),
                ("h264_amf", "amf"),
            )
        if "intel" in gpu_vendors:
            candidates += (
                ("h264_qsv", "qsv"),
                ("h264_vaapi", "vaapi"),
            )
        if "unknown" in gpu_vendors:
            candidates += (
                ("h264_vaapi", "vaapi"),
                ("h264_qsv", "qsv"),
                ("h264_nvenc", "nvenc"),
                ("h264_amf", "amf"),
            )

    for ffmpeg_name, profile_name in candidates:
        if ffmpeg_name in encoders:
            return profile_name
    return None


def _worker_count(
    physical_cores: int,
    available_memory_bytes: int,
    *,
    low_memory_mode: bool,
) -> int:
    if low_memory_mode:
        return 1

    cpu_budget = max(1, physical_cores // 2)
    reserved_memory = 2 * _GIB
    usable_memory = max(_GIB, available_memory_bytes - reserved_memory)
    memory_budget = max(1, int(usable_memory // _GIB))
    return max(1, min(8, cpu_budget, memory_budget))


@lru_cache(maxsize=1)
def detect_cartoon_render_profile() -> CartoonRenderProfile:
    """Inspect the host once and select a stable, high-quality render profile."""
    logical_cpus = max(1, os.cpu_count() or 1)
    physical_cores = max(1, _physical_core_count(logical_cpus))
    total_memory, available_memory = _memory_bytes()
    encoders = _ffmpeg_encoders()
    gpu_vendors = _gpu_vendors(encoders)
    encoder = _hardware_encoder(encoders, gpu_vendors)
    low_memory_mode = total_memory <= 8 * _GIB or available_memory <= 3 * _GIB
    workers = _worker_count(
        physical_cores,
        available_memory,
        low_memory_mode=low_memory_mode,
    )

    profile = CartoonRenderProfile(
        platform=f"{platform.system().lower()}-{platform.machine().lower()}",
        logical_cpus=logical_cpus,
        physical_cores=physical_cores,
        total_memory_gb=round(total_memory / _GIB, 1),
        available_memory_gb=round(available_memory / _GIB, 1),
        workers=workers,
        gpu_detected=bool(gpu_vendors),
        gpu_vendors=tuple(sorted(gpu_vendors)),
        browser_gpu=bool(gpu_vendors),
        gpu_encoding=encoder is not None,
        hardware_encoder=encoder,
        low_memory_mode=low_memory_mode,
    )
    logger.info("HyperFrames 自动渲染配置: %s", profile.as_metadata())
    return profile


class CartoonVideoRenderer:
    """Render HyperFrames HTML with automatic host tuning and CPU fallback."""

    def __init__(self, timeout_seconds: int = 900) -> None:
        self.timeout_seconds = max(60, timeout_seconds)

    async def render(self, output_dir: Path) -> CartoonRenderResult:
        html_file = output_dir / "index.html"
        if not html_file.is_file():
            raise CartoonRenderError(f"合成 HTML 文件缺失: {html_file}")

        final_output = output_dir / "video.mp4"
        profile = await asyncio.to_thread(detect_cartoon_render_profile)
        first_error = await self._run_render(output_dir, final_output, profile)

        if first_error is not None and (profile.browser_gpu or profile.gpu_encoding):
            logger.warning(
                "HyperFrames GPU 渲染失败，自动切换 CPU 重试: %s",
                first_error,
            )
            profile = replace(
                profile,
                browser_gpu=False,
                gpu_encoding=False,
                hardware_encoder=None,
                cpu_fallback=True,
            )
            second_error = await self._run_render(output_dir, final_output, profile)
            if second_error is not None:
                raise CartoonRenderError(
                    f"GPU 渲染失败: {first_error}；CPU 回退也失败: {second_error}"
                )
        elif first_error is not None:
            raise CartoonRenderError(first_error)

        if not final_output.is_file() or final_output.stat().st_size == 0:
            raise CartoonRenderError("HyperFrames CLI 完成但未生成有效的 video.mp4")

        logger.info(
            "HyperFrames 渲染完成: %s (%d 字节, workers=%d, gpu=%s)",
            final_output,
            final_output.stat().st_size,
            profile.workers,
            profile.browser_gpu or profile.gpu_encoding,
        )
        return CartoonRenderResult(video_path=final_output, profile=profile)

    async def _run_render(
        self,
        output_dir: Path,
        final_output: Path,
        profile: CartoonRenderProfile,
    ) -> str | None:
        final_output.unlink(missing_ok=True)
        command = self._command(profile)
        logger.info("在 %s 启动 HyperFrames: %s", output_dir, " ".join(command))

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            return f"无法启动 HyperFrames CLI: {exc}"

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise CartoonRenderError(
                f"HyperFrames 渲染在 {self.timeout_seconds} 秒后超时"
            ) from exc

        if process.returncode == 0:
            return None

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        details = self._error_details(stdout_text, stderr_text)
        return f"退出码 {process.returncode}: {details}"

    @staticmethod
    def _command(profile: CartoonRenderProfile) -> list[str]:
        command = [
            "npx",
            "--no-install",
            "hyperframes",
            "render",
            ".",
            "--output",
            "video.mp4",
            "--fps",
            str(profile.fps),
            "--quality",
            profile.quality,
            "--workers",
            str(profile.workers),
            "--json",
        ]
        command.append("--browser-gpu" if profile.browser_gpu else "--no-browser-gpu")
        if profile.gpu_encoding:
            command.append("--gpu")
        if profile.low_memory_mode:
            command.append("--low-memory-mode")
        return command

    @staticmethod
    def _error_details(stdout: str, stderr: str) -> str:
        for raw_line in reversed(stdout.splitlines()):
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                errors = payload.get("errors")
                if isinstance(errors, list) and errors:
                    return "; ".join(
                        str(item.get("message", item))
                        if isinstance(item, dict)
                        else str(item)
                        for item in errors[:6]
                    )
                message = payload.get("message")
                if message:
                    return str(message)
        return stderr or stdout or "无进程输出"
