"""
全局路径常量。

环境变量由 app.main 统一加载；这里仅从已存在的进程环境读取。
"""

import os
from pathlib import Path

# server/ 根目录（唯一的路径锚点）
SERVER_DIR = Path(__file__).resolve().parents[2]


def _env_path(key: str, default: str) -> Path:
    """从环境变量读取相对路径，转为基于 SERVER_DIR 的绝对路径。"""
    return SERVER_DIR / os.getenv(key, default)


# 导出路径常量
WORKPLACE_DIR = _env_path("WORKPLACE_DIR", "workplace")
LOGS_DIR = _env_path("LOGS_DIR", "logs")
KNOWLEDGE_BASE_DIR = _env_path("KNOWLEDGE_BASE_DIR", "data")
