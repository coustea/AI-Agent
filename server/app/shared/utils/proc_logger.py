"""Subprocess execution with real-time logging to both python logging and a file."""

from __future__ import annotations

import asyncio
from pathlib import Path
from app.infra.logging import get_logger

logger = get_logger(__name__)


async def run_process_with_logging(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int,
    logger_name: str = "app.shared.render",
) -> tuple[int, str, str]:
    """Run a subprocess, streaming its stdout and stderr in real-time.

    Logs stdout/stderr lines to Python logging (logger_name).
    Returns returncode, stdout string, and stderr string.
    """
    proc_logger = get_logger(logger_name)

    proc_logger.info(f"Starting process: {' '.join(command)} (cwd={cwd})")

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    async def read_stream(stream, is_stderr: bool):
        while True:
            try:
                line = await stream.readline()
            except ValueError as e:
                if "Separator is not found" in str(e):
                    # Buffer limit exceeded, read in large chunks to prevent crashes
                    line = await stream.read(65536)
                else:
                    raise
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace")
            decoded_strip = decoded.rstrip("\r\n")
            if is_stderr:
                stderr_lines.append(decoded)
                proc_logger.warning(f"[Render Stderr] {decoded_strip}")
            else:
                stdout_lines.append(decoded)
                proc_logger.info(f"[Render Stdout] {decoded_strip}")

    try:
        await asyncio.wait_for(
            asyncio.gather(
                read_stream(process.stdout, False),
                read_stream(process.stderr, True),
            ),
            timeout=timeout_seconds,
        )
        await process.wait()
    except asyncio.TimeoutError:
        try:
            process.kill()
        except OSError:
            pass
        await process.wait()
        raise

    return (
        process.returncode or 0,
        "".join(stdout_lines),
        "".join(stderr_lines),
    )
