"""``bash`` —— 在工作目录执行 shell 命令。"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import BASH_TIMEOUT_S, truncate


class BashArgs(BaseModel):
    """执行 shell 命令。"""

    command: str = Field(min_length=1, max_length=8000, description="要执行的 shell 命令")


def build(workdir: Path) -> Tool:
    """构造 bash 工具。``workdir`` 是命令的工作目录。"""

    async def bash(command: str) -> dict[str, Any]:
        dangerous = ("rm -rf /", "sudo ", "shutdown", "reboot")
        if any(d in command for d in dangerous):
            return {"text": "拒绝执行危险命令", "status": "failed"}

        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-lc",
            command,
            cwd=str(workdir),
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
                timeout=BASH_TIMEOUT_S,
            )
        except TimeoutError:
            proc.kill()
            return {"text": f"命令超时（>{BASH_TIMEOUT_S}s）", "status": "failed"}

        parts: list[str] = []
        out = stdout.decode("utf-8", "ignore").strip()
        err = stderr.decode("utf-8", "ignore").strip()
        if out:
            parts.append(out)
        if err:
            parts.append(f"[stderr]\n{err}")
        text = truncate("\n\n".join(parts)) if parts else f"命令完成（exit {proc.returncode}），无输出。"
        return {"text": text, "status": "ok" if proc.returncode == 0 else "failed"}

    return Tool(
        name="bash",
        description=(
            "在工作目录执行 shell 命令。用于写文件、跑 CLI、查看目录。"
            "工作目录已是本轮任务目录，命令里用相对路径即可。"
        ),
        args_model=BashArgs,
        handler=bash,
    )
