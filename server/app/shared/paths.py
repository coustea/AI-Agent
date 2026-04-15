"""全局路径常量。"""
import os
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[2]


def _env_path(key: str, default: str) -> Path:
    return SERVER_DIR / os.getenv(key, default)


WORKPLACE_DIR = _env_path("WORKPLACE_DIR", "workplace")
LOGS_DIR = _env_path("LOGS_DIR", "logs")
KNOWLEDGE_BASE_DIR = _env_path("KNOWLEDGE_BASE_DIR", "data")
