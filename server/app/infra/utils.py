"""共享工具模块：服务异常与 LLM 输出 JSON 解析。

- ServiceError: 外部服务（LLM / 数据库 / 第三方 API）不可用
- parse_first_json_object(): 从文本中提取首个 JSON 对象
- strip_markdown_code_fences(): 去掉 Markdown 代码围栏
"""

# 本模块提供服务异常与 LLM 输出 JSON 解析工具
from __future__ import annotations

import json
from typing import Any


# ============ 异常定义 ============

# 外部服务不可用异常（LLM / 数据库 / 第三方 API 失败）
class ServiceError(Exception):
    """外部服务不可用异常。

    当 LLM、数据库、第三方 API 等外部服务调用失败时抛出。
    """

    def __init__(self, message: str = "") -> None:
        """初始化服务异常。"""
        self.message = message
        super().__init__(message)


# ============ JSON 解析工具 ============


# 去除 Markdown 代码围栏（```json ... ```），仅做字符串操作
def strip_markdown_code_fences(text: str) -> str:
    """去掉 Markdown 代码围栏（```json ... ```）。

    LLM 输出常带有 Markdown 格式的代码块，需要清理后才能解析 JSON。
    不使用正则表达式，通过字符串操作实现。

    Args:
        text: 可能包含 Markdown 代码围栏的文本

    Returns:
        去除代码围栏后的纯文本
    """
    if not text:
        return ""
    raw = text.strip()
    # 如果不以 ``` 开头，直接返回
    if not raw.startswith("```"):
        return raw
    # 过滤掉以 ``` 开头的行（代码围栏标记）
    lines = [line for line in raw.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def parse_first_json_object(text: str) -> dict[str, Any]:
    """Parse one outer JSON object without salvaging nested fragments.

    A prose prefix and a Markdown fence are tolerated. If the outer object is
    malformed, the error is preserved instead of returning a valid list or
    object nested inside the broken response.
    """
    cleaned = strip_markdown_code_fences(text)
    if not cleaned:
        raise json.JSONDecodeError("empty input", "", 0)

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise
        value, _end = json.JSONDecoder().raw_decode(cleaned[start:])

    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object(dict), got {type(value).__name__}")
    return value


# 将任意值摘要为单行截断字符串，用于安全记录日志
