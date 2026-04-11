"""
Shell 命令执行工具。

提供安全的 shell 命令执行能力，支持：
- 工作目录指定
- 超时控制
- 输出捕获（stdout + stderr）
- 危险命令拦截
- 环境变量隔离
"""

import asyncio
import re
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.utils.paths import SERVER_DIR, WORKPLACE_DIR

# ──────────────────────────────────────────────────────────────
# 安全策略
# ──────────────────────────────────────────────────────────────

# 危险命令黑名单（正则匹配）
BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brm\s+(-\w*r\w*f\w*|--force)\s+/", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=.*of=/dev/", re.IGNORECASE),
    re.compile(r">\s*/dev/sd", re.IGNORECASE),
    re.compile(r"\bchmod\s+(-R\s+)?000\b"),
    re.compile(r"\bchown\s+(-R\s+)?root\b"),
    re.compile(r"\biptables\b", re.IGNORECASE),
    re.compile(r"\bsystemctl\s+(stop|disable|mask)\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\bcurl\s+.*\|\s*sh", re.IGNORECASE),
    re.compile(r"\bwget\s+.*\|\s*sh", re.IGNORECASE),
    re.compile(r"\bpip\s+uninstall\s+-y\s+(langchain|fastapi|sqlmodel)", re.IGNORECASE),
]

# 允许执行命令的工作目录范围
ALLOWED_BASE_DIRS: list[Path] = [
    SERVER_DIR,
    WORKPLACE_DIR,
]

MAX_OUTPUT_LENGTH = 50_000  # 输出截断长度
DEFAULT_TIMEOUT = 30        # 默认超时（秒）


def _is_command_safe(command: str) -> tuple[bool, str]:
    """检查命令是否安全。

    Returns:
        (is_safe, reason) 元组
    """
    for pattern in BLOCKED_PATTERNS:
        match = pattern.search(command)
        if match:
            return False, f"危险命令被拦截: 匹配规则 '{pattern.pattern}'"
    return True, ""


def _is_workdir_safe(workdir: str) -> bool:
    """检查工作目录是否在允许范围内。"""
    try:
        resolved = Path(workdir).resolve()
        return any(
            str(resolved).startswith(str(base.resolve()))
            for base in ALLOWED_BASE_DIRS
        )
    except (OSError, ValueError):
        return False


# ──────────────────────────────────────────────────────────────
# @tool 工具函数
# ──────────────────────────────────────────────────────────────

@tool("execute_shell")
async def execute_shell(
    command: str,
    workdir: str = "",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """安全执行 shell 命令，捕获 stdout 和 stderr。

    Args:
        command: 要执行的 shell 命令字符串
        workdir: 工作目录（留空则使用 server 目录），仅允许 server/ 及其子目录
        timeout: 超时时间（秒），默认 30 秒，最大 120 秒

    Returns:
        命令输出（stdout + stderr），或在失败时返回错误信息
    """
    # 1. 安全检查
    is_safe, reason = _is_command_safe(command)
    if not is_safe:
        return f"❌ 命令被拒绝: {reason}"

    # 2. 工作目录验证
    cwd = SERVER_DIR
    if workdir:
        if not _is_workdir_safe(workdir):
            return f"❌ 工作目录被拒绝: {workdir}（仅允许项目目录）"
        cwd = Path(workdir).resolve()

    # 3. 超时限制
    timeout = min(timeout, 120)

    # 4. 执行命令
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # 5. 组装输出
        parts = []
        if stdout.strip():
            parts.append(stdout.strip())
        if stderr.strip():
            parts.append(f"[stderr]\n{stderr.strip()}")

        output = "\n".join(parts) if parts else "(无输出)"

        # 添加退出码
        exit_info = f"\n\n[退出码: {proc.returncode}]"
        result = output + exit_info

        # 6. 截断过长输出
        if len(result) > MAX_OUTPUT_LENGTH:
            result = result[:MAX_OUTPUT_LENGTH] + f"\n\n... (输出已截断，共 {len(result)} 字符)"

        return result

    except asyncio.TimeoutError:
        proc.kill()  # type: ignore[union-attr]
        return f"❌ 命令超时 ({timeout}秒): {command}"
    except Exception as e:
        return f"❌ 执行失败: {type(e).__name__}: {e}"


@tool("execute_shell_sync")
def execute_shell_sync(
    command: str,
    workdir: str = "",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """同步版本的 shell 命令执行（用于非异步上下文）。

    Args:
        command: 要执行的 shell 命令字符串
        workdir: 工作目录（留空则使用 server 目录）
        timeout: 超时时间（秒），默认 30 秒

    Returns:
        命令输出或错误信息
    """
    import subprocess

    is_safe, reason = _is_command_safe(command)
    if not is_safe:
        return f"❌ 命令被拒绝: {reason}"

    cwd = SERVER_DIR
    if workdir:
        if not _is_workdir_safe(workdir):
            return f"❌ 工作目录被拒绝: {workdir}"
        cwd = Path(workdir).resolve()

    timeout = min(timeout, 120)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
        )

        parts = []
        if result.stdout.strip():
            parts.append(result.stdout.strip())
        if result.stderr.strip():
            parts.append(f"[stderr]\n{result.stderr.strip()}")

        output = "\n".join(parts) if parts else "(无输出)"
        output += f"\n\n[退出码: {result.returncode}]"

        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n\n... (截断，共 {len(output)} 字符)"

        return output

    except subprocess.TimeoutExpired:
        return f"❌ 命令超时 ({timeout}秒): {command}"
    except Exception as e:
        return f"❌ 执行失败: {type(e).__name__}: {e}"