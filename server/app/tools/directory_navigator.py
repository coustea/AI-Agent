"""
目录导航与文件搜索工具。

提供文件系统浏览能力：
- list_directory: 列出目录内容（带类型标记）
- file_tree: 显示目录树结构
- find_files: 按名称/扩展名模式搜索文件
- get_file_info: 获取文件/目录元信息
"""

import os
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.shared.paths import SERVER_DIR, WORKPLACE_DIR
from app.tools.registry import register

# ──────────────────────────────────────────────────────────────
# 安全策略
# ──────────────────────────────────────────────────────────────

ALLOWED_BASE_DIRS: list[Path] = [
    SERVER_DIR,
    WORKPLACE_DIR,
]

MAX_TREE_DEPTH = 5
MAX_FIND_RESULTS = 100
MAX_LIST_ENTRIES = 200


def _is_path_allowed(target: str) -> tuple[bool, Path]:
    try:
        p = Path(target).resolve()
        if not p.exists():
            return False, p
        allowed = any(
            str(p).startswith(str(base.resolve()))
            for base in ALLOWED_BASE_DIRS
        )
        return allowed, p
    except (OSError, ValueError):
        return False, Path(target)


# ──────────────────────────────────────────────────────────────
# @tool 工具函数
# ──────────────────────────────────────────────────────────────

@tool("list_directory")
def list_directory(
    path: str = "",
    show_hidden: bool = False,
    pattern: str = "",
) -> str:
    """列出指定目录下的文件和子目录。

    Args:
        path: 目录路径（留空则列出 server 目录）
        show_hidden: 是否显示隐藏文件（以 . 开头）
        pattern: 文件名过滤模式（glob 语法，如 "*.py"）

    Returns:
        目录内容列表，带类型标记（[DIR] / [FILE] / 大小）
    """
    target = path or str(SERVER_DIR)
    allowed, resolved = _is_path_allowed(target)

    if not allowed:
        return f"❌ 路径被拒绝: {target}（仅允许项目目录）"

    if not resolved.is_dir():
        return f"❌ 不是目录: {target}"

    try:
        entries = sorted(resolved.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))

        lines = [f"📁 {resolved}/", ""]
        count = 0

        for entry in entries:
            if count >= MAX_LIST_ENTRIES:
                lines.append(f"... (已截断，最多显示 {MAX_LIST_ENTRIES} 项)")
                break

            if not show_hidden and entry.name.startswith("."):
                continue

            if pattern and entry.is_file():
                if not entry.match(pattern):
                    continue

            if entry.is_dir():
                lines.append(f"  [DIR]  {entry.name}/")
            else:
                size = entry.stat().st_size
                size_str = _format_size(size)
                lines.append(f"  [FILE] {entry.name}  ({size_str})")

            count += 1

        lines.append(f"\n共 {count} 项")
        return "\n".join(lines)

    except PermissionError:
        return f"❌ 权限不足: {target}"
    except Exception as e:
        return f"❌ 列出目录失败: {type(e).__name__}: {e}"


@tool("file_tree")
def file_tree(
    path: str = "",
    max_depth: int = 3,
    ignore_dirs: str = "__pycache__,.git,node_modules,.venv,.idea",
) -> str:
    """显示目录树结构（类似 tree 命令）。

    Args:
        path: 目录路径（留空则使用 server 目录）
        max_depth: 最大递归深度（1-5）
        ignore_dirs: 要忽略的目录名（逗号分隔）

    Returns:
        目录树的文本表示
    """
    target = path or str(SERVER_DIR)
    allowed, resolved = _is_path_allowed(target)

    if not allowed:
        return f"❌ 路径被拒绝: {target}"

    if not resolved.is_dir():
        return f"❌ 不是目录: {target}"

    max_depth = min(max(max_depth, 1), MAX_TREE_DEPTH)
    ignore_set = set(d.strip() for d in ignore_dirs.split(",") if d.strip())

    lines: list[str] = [f"{resolved.name}/"]
    _build_tree(resolved, lines, prefix="", depth=0, max_depth=max_depth, ignore=ignore_set)

    return "\n".join(lines)


@tool("find_files")
def find_files(
    name_pattern: str = "",
    extension: str = "",
    path: str = "",
    max_results: int = 50,
) -> str:
    """在目录中搜索文件。

    Args:
        name_pattern: 文件名包含的关键字（如 "agent"）
        extension: 文件扩展名（如 ".py"，不含点也行）
        path: 搜索起始目录（留空则使用 server 目录）
        max_results: 最大返回结果数

    Returns:
        匹配的文件路径列表
    """
    target = path or str(SERVER_DIR)
    allowed, resolved = _is_path_allowed(target)

    if not allowed:
        return f"❌ 路径被拒绝: {target}"

    if not resolved.is_dir():
        return f"❌ 不是目录: {target}"

    if extension and not extension.startswith("."):
        extension = f".{extension}"

    max_results = min(max_results, MAX_FIND_RESULTS)
    results: list[str] = []

    try:
        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for filename in sorted(files):
                filepath = Path(root) / filename

                if extension and filepath.suffix.lower() != extension.lower():
                    continue

                if name_pattern and name_pattern.lower() not in filename.lower():
                    continue

                try:
                    rel = filepath.relative_to(resolved)
                    results.append(str(rel))
                except ValueError:
                    results.append(str(filepath))

                if len(results) >= max_results:
                    break

            if len(results) >= max_results:
                break

        if not results:
            return f"未找到匹配文件 (pattern={name_pattern!r}, ext={extension!r})"

        lines = [f"在 {resolved} 中找到 {len(results)} 个文件:", ""]
        lines.extend(f"  {r}" for r in results)
        return "\n".join(lines)

    except Exception as e:
        return f"❌ 搜索失败: {type(e).__name__}: {e}"


@tool("get_file_info")
def get_file_info(path: str) -> str:
    """获取文件或目录的详细信息（大小、权限、修改时间等）。

    Args:
        path: 文件或目录路径

    Returns:
        文件元信息
    """
    allowed, resolved = _is_path_allowed(path)

    if not allowed:
        return f"❌ 路径被拒绝: {path}"

    if not resolved.exists():
        return f"❌ 不存在: {path}"

    try:
        stat = resolved.stat()
        import time

        lines = [
            f"路径: {resolved}",
            f"类型: {'目录' if resolved.is_dir() else '文件'}",
            f"大小: {_format_size(stat.st_size)}",
            f"修改时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))}",
            f"权限: {oct(stat.st_mode)[-3:]}",
        ]

        if resolved.is_file():
            lines.append(f"扩展名: {resolved.suffix or '(无)'}")

        if resolved.is_dir():
            try:
                items = list(resolved.iterdir())
                files = sum(1 for i in items if i.is_file())
                dirs = sum(1 for i in items if i.is_dir())
                lines.append(f"内容: {dirs} 个目录, {files} 个文件")
            except PermissionError:
                pass

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 获取信息失败: {type(e).__name__}: {e}"


# ──────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────

def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _build_tree(
    directory: Path,
    lines: list[str],
    prefix: str,
    depth: int,
    max_depth: int,
    ignore: set[str],
) -> None:
    if depth >= max_depth:
        return

    try:
        entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return

    entries = [
        e for e in entries
        if e.name not in ignore and not e.name.startswith(".")
    ]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            _build_tree(entry, lines, prefix + child_prefix, depth + 1, max_depth, ignore)
        else:
            lines.append(f"{prefix}{connector}{entry.name}")


# 自注册到工具注册表
register(list_directory)
register(file_tree)
register(find_files)
register(get_file_info)