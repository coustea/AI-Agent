"""算法模板注册表。管理算法元信息和模板代码。
 * service.py 调用 get_all_algorithms / get_algorithm_info / get_template_code / LANGUAGES。"""

from __future__ import annotations

import os
from typing import Any, Dict, List

# 模板根目录
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 支持的语言列表
LANGUAGES: List[Dict[str, str]] = [
    {"key": "python", "label": "Python", "extension": "py"},
    {"key": "javascript", "label": "JavaScript", "extension": "js"},
    {"key": "cpp", "label": "C++", "extension": "cpp"},
    {"key": "java", "label": "Java", "extension": "java"},
    {"key": "c", "label": "C", "extension": "c"},
]

# 语言 key → 模板文件名
_LANGUAGE_FILE_MAP: Dict[str, str] = {
    "python": "python.py",
    "javascript": "js.js",
    "cpp": "cpp.cpp",
    "java": "java.java",
    "c": "c.c",
}

# 算法元信息注册表
ALGORITHMS: Dict[str, Dict[str, Any]] = {
    "bubble_sort": {
        "domain": "data_structure",
        "name": "冒泡排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_array", "compare", "swap", "mark_sorted", "finish"],
    },
    "selection_sort": {
        "domain": "data_structure",
        "name": "选择排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_array", "compare", "swap", "mark_sorted", "finish"],
    },
    "insertion_sort": {
        "domain": "data_structure",
        "name": "插入排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_array", "compare", "assign", "mark_sorted", "finish"],
    },
    "binary_search": {
        "domain": "data_structure",
        "name": "二分查找",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"],
    },
    "bracket_match": {
        "domain": "data_structure",
        "name": "括号匹配",
        "visualizer_type": "stack-queue",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_stack", "push", "pop", "highlight_input", "finish"],
    },
    "queue_simulation": {
        "domain": "data_structure",
        "name": "队列模拟",
        "visualizer_type": "stack-queue",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_queue", "enqueue", "dequeue", "finish"],
    },
}


def get_all_algorithms(domain: str = "data_structure") -> List[Dict[str, Any]]:
    """获取指定 domain 下的所有算法信息列表。"""
    result = []
    for key, info in ALGORITHMS.items():
        if info["domain"] == domain:
            result.append({"key": key, **info})
    return result


def get_algorithm_info(algorithm_key: str) -> Dict[str, Any]:
    """获取单个算法的元信息，不存在则抛出 ValueError。"""
    info = ALGORITHMS.get(algorithm_key)
    if not info:
        raise ValueError(f"不支持的算法: {algorithm_key}")
    return {"key": algorithm_key, **info}


def get_template_code(algorithm_key: str, language: str) -> str:
    """读取并返回指定算法+语言的模板代码。"""
    info = get_algorithm_info(algorithm_key)
    if language not in info["supported_languages"]:
        raise ValueError(f"算法 {algorithm_key} 不支持语言 {language}")

    filename = _LANGUAGE_FILE_MAP.get(language)
    if not filename:
        raise ValueError(f"不支持的语言: {language}")

    filepath = os.path.join(_TEMPLATES_DIR, info["domain"], algorithm_key, filename)
    if not os.path.isfile(filepath):
        raise ValueError(f"模板文件不存在: {algorithm_key}/{language}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def get_supported_languages(algorithm_key: str) -> List[str]:
    """获取指定算法支持的语言列表。"""
    info = get_algorithm_info(algorithm_key)
    return info["supported_languages"]
