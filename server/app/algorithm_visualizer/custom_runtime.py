"""Bounded subprocess runner for LLM-instrumented custom Python code."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CustomRuntimeError(RuntimeError):
    """Raised when the bounded custom-code worker cannot return a trace."""


@dataclass(frozen=True, slots=True)
class CustomExecution:
    events: list[dict[str, Any]]
    result: Any
    stdout: str


_SDK_SOURCE = Path(__file__).parent / "tracer_sdks" / "python_tracer.py"
_RESULT_PREFIX = "__ALGORITHM_VISUALIZER_RESULT__="
_BOOTSTRAP = """
import json
import sys

input_data = json.loads(sys.stdin.read() or "{}")
tracer = VisualTracer(__VISUALIZER_TYPE__)
result = visualize(input_data, tracer)
print(__RESULT_PREFIX__ + json.dumps({"events": tracer.events, "result": result}, ensure_ascii=False, default=str))
"""


async def run_custom_program(
    *,
    instrumented_code: str,
    visualizer_type: str,
    input_data: dict[str, Any],
) -> CustomExecution:
    """Run code in a fresh process with time, memory and output limits.

    The AST contract is intentionally restrictive.  A production deployment
    should additionally place this worker in an OS/container sandbox; this
    runner never shares the application process with user code.
    """
    with tempfile.TemporaryDirectory(prefix="algorithm-visualizer-") as temp_dir:
        workdir = Path(temp_dir)
        program = (
            _SDK_SOURCE.read_text(encoding="utf-8")
            + "\n\n"
            + instrumented_code
            + "\n"
            + _BOOTSTRAP.replace("__VISUALIZER_TYPE__", repr(visualizer_type)).replace("__RESULT_PREFIX__", repr(_RESULT_PREFIX))
        )
        (workdir / "program.py").write_text(program, encoding="utf-8")
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",
                "program.py",
                cwd=workdir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=_limit_resources if os.name == "posix" else None,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(input_data, ensure_ascii=False).encode()),
                timeout=5,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise CustomRuntimeError("自定义代码执行超时（5 秒）。") from exc

    output = stdout.decode("utf-8", errors="replace")
    error = stderr.decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        raise CustomRuntimeError(f"插装后的代码运行失败：{_short(error or output)}")
    if len(output) > 2_000_000:
        raise CustomRuntimeError("自定义代码输出过大。")

    marker_index = output.rfind(_RESULT_PREFIX)
    if marker_index < 0:
        raise CustomRuntimeError("插装后的代码没有返回可视化事件。")
    trace_text = output[marker_index + len(_RESULT_PREFIX):].strip().splitlines()[0]
    try:
        payload = json.loads(trace_text)
    except json.JSONDecodeError as exc:
        raise CustomRuntimeError("可视化事件解析失败。") from exc
    events = payload.get("events")
    if not isinstance(events, list):
        raise CustomRuntimeError("可视化事件格式错误。")
    return CustomExecution(events=events, result=payload.get("result"), stdout=output[:marker_index].strip())


def _limit_resources() -> None:
    import resource

    for limit, value in (
        (resource.RLIMIT_CPU, 4),
        (resource.RLIMIT_AS, 512 * 1024 * 1024),
        (resource.RLIMIT_FSIZE, 2 * 1024 * 1024),
    ):
        try:
            resource.setrlimit(limit, (value, value))
        except (ValueError, OSError):
            # macOS does not support every Linux resource limit.  The worker
            # still has the wall-clock timeout enforced by the parent.
            continue


def _short(value: str) -> str:
    return value[-1000:] if len(value) > 1000 else value
