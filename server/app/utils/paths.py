"""
全局路径常量，统一从 .env 读取。

所有模块通过 from app.utils.paths import XXX_DIR 获取路径，
不再各自计算 Path(__file__).resolve().parents[X]。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# server/ 根目录（唯一的路径锚点）
SERVER_DIR = Path(__file__).resolve().parents[2]

# 加载 .env（只在首次 import 时执行一次）
load_dotenv(SERVER_DIR / ".env", override=False)


def _env_path(key: str, default: str) -> Path:
    """从环境变量读取相对路径，转为基于 SERVER_DIR 的绝对路径。"""
    return SERVER_DIR / os.getenv(key, default)


# 导出路径常量
SKILLS_DIR = _env_path("SKILLS_DIR", "skills")
WORKPLACE_DIR = _env_path("WORKPLACE_DIR", "workplace")
LOGS_DIR = _env_path("LOGS_DIR", "logs")
KNOWLEDGE_BASE_DIR = _env_path("KNOWLEDGE_BASE_DIR", "data")
