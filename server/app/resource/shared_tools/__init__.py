"""
共享工具模块

提供跨 Agent 使用的通用工具函数和类。

工具清单：
  - file_handler:     文件读写（save_to_workplace, read_file_safe）
  - file_editor:      文件编辑（write_file, edit_file, append_file, read_file_lines）
  - shell_executor:   Shell 命令执行（execute_shell, execute_shell_sync）
  - code_runner:      多语言代码运行（run_code, run_file）
  - directory_navigator: 目录导航（list_directory, file_tree, find_files, get_file_info）
"""

# 文件处理
from .file_handler import FileHandler, save_to_workplace, read_file_safe

# 文件编辑
from .file_editor import write_file, edit_file, append_file, read_file_lines

# Shell 执行
from .shell_executor import execute_shell, execute_shell_sync

# 代码运行
from .code_runner import run_code, run_file

# 目录导航
from .directory_navigator import list_directory, file_tree, find_files, get_file_info

__all__ = [
    # file_handler
    "FileHandler",
    "save_to_workplace",
    "read_file_safe",
    # file_editor
    "write_file",
    "edit_file",
    "append_file",
    "read_file_lines",
    # shell_executor
    "execute_shell",
    "execute_shell_sync",
    # code_runner
    "run_code",
    "run_file",
    # directory_navigator
    "list_directory",
    "file_tree",
    "find_files",
    "get_file_info",
]
