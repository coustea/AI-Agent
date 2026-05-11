"""Prompt 加载工具。

模块职责：
- 从 .md 文件加载 prompt 模板
- 支持变量占位符替换
- 缓存已加载的 prompt
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(filename: str) -> str:
    """加载 prompt 文件内容。

    Args:
        filename: prompt 文件名（相对于 prompts 目录）。

    Returns:
        prompt 文件内容。

    Raises:
        FileNotFoundError: prompt 文件不存在。
    """
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(filename: str, **variables: str) -> str:
    """加载并渲染 prompt 模板。

    Args:
        filename: prompt 文件名。
        **variables: 模板变量。

    Returns:
        渲染后的 prompt 文本。
    """
    template = load_prompt(filename)
    return template.format(**variables)
