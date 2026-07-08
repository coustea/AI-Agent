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

REPOSITORY_DIR = Path(__file__).resolve().parents[4]


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
    browser_gpu: bool = False
    gpu_encoding: bool = False
    low_memory_mode: bool = False
    cpu_fallback: bool = False
    browser_path: str | None = None

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

    if platform.system() == "Windows":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys), int(stat.ullAvailPhys)
        except Exception:
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

    if system == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "NumberOfCores"],
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if len(lines) > 1:
                return max(1, int(lines[1]))
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

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


def _nvidia_gpu_available(encoders: str) -> bool:
    """Return whether Linux or Windows has a working NVIDIA driver and NVENC encoder."""
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
            [
                nvidia_smi,
                "--query-gpu=name",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _find_chrome_headless_shell() -> str | None:
    """定位 chrome-headless-shell 二进制，供 hyperframes 使用 beginFrame 优化捕获路径。

    hyperframes 默认调用系统 Chrome，仅支持逐帧截图捕获（慢）；chrome-headless-shell
    支持 HeadlessExperimental.beginFrame，逐帧捕获显著更快。优先复用 Remotion 已经下载
    的 chrome-headless-shell，避免重复下载；同时尊重 HYPERFRAMES_BROWSER_PATH 显式覆盖。
    找不到时返回 None，hyperframes 会回退系统 Chrome（功能正常但较慢）。
    """
    env_path = os.environ.get("HYPERFRAMES_BROWSER_PATH")
    if env_path and Path(env_path).is_file() and os.access(env_path, os.X_OK):
        return env_path

    remotion_cache = REPOSITORY_DIR / "video-render" / "node_modules" / ".remotion"
    if remotion_cache.is_dir():
        for candidate in remotion_cache.rglob("chrome-headless-shell"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

    puppeteer_cache = Path.home() / ".cache" / "puppeteer"
    if puppeteer_cache.is_dir():
        for candidate in puppeteer_cache.rglob("chrome-headless-shell"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

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
    nvidia_gpu = _nvidia_gpu_available(encoders)
    low_memory_mode = total_memory <= 8 * _GIB or available_memory <= 3 * _GIB
    workers = _worker_count(
        physical_cores,
        available_memory,
        low_memory_mode=low_memory_mode,
    )
    browser_path = _find_chrome_headless_shell()
    if browser_path:
        logger.info("HyperFrames 复用 chrome-headless-shell 优化捕获路径: %s", browser_path)
    else:
        logger.warning(
            "未找到 chrome-headless-shell，hyperframes 将回退系统 Chrome 截图模式（较慢）；"
            "可运行 `npx @puppeteer/browsers install chrome-headless-shell` 或设置 HYPERFRAMES_BROWSER_PATH"
        )

    profile = CartoonRenderProfile(
        platform=f"{platform.system().lower()}-{platform.machine().lower()}",
        logical_cpus=logical_cpus,
        physical_cores=physical_cores,
        total_memory_gb=round(total_memory / _GIB, 1),
        available_memory_gb=round(available_memory / _GIB, 1),
        workers=workers,
        gpu_detected=nvidia_gpu,
        browser_gpu=nvidia_gpu,
        gpu_encoding=nvidia_gpu,
        low_memory_mode=low_memory_mode,
        browser_path=browser_path,
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

        # chrome-headless-shell 启用 beginFrame 优化捕获路径（替代系统 Chrome 的逐帧截图）。
        # 传入 env 会整体替换父进程环境，必须合并 os.environ，否则子进程丢失 PATH 等关键变量。
        env: dict[str, str] | None = None
        if profile.browser_path:
            env = {**os.environ, "HYPERFRAMES_BROWSER_PATH": profile.browser_path}

        # 显式记录渲染命令与浏览器/编码模式，便于调试与性能排查。
        # 浏览器模式不在命令行参数里（通过 env 注入），故单独标注。
        browser_mode = (
            f"chrome-headless-shell(beginFrame优化): {profile.browser_path}"
            if profile.browser_path
            else "系统Chrome(截图模式，较慢)"
        )
        encoding_mode = "GPU(NVENC)" if profile.gpu_encoding else "CPU(libx264)"
        logger.info(
            "HyperFrames 渲染启动 | 输出=%s | 浏览器=[%s] | 编码=[%s] | workers=%d | fps=%d | quality=%s",
            final_output, browser_mode, encoding_mode,
            profile.workers, profile.fps, profile.quality,
        )
        logger.info("HyperFrames 命令: %s", " ".join(command))

        try:
            from app.shared.utils.proc_logger import run_process_with_logging
            code, stdout_text, stderr_text = await run_process_with_logging(
                command,
                cwd=output_dir,
                timeout_seconds=self.timeout_seconds,
                logger_name="app.shared.cartoon.render",
                env=env,
            )
        except asyncio.TimeoutError as exc:
            raise CartoonRenderError(
                f"HyperFrames 渲染在 {self.timeout_seconds} 秒后超时"
            ) from exc
        except OSError as exc:
            return f"无法启动 HyperFrames CLI: {exc}"

        if code == 0:
            return None

        stdout_text = stdout_text.strip()
        stderr_text = stderr_text.strip()
        details = self._error_details(stdout_text, stderr_text)
        return f"退出码 {code}: {details}"

    @staticmethod
    def _command(profile: CartoonRenderProfile) -> list[str]:
        npx_cmd = "npx.cmd" if platform.system() == "Windows" else "npx"
        command = [
            npx_cmd,
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
