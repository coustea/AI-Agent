"""Subprocess execution with real-time logging to both python logging and a file.

Stdout/stderr lines are truncated to 500 chars to prevent log flooding
(e.g. Remotion render errors, Pydantic validation dumps).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 单行日志最大长度，超过则截断，避免大段输出（如校验错误）淹没日志
_MAX_LINE_LENGTH = 500


# 带实时日志的子进程执行包装：边运行边把 stdout/stderr 写入日志与返回结果
async def run_process_with_logging(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int,
    logger_name: str = "app.shared.render",
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a subprocess, streaming its stdout and stderr in real-time.

    Logs stdout/stderr lines to Python logging (logger_name).
    Lines exceeding _MAX_LINE_LENGTH are truncated with "…(truncated)" suffix.
    Returns returncode, stdout string, and stderr string.

    Args:
        env: 子进程环境变量覆盖。``None`` 表示继承父进程环境（默认）。
            传入时会**整体替换**父进程环境，调用方需自行合并所需变量。
    """
    # 获取子进程专用日志器
    proc_logger = get_logger(logger_name)

    # 记录进程启动信息
    proc_logger.info(f"启动进程: {' '.join(command)} (cwd={cwd})")

    # 创建子进程，标准输出与标准错误均重定向为管道
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # 收集子进程的标准输出与标准错误原文
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    # 持续读取单个流：按行解码、截断并记录日志
    async def read_stream(stream, is_stderr: bool):
        while True:
            try:
                line = await stream.readline()
            except ValueError as e:
                if "Separator is not found" in str(e):
                    # 单行超出缓冲区上限，按大块读取以免崩溃
                    line = await stream.read(65536)
                else:
                    raise
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace")
            decoded_strip = decoded.rstrip("\r\n")
            # 截断过长行，避免 ValidationError 等大段输出淹没日志
            truncated = decoded_strip
            if len(truncated) > _MAX_LINE_LENGTH:
                truncated = truncated[:_MAX_LINE_LENGTH] + "…(truncated)"
            if is_stderr:
                stderr_lines.append(decoded)
                proc_logger.warning(f"[Render Stderr] {truncated}")
            else:
                stdout_lines.append(decoded)
                proc_logger.info(f"[Render Stdout] {truncated}")

    try:
        # 并发读取两个流，并在超时时间内等待完成
        await asyncio.wait_for(
            asyncio.gather(
                read_stream(process.stdout, False),
                read_stream(process.stderr, True),
            ),
            timeout=timeout_seconds,
        )
        await process.wait()
    except asyncio.TimeoutError:
        # 超时则强制结束进程并向上抛出
        try:
            process.kill()
        except OSError:
            pass
        await process.wait()
        raise

    # 返回退出码、完整 stdout 与 stderr 文本
    return (
        process.returncode or 0,
        "".join(stdout_lines),
        "".join(stderr_lines),
    )
