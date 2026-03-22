import asyncio
import shutil
import logging
import re
import sys
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def shell_exec(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    """安全且异步地执行 shell 命令。用于运行系统命令或脚本。(注意：破坏性命令会被拦截)。"""
    timeout = min(max(timeout, 1), 300)

    dangerous_patterns = [
        r"\brm\b", r"\brmdir\b", r"\bunlink\b",
        r"\bmkfs\b", r"\bfdisk\b", r"\bdd\b", r">\s*/dev/",
        r"\bchmod\b", r"\bchown\b", r"\bchgrp\b",
        r":\(\)\{\s*:\|:&\s*\};:", r"\bsudo\b", r"\bsu\b",
        r"\bmv\b.*/dev/null", r"\bkill\b", r"\bpkill\b",
        r"\breboot\b", r"\bshutdown\b", r"\bhalt\b"
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, command_lower):
            logger.warning(f"Blocked dangerous command: {command}")
            return f"Error: Command blocked for safety. Dangerous pattern detected: {pattern}"

    try:
        if sys.platform == "win32":
            shell_path = shutil.which("powershell") or shutil.which("pwsh")
            if shell_path:
                process = await asyncio.create_subprocess_exec(
                    shell_path, "-NoProfile", "-Command", command,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    cwd=cwd, shell=True
                )
        else:
            shell_path = shutil.which("bash") or shutil.which("sh")
            if not shell_path:
                return "Error: No shell available (bash/sh not found)"
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=cwd, executable=shell_path
            )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        stdout = stdout_bytes.decode('utf-8', errors='replace').strip()
        stderr = stderr_bytes.decode('utf-8', errors='replace').strip()

        output_parts = []
        if stdout: output_parts.append(stdout)
        if stderr: output_parts.append(f"[stderr]\n{stderr}")
        output = "\n".join(output_parts).strip()

        if not output:
            return "Command executed successfully (no output)" if process.returncode == 0 else f"Command exited with code {process.returncode} (no output)"

        if process.returncode != 0:
            output = f"{output}\n\n[exit code: {process.returncode}]"
        return output

    except asyncio.TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"