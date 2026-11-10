"""``bash`` —— 在工作目录执行 shell 命令。"""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.infra.logging import get_logger
from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import BASH_TIMEOUT_S, truncate_output

logger = get_logger(__name__)


class BashArgs(BaseModel):
    """执行 shell 命令。"""

    command: str = Field(min_length=1, max_length=8000, description="要执行的 shell 命令")


def build(workdir: Path, *, timeout_s: float = BASH_TIMEOUT_S) -> Tool:
    """构造 bash 工具。``workdir`` 是命令的工作目录。"""

    async def bash(command: str) -> dict[str, Any]:
        """在工作目录执行 shell 命令；工作目录不构成系统沙箱。"""
        dangerous = ("rm -rf /", "sudo ", "shutdown", "reboot")
        if any(d in command for d in dangerous):
            logger.warning("[BashTool] 拒绝执行危险命令: cmd={}", command)
            return {"text": "拒绝执行危险命令", "status": "failed"}

        cmd_preview = command.strip().replace("\n", " ")
        if len(cmd_preview) > 120:
            cmd_preview = f"{cmd_preview[:117]}..."
        logger.info("[BashTool] 执行 shell 命令: cwd={} cmd={!r}", workdir.name, cmd_preview)

        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-lc",
            command,
            cwd=str(workdir),
            start_new_session=True,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **os.environ,
                "HYPERFRAMES_SKIP_SKILLS": "1",
                "CI": "1",
            },
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_s,
            )
        except (TimeoutError, asyncio.CancelledError) as exc:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await proc.communicate()
            if isinstance(exc, asyncio.CancelledError):
                raise
            logger.error("[BashTool] 命令执行超时 (>{}s): cmd={!r}", timeout_s, cmd_preview)
            return {"stderr": f"命令超时（>{timeout_s}s）", "stdout": "", "exit_code": -1}

        out_str = stdout.decode("utf-8", "replace")
        err_str = stderr.decode("utf-8", "replace")
        logger.info(
            "[BashTool] 命令执行完成: exit={} stdout_len={} stderr_len={}",
            proc.returncode, len(out_str), len(err_str),
        )
        return {
            "stdout": truncate_output(out_str),
            "stderr": truncate_output(err_str),
            "exit_code": proc.returncode,
        }

    return Tool(
        name="bash",
        description=(
            "在工作目录执行 shell 命令。用于写文件、跑 CLI、查看目录。"
            "工作目录已是本轮任务目录，命令里用相对路径即可。"
        ),
        args_model=BashArgs,
        handler=bash,
    )
