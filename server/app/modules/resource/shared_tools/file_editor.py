"""
文件编辑工具。

提供文件写入、追加、行级编辑能力：
- write_file: 创建或覆盖文件
- edit_file: 按行号范围替换内容
- append_file: 追加内容到文件末尾
- read_file_lines: 读取文件指定行范围

与 file_handler.py 中的 read_file_safe 互补，
后者提供安全的只读文件读取能力。
"""

import os
import re
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.utils.paths import SERVER_DIR, WORKPLACE_DIR

# ──────────────────────────────────────────────────────────────
# 安全策略
# ──────────────────────────────────────────────────────────────

ALLOWED_BASE_DIRS: list[Path] = [
    SERVER_DIR,
    WORKPLACE_DIR,
]

# 禁止写入的路径模式
BLOCKED_WRITE_PATTERNS: list[str] = [
    ".env",
    ".git/",
    "__pycache__/",
]

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _is_write_allowed(filepath: str) -> tuple[bool, Path, str]:
    """检查文件写入路径是否安全。

    Returns:
        (is_allowed, resolved_path, reason) 三元组
    """
    try:
        p = Path(filepath).resolve()
    except (OSError, ValueError) as e:
        return False, Path(filepath), f"路径解析失败: {e}"

    # 检查是否在允许的根目录下
    in_allowed = any(
        str(p).startswith(str(base.resolve()))
        for base in ALLOWED_BASE_DIRS
    )
    if not in_allowed:
        return False, p, f"路径不在允许范围内: {p}"

    # 检查是否匹配禁止模式
    path_str = str(p)
    for pattern in BLOCKED_WRITE_PATTERNS:
        if pattern in path_str:
            return False, p, f"禁止写入受保护路径: {pattern}"

    return True, p, ""


# ──────────────────────────────────────────────────────────────
# @tool 工具函数
# ──────────────────────────────────────────────────────────────

@tool("write_file")
def write_file(
    filepath: str,
    content: str,
    create_dirs: bool = True,
) -> str:
    """创建或覆盖文件，写入指定内容。

    Args:
        filepath: 目标文件路径（必须在项目目录下）
        content: 要写入的文件内容
        create_dirs: 是否自动创建父目录

    Returns:
        操作结果（成功返回文件路径，失败返回错误信息）
    """
    allowed, resolved, reason = _is_write_allowed(filepath)
    if not allowed:
        return f"❌ {reason}"

    if len(content) > MAX_FILE_SIZE:
        return f"❌ 内容过大: {len(content)} 字节（最大 {MAX_FILE_SIZE} 字节）"

    try:
        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        resolved.write_text(content, encoding="utf-8")
        return f"✓ 文件已写入: {resolved} ({len(content)} 字符)"

    except Exception as e:
        return f"❌ 写入失败: {type(e).__name__}: {e}"


@tool("edit_file")
def edit_file(
    filepath: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> str:
    """按行号范围替换文件内容。

    Args:
        filepath: 文件路径
        start_line: 起始行号（从 1 开始，包含）
        end_line: 结束行号（包含，若与 start_line 相同则替换单行）
        new_content: 替换后的新内容

    Returns:
        操作结果
    """
    allowed, resolved, reason = _is_write_allowed(filepath)
    if not allowed:
        return f"❌ {reason}"

    if not resolved.exists():
        return f"❌ 文件不存在: {filepath}"

    try:
        lines = resolved.read_text(encoding="utf-8").splitlines(keepends=True)
        total_lines = len(lines)

        # 边界检查
        if start_line < 1 or start_line > total_lines:
            return f"❌ 起始行号无效: {start_line}（文件共 {total_lines} 行）"
        if end_line < start_line:
            return f"❌ 结束行号不能小于起始行号: end={end_line} < start={start_line}"
        end_line = min(end_line, total_lines)

        # 构建新内容（保持换行符一致）
        new_lines = new_content.splitlines(keepends=True)
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"

        # 替换
        replaced_count = end_line - start_line + 1
        new_all_lines = lines[: start_line - 1] + new_lines + lines[end_line:]

        resolved.write_text("".join(new_all_lines), encoding="utf-8")

        return (
            f"✓ 文件已编辑: {resolved}\n"
            f"  替换行 {start_line}-{end_line}（共 {replaced_count} 行）→ {len(new_lines)} 行\n"
            f"  文件总行数: {total_lines} → {len(new_all_lines)}"
        )

    except Exception as e:
        return f"❌ 编辑失败: {type(e).__name__}: {e}"


@tool("append_file")
def append_file(
    filepath: str,
    content: str,
) -> str:
    """追加内容到文件末尾（文件不存在则创建）。

    Args:
        filepath: 目标文件路径
        content: 要追加的内容

    Returns:
        操作结果
    """
    allowed, resolved, reason = _is_write_allowed(filepath)
    if not allowed:
        return f"❌ {reason}"

    if len(content) > MAX_FILE_SIZE:
        return f"❌ 内容过大: {len(content)} 字节"

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # 确保追加前有换行
        existing = ""
        if resolved.exists():
            existing = resolved.read_text(encoding="utf-8")
            if existing and not existing.endswith("\n"):
                existing += "\n"

        resolved.write_text(existing + content, encoding="utf-8")

        total = len(existing) + len(content)
        return f"✓ 内容已追加: {resolved}（文件总大小: {_format_size(len(existing + content))})"

    except Exception as e:
        return f"❌ 追加失败: {type(e).__name__}: {e}"


@tool("read_file_lines")
def read_file_lines(
    filepath: str,
    start_line: int = 1,
    end_line: int = 0,
    show_line_numbers: bool = True,
) -> str:
    """读取文件的指定行范围（比 read_file_safe 更精确的行级读取）。

    Args:
        filepath: 文件路径
        start_line: 起始行号（从 1 开始）
        end_line: 结束行号（0 表示读到末尾）
        show_line_numbers: 是否显示行号

    Returns:
        指定行范围的内容
    """
    # 复用 file_handler 的路径安全检查
    from app.modules.resource.shared_tools.file_handler import FileHandler

    try:
        path = Path(filepath)
        if not path.is_absolute():
            path = SERVER_DIR / path
        path = path.resolve()

        if not FileHandler.is_safe_path(path):
            return "❌ 拒绝访问：越权路径"

        if not path.exists():
            return f"❌ 文件不存在: {filepath}"

        if path.stat().st_size > MAX_FILE_SIZE:
            return f"❌ 文件过大（超过 {MAX_FILE_SIZE} 字节）"

        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        total_lines = len(lines)
        start = max(start_line, 1) - 1  # 转为 0-based
        end = end_line if end_line > 0 else total_lines
        end = min(end, total_lines)

        selected = lines[start:end]

        if show_line_numbers:
            numbered = []
            for i, line in enumerate(selected, start=start + 1):
                numbered.append(f"{i:>6}\t{line}")
            result = "\n".join(numbered)
        else:
            result = "\n".join(selected)

        header = f"文件: {path} (行 {start+1}-{end}/{total_lines})\n{'─' * 50}\n"
        return header + result

    except Exception as e:
        return f"❌ 读取失败: {type(e).__name__}: {e}"


# ──────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────

def _format_size(size: int) -> str:
    """将字节数格式化为可读字符串。"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"