"""
安全 Shell 执行工具（白名单模式）。

仅允许执行预定义的安全命令，用于代码 Agent 的受限环境。
与 shell_executor.py 的区别：
  - shell_executor: 通用型，黑名单过滤
  - shell_execute:  严格型，白名单放行
"""

import shlex
import subprocess
from pathlib import Path
from langchain.tools import tool

from app.shared.paths import SERVER_DIR
from app.tools.registry import register

# 白名单命令
ALLOWED_COMMANDS = {
    "ls", "pwd", "echo", "cat", "grep", "find",
    "head", "tail", "python3", "node",
}

# 黑名单关键词
BLOCKED_KEYWORDS = {
    "rm", "shutdown", "reboot", "mkfs", "dd",
    "chmod", "chown", "kill", "pkill", "sudo", "su",
}

# 危险符号（防止命令拼接攻击）
DANGEROUS_SYMBOLS = {
    ";", "&&", "||", "|", "`", "$(", ">", ">>", "<",
}


def is_safe_command(command: str):
    """检查命令是否安全"""
    for symbol in DANGEROUS_SYMBOLS:
        if symbol in command:
            return False, f"包含危险符号: {symbol}"

    try:
        parts = shlex.split(command)
    except Exception:
        return False, "命令解析失败"

    if not parts:
        return False, "空命令"

    base_cmd = parts[0]

    if base_cmd not in ALLOWED_COMMANDS:
        return False, f"命令不在白名单: {base_cmd}"

    for keyword in BLOCKED_KEYWORDS:
        if keyword in parts:
            return False, f"包含黑名单命令: {keyword}"

    return True, "安全"


@tool("safe_shell", description="安全执行受限的Shell命令，仅支持白名单命令")
def safe_shell(command: str) -> str:
    """执行安全Shell命令（带白名单和黑名单控制）"""
    is_safe, message = is_safe_command(command)
    if not is_safe:
        return f" 拒绝执行: {message}"

    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(SERVER_DIR),
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode != 0:
            return f"执行失败:\n{error}"

        return output if output else "执行成功（无输出）"

    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"执行异常: {str(e)}"


# 自注册到工具注册表
register(safe_shell)