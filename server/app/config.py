"""
统一配置模块。

从环境变量读取所有配置，提供 typed settings。
load_dotenv() 由 main.py 统一调用，此模块不做 load_dotenv。
"""

import os


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int = 0) -> int:
    return int(os.getenv(key, str(default)))


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default).lower()) in ("true", "1", "yes")


# Server
SERVER_HOST: str = _env("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = _env_int("SERVER_PORT", 9999)

# Database
DB_HOST: str = _env("DB_HOST", "localhost")
DB_PORT: int = _env_int("DB_PORT", 3306)
DB_USER: str = _env("DB_USER", "root")
DB_PASSWORD: str = _env("DB_PASSWORD")
DB_NAME: str = _env("DB_NAME", "agent")
DB_ECHO: bool = _env_bool("DB_ECHO", False)
DB_POOL_SIZE: int = _env_int("DB_POOL_SIZE", 10)
DB_MAX_OVERFLOW: int = _env_int("DB_MAX_OVERFLOW", 20)
DB_POOL_RECYCLE: int = _env_int("DB_POOL_RECYCLE", 1800)
DB_POOL_TIMEOUT: int = _env_int("DB_POOL_TIMEOUT", 30)

# JWT
JWT_SECRET_KEY: str = _env("JWT_SECRET_KEY", "")
JWT_ALGORITHM: str = _env("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_DAYS: int = _env_int("JWT_EXPIRE_DAYS", 7)

# LLM
OPENAI_API_KEY: str = _env("OPENAI_API_KEY", "")
OPENAI_MODEL: str = _env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_BASE: str = _env("OPENAI_API_BASE", "")
FAST_LLM_MODEL: str = _env("FAST_LLM_MODEL", "general")
FAST_LLM_API_KEY: str = _env("FAST_LLM_API_KEY", OPENAI_API_KEY)

# Vision
GLM_VISION_MODEL: str = _env("GLM_VISION_MODEL", "glm-4v-flash")
GLM_API_KEY: str = _env("GLM_API_KEY", "")

# Agent
LLM_TIMEOUT: int = _env_int("LLM_TIMEOUT", 300)
MAX_MESSAGE_HISTORY: int = _env_int("MAX_MESSAGE_HISTORY", 20)

# Debug
APP_DEBUG: bool = _env_bool("APP_DEBUG", False)
