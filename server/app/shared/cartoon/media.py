"""HyperFrames execution, typed diagnostics and publication quality policy."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.infra.logging import get_logger
from app.shared.cartoon.models import Lesson


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


class HyperFramesToolchainError(RuntimeError):
    """The installed CLI cannot provide the checks required for publication."""


class QualityPolicy:
    """Publish only bundles that pass every strict HyperFrames error check."""

    _BLOCKING_CATEGORIES = (
        "lint",
        "runtime",
        "layout",
        "motion",
        "contrast",
        "semantic",
        "unknown",
    )

    def enforce(self, report: HyperFramesReport) -> None:
        problems: list[str] = []
        for category in self._BLOCKING_CATEGORIES:
            blocking = [
                item for item in report.findings
                if item.category == category and item.severity == "error"
            ]
            if blocking:
                problems.append(f"{category} findings: {self._summarize(blocking)}")
                logger.warning(
                    "[QualityPolicy] %s 阻断问题: %s",
                    category,
                    self._summarize(blocking),
                )

        advisory = [
            item for item in report.findings
            if item.category not in self._BLOCKING_CATEGORIES
            and item.severity in {"error", "warning"}
        ]
        if advisory:
            logger.warning(
                "[QualityPolicy] 非阻断质量问题: %s",
                self._summarize(advisory),
            )

        # A tool failure without any finding is not a quality preference and
        # remains blocking because there is no evidence the bundle was checked.
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


@dataclass(frozen=True, slots=True)
class RenderProfile:
    """A bounded render plan derived from the host, with explicit overrides.

    HyperFrames workers are Chrome processes, not lightweight encoder threads.
    The profile therefore budgets memory first and only then uses the available
    CPU.  This keeps constrained servers reliable while allowing workstations
    to render several frames in parallel.
    """

    selection: Literal["adaptive"]
    workers: int
    gpu_encoding: bool
    low_memory_mode: bool
    cpu_cores: int
    effective_cpu_cores: int
    load_1m: float | None
    memory_total_gib: int | None
    memory_available_gib: int | None
    platform_name: str
    machine: str
    gpu_backend: str | None
    gpu_memory_free_mib: int | None
    gpu_utilization_percent: int | None
    workers_source: Literal["automatic", "override"]
    gpu_source: Literal["automatic", "override"]

    def metadata(self) -> dict[str, Any]:
        return asdict(self)


class CartoonMedia:
    """Run the fixed repository toolchain and verify the final media artifact."""

    # Unbounded tween boundaries can make HyperFrames' diagnostic navigation time out.
    _MAX_TRANSITION_SAMPLES = 64
    # HyperFrames validate uses this value only for page settling, not page
    # navigation.  Keeping it small avoids turning a visual smoke check into
    # a minute-long delay for every bundle.
    _VALIDATE_SETTLE_TIMEOUT_MS = 3_000
    _QUALITY_COMMANDS = ("lint", "validate", "inspect")
    _toolchain_cache: set[tuple[str, int, int]] = set()

    def __init__(
        self,
        *,
        check_timeout_seconds: int = 360,
        check_navigation_timeout_ms: int = 60_000,
        render_timeout_seconds: int = 1_800,
        render_workers: int | str | None = None,
        render_gpu: bool | None = None,
    ) -> None:
        self.check_timeout_seconds = check_timeout_seconds
        self.check_navigation_timeout_ms = check_navigation_timeout_ms
        self.render_timeout_seconds = render_timeout_seconds
        self._render_workers_override = render_workers
        self._render_gpu_override = render_gpu
        self.render_profile: RenderProfile | None = None
        self.policy = QualityPolicy()

    @staticmethod
    def hyperframes_path() -> Path:
        return CartoonMedia._node_binary("hyperframes")

    @staticmethod
    def gsap_path() -> Path:
        return CartoonMedia._node_asset("gsap", "dist", "gsap.min.js")

    @staticmethod
    def _node_roots() -> tuple[Path, Path]:
        """Prefer backend-owned tools, then allow the repository frontend runtime."""

        backend_root = Path(__file__).resolve().parents[3]
        return backend_root, backend_root.parent

    @classmethod
    def _node_binary(cls, name: str) -> Path:
        candidates: list[Path] = []
        for root in cls._node_roots():
            path = root / "node_modules" / ".bin" / name
            candidates.extend((path.with_suffix(".cmd"), path))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        searched = ", ".join(str(path) for path in candidates)
        raise RuntimeError(f"仓库缺少 HyperFrames CLI，请先安装依赖（searched: {searched}）")

    @classmethod
    def _node_asset(cls, package: str, *parts: str) -> Path:
        candidates = [root / "node_modules" / package / Path(*parts) for root in cls._node_roots()]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        searched = ", ".join(str(path) for path in candidates)
        raise RuntimeError(f"仓库缺少 {package} 运行时，请先安装依赖（searched: {searched}）")

    @classmethod
    def _resolve_render_profile(
        cls,
        *,
        render_workers: int | str | None,
        render_gpu: bool | None,
    ) -> RenderProfile:
        """Build one stable plan before rendering; explicit configuration wins."""

        platform_name = platform.system().lower()
        machine = platform.machine().lower()
        cpu_cores = max(1, os.cpu_count() or 1)
        effective_cpu_cores = cls._effective_cpu_cores(cpu_cores)
        load_1m = cls._load_average()
        available_cpu_cores = max(1, effective_cpu_cores - int((load_1m or 0) + 0.999))
        memory_total_gib, memory_available_gib = cls._memory_snapshot(platform_name)
        gpu_backend, gpu_memory_free_mib, gpu_utilization_percent = cls._detected_gpu_backend(
            platform_name,
            machine,
        )

        # A render worker is an entire Chrome process plus frame buffers and
        # compositor state.  Leave host headroom, allocate at most one worker
        # per 3 GiB that remains, then bound it by currently available CPU.
        if memory_available_gib is None:
            memory_worker_budget = 1
        else:
            memory_worker_budget = max(1, (max(0, memory_available_gib - 2)) // 3)
        cpu_worker_budget = max(1, int(available_cpu_cores * 0.75))
        auto_workers = min(8, cpu_worker_budget, memory_worker_budget)

        configured_workers = render_workers
        workers_source: Literal["automatic", "override"] = "automatic"
        if configured_workers is None:
            configured_workers = os.environ.get("CARTOON_RENDER_WORKERS", "").strip()
        if configured_workers not in (None, ""):
            normalized = str(configured_workers).strip().lower()
            if normalized == "auto":
                workers = auto_workers
            elif normalized.isdigit() and int(normalized) >= 1:
                workers = int(normalized)
                workers_source = "override"
            else:
                raise ValueError("CARTOON_RENDER_WORKERS 必须为 auto 或正整数")
        else:
            workers = auto_workers

        low_memory_mode = workers_source == "automatic" and memory_worker_budget == 1

        configured_gpu = render_gpu
        gpu_source: Literal["automatic", "override"] = "automatic"
        if configured_gpu is None:
            gpu_value = os.environ.get("CARTOON_RENDER_GPU", "").strip().lower()
            if gpu_value in {"", "auto"}:
                gpu_encoding = (
                    gpu_backend is not None
                    and memory_worker_budget > 1
                    and (gpu_memory_free_mib is None or gpu_memory_free_mib >= 2_048)
                    and (gpu_utilization_percent is None or gpu_utilization_percent < 85)
                )
            elif gpu_value in {"1", "true", "yes"}:
                gpu_encoding = True
                gpu_source = "override"
            elif gpu_value in {"0", "false", "no"}:
                gpu_encoding = False
                gpu_source = "override"
            else:
                raise ValueError("CARTOON_RENDER_GPU 必须为 auto 或 true/false")
        else:
            gpu_encoding = configured_gpu
            gpu_source = "override"

        return RenderProfile(
            selection="adaptive",
            workers=workers,
            gpu_encoding=gpu_encoding,
            low_memory_mode=low_memory_mode,
            cpu_cores=cpu_cores,
            effective_cpu_cores=effective_cpu_cores,
            load_1m=load_1m,
            memory_total_gib=memory_total_gib,
            memory_available_gib=memory_available_gib,
            platform_name=platform_name,
            machine=machine,
            gpu_backend=gpu_backend,
            gpu_memory_free_mib=gpu_memory_free_mib,
            gpu_utilization_percent=gpu_utilization_percent,
            workers_source=workers_source,
            gpu_source=gpu_source,
        )

    @classmethod
    def _effective_cpu_cores(cls, host_cpu_cores: int) -> int:
        """Honor Linux container CPU quotas instead of reading host capacity."""

        cpu_max = Path("/sys/fs/cgroup/cpu.max")
        try:
            quota, period = cpu_max.read_text(encoding="utf-8").split()[:2]
            if quota != "max":
                return max(1, min(host_cpu_cores, int(quota) // int(period)))
        except (OSError, ValueError, IndexError):
            pass
        return host_cpu_cores

    @staticmethod
    def _load_average() -> float | None:
        try:
            return max(0.0, os.getloadavg()[0])
        except (AttributeError, OSError):
            return None

    @classmethod
    def _memory_snapshot(cls, platform_name: str) -> tuple[int | None, int | None]:
        """Return memory visible to this process, including cgroup limits."""

        total_bytes = cls._host_memory_bytes()
        available_bytes = cls._available_memory_bytes(platform_name)
        cgroup_limit = cls._cgroup_memory_limit_bytes()
        cgroup_current = cls._cgroup_memory_current_bytes()
        if cgroup_limit is not None:
            total_bytes = min(total_bytes, cgroup_limit) if total_bytes else cgroup_limit
            if cgroup_current is not None:
                cgroup_available = max(0, cgroup_limit - cgroup_current)
                available_bytes = min(available_bytes, cgroup_available) if available_bytes else cgroup_available
        to_gib = lambda value: max(1, value // (1024**3)) if value else None
        return (
            to_gib(total_bytes),
            to_gib(available_bytes) if available_bytes is not None else to_gib(total_bytes),
        )

    @staticmethod
    def _host_memory_bytes() -> int | None:
        if platform.system().lower() == "windows":
            return CartoonMedia._windows_memory_bytes()[0]
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            page_count = os.sysconf("SC_PHYS_PAGES")
        except (AttributeError, OSError, ValueError):
            return None
        value = page_size * page_count
        return value if value > 0 else None

    @staticmethod
    def _available_memory_bytes(platform_name: str) -> int | None:
        if platform_name == "linux":
            try:
                fields = dict(
                    line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line
                )
                return int(fields["MemAvailable"].split()[0]) * 1024
            except (OSError, KeyError, ValueError):
                return None
        if platform_name == "darwin":
            try:
                result = subprocess.run(
                    ["vm_stat"], check=False, capture_output=True, text=True, timeout=2
                )
                if result.returncode != 0:
                    return None
                lines = result.stdout.splitlines()
                page_size = int(lines[0].split("page size of ")[1].split(" bytes")[0])
                fields: dict[str, int] = {}
                for line in lines[1:]:
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    fields[key.strip()] = int(value.strip().rstrip(".").replace(".", "") or "0")
                available_pages = sum(
                    fields.get(key, 0)
                    for key in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable")
                )
                return available_pages * page_size if available_pages else None
            except (OSError, ValueError, IndexError, subprocess.SubprocessError):
                return None
        if platform_name == "windows":
            return CartoonMedia._windows_memory_bytes()[1]
        return None

    @staticmethod
    def _windows_memory_bytes() -> tuple[int | None, int | None]:
        """Use the native Windows API without adding a third-party dependency."""

        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None, None
            return int(status.ullTotalPhys), int(status.ullAvailPhys)
        except (AttributeError, OSError):
            return None, None

    @staticmethod
    def _cgroup_memory_limit_bytes() -> int | None:
        for path in (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")):
            try:
                value = path.read_text(encoding="utf-8").strip()
                if value != "max":
                    limit = int(value)
                    if 0 < limit < 1 << 60:
                        return limit
            except (OSError, ValueError):
                continue
        return None

    @staticmethod
    def _cgroup_memory_current_bytes() -> int | None:
        for path in (Path("/sys/fs/cgroup/memory.current"), Path("/sys/fs/cgroup/memory/memory.usage_in_bytes")):
            try:
                value = int(path.read_text(encoding="utf-8").strip())
                if value >= 0:
                    return value
            except (OSError, ValueError):
                continue
        return None

    @staticmethod
    def _detected_gpu_backend(platform_name: str, machine: str) -> tuple[str | None, int | None, int | None]:
        """Detect usable hardware, free VRAM and load without assuming a model."""

        if platform_name == "darwin" and machine in {"arm64", "aarch64"}:
            return "videotoolbox", None, None
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return None, None, None
        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,memory.free,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return None, None, None
        if result.returncode != 0 or not result.stdout.strip():
            return None, None, None
        try:
            _, memory_free, utilization = (part.strip() for part in result.stdout.splitlines()[0].split(","))
            return "nvenc", int(memory_free), int(utilization)
        except (ValueError, IndexError):
            return None, None, None

    def install_runtime(self, output_dir: Path) -> None:
        vendor_dir = output_dir / "assets" / "vendor"
        vendor_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.gsap_path(), vendor_dir / "gsap.min.js")

    async def preflight(self) -> None:
        """Fail before planning when the pinned CLI lacks our quality contract.

        HyperFrames publishes several unrelated ``check`` commands.  Treating a
        command name as a stable API caused a late failure after planning, TTS,
        and composition had already completed.  Probe every command this
        adapter relies on instead of guessing from a package version.
        """

        executable = self.hyperframes_path()
        try:
            stat = executable.stat()
        except OSError as exc:
            # Test doubles and PATH-resolved launchers need not be filesystem
            # objects.  The command probes below remain the source of truth.
            logger.debug("[CartoonMedia] HyperFrames CLI 无法 stat，将跳过预检缓存: %s", exc)
            fingerprint: tuple[str, int, int] | None = None
        else:
            fingerprint = (str(executable.resolve()), stat.st_mtime_ns, stat.st_size)
        if fingerprint is not None and fingerprint in self._toolchain_cache:
            return

        for command_name in self._QUALITY_COMMANDS:
            command = [str(executable), command_name, "--help"]
            exit_code, stdout, stderr = await self._run_streaming(
                command,
                cwd=executable.parent,
                timeout_seconds=20,
                label=f"preflight-{command_name}",
            )
            detail = (stderr or stdout).strip()
            if exit_code != 0 or "Unknown command" in detail:
                rendered = detail[:800] or f"exit_code={exit_code}"
                raise HyperFramesToolchainError(
                    "已安装的 HyperFrames 不支持 Cartoon 质量门命令 "
                    f"{command_name!r}: {rendered}"
                )

        if fingerprint is not None:
            self._toolchain_cache.add(fingerprint)
        logger.info(
            "[CartoonMedia] HyperFrames 质量门能力预检通过: cli=%s commands=%s",
            executable,
            ",".join(self._QUALITY_COMMANDS),
        )

    async def check(self, output_dir: Path) -> HyperFramesReport:
        logger.info("[CartoonMedia] 开始质量检查: dir=%s", output_dir)
        t0 = asyncio.get_event_loop().time()
        await self.preflight()
        executable = str(self.hyperframes_path())
        command_specs = (
            (
                "lint",
                [executable, "lint", ".", "--json"],
                self._lint_findings,
            ),
            (
                "validate",
                [
                    executable,
                    "validate",
                    ".",
                    "--json",
                    "--timeout",
                    str(self._VALIDATE_SETTLE_TIMEOUT_MS),
                ],
                self._validate_findings,
            ),
            (
                "inspect",
                [
                    executable,
                    "inspect",
                    ".",
                    "--json",
                    "--at-transitions",
                    f"--max-transition-samples={self._MAX_TRANSITION_SAMPLES}",
                    "--max-issues=200",
                ],
                self._inspect_findings,
            ),
        )
        payloads: dict[str, dict[str, Any]] = {}
        findings: list[QualityFinding] = []
        exit_codes: list[int] = []
        environment = {
            "PRODUCER_PAGE_NAVIGATION_TIMEOUT_MS": os.environ.get(
                "PRODUCER_PAGE_NAVIGATION_TIMEOUT_MS",
                str(self.check_navigation_timeout_ms),
            ),
        }
        for command_name, command, parser in command_specs:
            logger.info(
                "[CartoonMedia] HyperFrames %s 命令: %s (timeout=%ds)",
                command_name,
                " ".join(command[1:]),
                self.check_timeout_seconds,
            )
            exit_code, stdout, stderr = await self._run_streaming(
                command,
                cwd=output_dir,
                timeout_seconds=self.check_timeout_seconds,
                label=command_name,
                env=environment,
            )
            exit_codes.append(exit_code)
            if stderr.strip():
                logger.debug("[CartoonMedia] HyperFrames %s stderr: %s", command_name, stderr[:500])
            try:
                payload = self._json_payload(stdout)
            except ValueError as exc:
                detail = stderr.strip() or stdout.strip() or str(exc)
                logger.error(
                    "[CartoonMedia] HyperFrames %s JSON 解析失败: %s",
                    command_name,
                    detail[:800],
                )
                raise QualityGateError(
                    [f"HyperFrames {command_name} returned invalid JSON: {detail[:800]}"]
                ) from exc
            payloads[command_name] = payload
            findings.extend(parser(payload, exit_code=exit_code))
        check_ms = round((asyncio.get_event_loop().time() - t0) * 1000)
        report = HyperFramesReport(
            ok=all(bool(payload.get("ok", False)) for payload in payloads.values()),
            findings=findings,
            raw=payloads,
            exit_code=max(exit_codes, default=0),
        )
        logger.info(
            "[CartoonMedia] HyperFrames 检查完成: ok=%s exit_code=%d findings=%d elapsed_ms=%d",
            report.ok,
            report.exit_code,
            len(report.findings),
            check_ms,
        )
        report.findings.extend(self._semantic_findings(output_dir))
        self.policy.enforce(report)
        await self._check_runtime_visibility(output_dir)
        logger.info("[CartoonMedia] 质量检查全部通过")
        return report

    @classmethod
    def _lint_findings(
        cls,
        payload: Mapping[str, Any],
        *,
        exit_code: int,
    ) -> list[QualityFinding]:
        findings = cls._command_findings(payload, category="lint", source="lint")
        return cls._command_failure_finding(
            payload,
            findings,
            command_name="lint",
            exit_code=exit_code,
        )

    @classmethod
    def _validate_findings(
        cls,
        payload: Mapping[str, Any],
        *,
        exit_code: int,
    ) -> list[QualityFinding]:
        findings = cls._command_findings(
            payload,
            category="runtime",
            source="errors",
            severity="error",
        )
        findings.extend(
            cls._command_findings(
                payload,
                category="runtime",
                source="warnings",
                severity="warning",
            )
        )
        contrast_entries = payload.get("contrast", [])
        if isinstance(contrast_entries, list):
            for item in contrast_entries:
                if not isinstance(item, Mapping) or item.get("wcagAA", True):
                    continue
                findings.append(
                    QualityFinding(
                        category="contrast",
                        code="low_contrast",
                        severity="warning",
                        message=cls._finding_message(item),
                    )
                )
        return cls._command_failure_finding(
            payload,
            findings,
            command_name="validate",
            exit_code=exit_code,
        )

    @classmethod
    def _inspect_findings(
        cls,
        payload: Mapping[str, Any],
        *,
        exit_code: int,
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        for item in payload.get("issues", []):
            if not isinstance(item, Mapping):
                continue
            code = str(item.get("code") or "unknown")
            category: FindingCategory = "motion" if code.startswith("motion_") else "layout"
            findings.append(
                QualityFinding(
                    category=category,
                    code=code,
                    severity=cls._severity(item.get("severity")),
                    message=cls._finding_message(item),
                )
            )
        return cls._command_failure_finding(
            payload,
            findings,
            command_name="inspect",
            exit_code=exit_code,
        )

    @classmethod
    def _command_findings(
        cls,
        payload: Mapping[str, Any],
        *,
        category: FindingCategory,
        source: str,
        severity: Literal["error", "warning", "info"] | None = None,
    ) -> list[QualityFinding]:
        entries = payload.get(source, [])
        if not isinstance(entries, list):
            return []
        findings: list[QualityFinding] = []
        for item in entries:
            if isinstance(item, Mapping):
                findings.append(
                    QualityFinding(
                        category=category,
                        code=str(item.get("code") or source),
                        severity=severity or cls._severity(item.get("severity")),
                        message=cls._finding_message(item),
                    )
                )
            else:
                findings.append(
                    QualityFinding(
                        category=category,
                        code=source,
                        severity=severity or "error",
                        message=str(item),
                    )
                )
        return findings

    @staticmethod
    def _severity(value: Any) -> Literal["error", "warning", "info"]:
        normalized = str(value or "error").lower()
        return normalized if normalized in {"error", "warning", "info"} else "error"

    @staticmethod
    def _finding_message(item: Mapping[str, Any]) -> str:
        return str(item.get("message") or item.get("text") or item.get("error") or item)

    @classmethod
    def _command_failure_finding(
        cls,
        payload: Mapping[str, Any],
        findings: list[QualityFinding],
        *,
        command_name: str,
        exit_code: int,
    ) -> list[QualityFinding]:
        if not payload.get("ok", False) and not any(item.severity == "error" for item in findings):
            findings.append(
                QualityFinding(
                    category="unknown",
                    code=f"{command_name}_command_failed",
                    severity="error",
                    message=str(payload.get("error") or f"exit_code={exit_code}"),
                )
            )
        return findings

    @staticmethod
    def _semantic_findings(output_dir: Path) -> list[QualityFinding]:
        lesson_path = output_dir / "lesson.json"
        if not lesson_path.is_file():
            return [QualityFinding(category="semantic", code="missing_lesson", message="semantic validation requires lesson.json")]
        try:
            Lesson.model_validate_json(lesson_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return [QualityFinding(category="semantic", code="invalid_lesson", message=str(exc))]
        return []

    async def _check_runtime_visibility(self, output_dir: Path) -> None:
        """Verify every authored beat and caption without serial CDP round trips.

        Audio is already validated by synthesis and the renderer.  Waiting for
        every ``<audio>`` request here made a visual-only gate depend on media
        preload timing, then the old loop sent one browser RPC per beat and
        caption.  Keep the coverage identical, but sample the complete
        timeline inside the already-loaded page.
        """
        logger.info("[CartoonMedia] 开始运行时可见性检查: dir=%s", output_dir)
        t0 = asyncio.get_running_loop().time()
        timeline_path = output_dir / "timeline.json"
        if not timeline_path.is_file():
            raise QualityGateError(["caption visibility check requires timeline.json"])
        try:
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
            beats = timeline["beats"]
            cues = timeline["captions"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise QualityGateError([f"caption timeline is invalid: {exc}"]) from exc
        if not isinstance(cues, list) or not cues:
            raise QualityGateError(["caption timeline contains no cues"])
        if not isinstance(beats, list) or not beats:
            raise QualityGateError(["timeline contains no beats"])

        logger.debug(
            "[CartoonMedia] 浏览器检查: beats=%d cues=%d",
            len(beats),
            len(cues),
        )

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
                        # ``load`` waits for every generated audio track.
                        # The visibility gate only needs DOM + runtime JS;
                        # TTS output itself is checked before composition.
                        wait_until="domcontentloaded",
                        timeout=self.check_navigation_timeout_ms,
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
                        timeout=self.check_navigation_timeout_ms,
                    )
                    sampled_problems = await page.evaluate(
                        """({beats, captions}) => {
                          const timeline = window.__timelines['cartoon-teaching-video'];
                          const problems = [];
                          const setTime = time => timeline.time(time, false);
                          beats.forEach(beat => {
                            const midpoint = (Number(beat.start_ms) + Number(beat.duration_ms) / 2) / 1000;
                            setTime(midpoint);
                            const element = document.getElementById(`scene-${beat.scene_id}`);
                            if (!element) {
                              problems.push(`scene-${beat.scene_id} is not visibly rendered at ${midpoint.toFixed(3)}s`);
                              return;
                            }
                            const style = getComputedStyle(element);
                            const rect = element.getBoundingClientRect();
                            const visibleEntities = Array.from(element.querySelectorAll('.visual-entity')).filter(entity => {
                              const entityStyle = getComputedStyle(entity);
                              const entityRect = entity.getBoundingClientRect();
                              return Number(entityStyle.opacity) > 0.05
                                && entityStyle.visibility === 'visible'
                                && entityStyle.display !== 'none'
                                && entityRect.width > 0 && entityRect.height > 0;
                            }).length;
                            if (Number(style.opacity) < 0.95 || style.visibility !== 'visible'
                              || style.display === 'none' || rect.width < 1000 || rect.height < 600
                              || visibleEntities < 1) {
                              problems.push(`scene-${beat.scene_id} is not visibly rendered at ${midpoint.toFixed(3)}s`);
                            }
                          });
                          captions.forEach((cue, index) => {
                            const midpoint = (Number(cue.start_ms) + Number(cue.end_ms)) / 2000;
                            setTime(midpoint);
                            const element = document.getElementById(`caption-${index}`);
                            if (!element) {
                              problems.push(`caption-${index} is not visibly rendered at ${midpoint.toFixed(3)}s`);
                              return;
                            }
                            const style = getComputedStyle(element);
                            const rect = element.getBoundingClientRect();
                            const text = (element.textContent || '').trim();
                            if (Number(style.opacity) < 0.95 || style.visibility !== 'visible'
                              || style.display === 'none' || !text || rect.width < 400 || rect.height < 40
                              || rect.top < 850 || rect.bottom > 1080) {
                              problems.push(`caption-${index} is not visibly rendered at ${midpoint.toFixed(3)}s`);
                            }
                          });
                          return problems;
                        }""",
                        {"beats": beats, "captions": cues},
                    )
                    if not isinstance(sampled_problems, list):
                        raise RuntimeError("runtime visibility probe returned an invalid result")
                    problems.extend(str(problem) for problem in sampled_problems)
                finally:
                    await browser.close()
        except QualityGateError:
            raise
        except Exception as exc:
            detail = " | ".join(browser_messages[-8:])
            message = f"runtime browser check failed: {exc}"
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
            logger.error("[CartoonMedia] 运行时可见性问题: %s", problems)
            raise QualityGateError(problems)
        logger.info(
            "[CartoonMedia] 运行时可见性检查通过: beats=%d cues=%d elapsed_ms=%d",
            len(beats),
            len(cues),
            round((asyncio.get_running_loop().time() - t0) * 1000),
        )

    async def render(self, output_dir: Path, output_name: str = "video.mp4") -> Path:
        if Path(output_name).name != output_name or not output_name.endswith(".mp4"):
            raise ValueError("output_name must be a local MP4 filename")
        # Evaluate immediately before spawning Chrome: a long LLM/TTS phase can
        # materially change memory pressure and CPU load after pipeline startup.
        render_profile = self._resolve_render_profile(
            render_workers=self._render_workers_override,
            render_gpu=self._render_gpu_override,
        )
        self.render_profile = render_profile
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
            "--workers",
            str(render_profile.workers),
            "--page-side-compositing",
            "--no-best-effort",
        ]
        if render_profile.low_memory_mode:
            command.append("--low-memory-mode")
        if render_profile.gpu_encoding:
            command.append("--gpu")
        render_config = {
            **render_profile.metadata(),
            "fps": 24,
            "resolution": "landscape",
            "page_side_compositing": True,
            # Do not force a host GPU for Chrome: HyperFrames probes it and
            # falls back to software automatically when unavailable.
            "browser_gpu": "auto",
            "timeout_seconds": self.render_timeout_seconds,
        }
        logger.info(
            "[CartoonMedia] 渲染配置: %s",
            json.dumps(render_config, ensure_ascii=False, sort_keys=True),
        )
        logger.info(
            "[CartoonMedia] HyperFrames render 命令: %s (timeout=%ds workers=%s gpu=%s low_memory=%s; browser_gpu=auto)",
            " ".join(command[1:]),
            self.render_timeout_seconds,
            render_profile.workers,
            render_profile.gpu_encoding,
            render_profile.low_memory_mode,
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
        env: Mapping[str, str] | None = None,
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
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=process_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10485760,  # 10MB limit to prevent LimitOverrunError on huge lines
        )
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

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
