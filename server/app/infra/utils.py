"""共享工具：异常定义与 JSON 解析。

异常层级：
- AppError → ServiceError / NotFoundError / ForbiddenError

JSON 工具（用于 LLM 输出解析）：
- parse_first_json_object(): 从文本中提取首个 JSON 对象
- strip_markdown_code_fences(): 去掉 Markdown 代码围栏
- preview_for_log(): 日志摘要
"""

from __future__ import annotations

import json
from typing import Any


# ============ 异常定义 ============


class AppError(Exception):
    """应用异常基类。"""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class ServiceError(AppError):
    """外部服务不可用（LLM、数据库等）。"""


class NotFoundError(AppError):
    """资源不存在。"""


class ForbiddenError(AppError):
    """权限不足。"""


# ============ JSON 解析 ============


def strip_markdown_code_fences(text: str) -> str:
    """去掉 Markdown code fence（不使用正则）。"""
    if not text:
        return ""
    raw = text.strip()
    if not raw.startswith("```"):
        return raw
    lines = [line for line in raw.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def parse_first_json_value(text: str) -> Any:
    """从文本中解析出第一个 JSON 值（dict/list/str/number/bool/null）。

    不使用正则。解析策略：
    1) 去除 code fence
    2) 尝试 json.loads（要求整体即 JSON）
    3) 使用 JSONDecoder.raw_decode 扫描第一个 '{' / '[' 起点并解析
    """
    cleaned = strip_markdown_code_fences(text)
    if not cleaned:
        raise json.JSONDecodeError("empty input", "", 0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    s = cleaned.strip()
    candidates: list[int] = []
    idx = s.find("{")
    while idx != -1:
        candidates.append(idx)
        idx = s.find("{", idx + 1)
    idx = s.find("[")
    while idx != -1:
        candidates.append(idx)
        idx = s.find("[", idx + 1)

    for start in sorted(set(candidates)):
        try:
            value, _end = decoder.raw_decode(s[start:])
            return value
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("no JSON value found", s, 0)


def parse_first_json_object(text: str) -> dict[str, Any]:
    """解析并保证返回 dict。"""
    value = parse_first_json_value(text)
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object(dict), got {type(value).__name__}")
    return value


def preview_for_log(value: Any, max_len: int = 500) -> str:
    """用于日志的输出摘要，避免日志过长。"""
    try:
        dumped = json.dumps(value, ensure_ascii=False)
    except Exception:
        dumped = str(value)
    dumped = dumped.replace("\n", " ")
    return dumped[:max_len] + ("..." if len(dumped) > max_len else "")
