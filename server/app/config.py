"""
统一配置模块。

从环境变量读取所有配置，提供 typed settings。
此模块是唯一的 `.env` 读取入口。
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int = 0) -> int:
    return int(os.getenv(key, str(default)))


def _env_float(key: str, default: float = 0.0) -> float:
    return float(os.getenv(key, str(default)))


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default).lower()) in ("true", "1", "yes")


# Server
SERVER_HOST: str = _env("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = _env_int("SERVER_PORT", 9999)

# Database
DB_SCHEME: str = _env("DB_SCHEME", "postgresql+asyncpg")
DB_HOST: str = _env("DB_HOST", "localhost")
DB_PORT: int = _env_int("DB_PORT", 5432)
DB_USER: str = _env("DB_USER", "postgres")
DB_PASSWORD: str = _env("DB_PASSWORD")
DB_NAME: str = _env("DB_NAME", "agent")
DATABASE_URL: str = _env("DATABASE_URL", "")
DB_ECHO: bool = _env_bool("DB_ECHO", False)
DB_POOL_SIZE: int = _env_int("DB_POOL_SIZE", 10)
DB_MAX_OVERFLOW: int = _env_int("DB_MAX_OVERFLOW", 20)
DB_POOL_RECYCLE: int = _env_int("DB_POOL_RECYCLE", 1800)
DB_POOL_TIMEOUT: int = _env_int("DB_POOL_TIMEOUT", 30)
DB_INIT_MAX_RETRIES: int = _env_int("DB_INIT_MAX_RETRIES", 5)
DB_INIT_RETRY_DELAY_SEC: float = _env_float("DB_INIT_RETRY_DELAY_SEC", 1.5)

# JWT
JWT_SECRET_KEY: str = _env("JWT_SECRET_KEY", "")
JWT_ALGORITHM: str = _env("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_DAYS: int = _env_int("JWT_EXPIRE_DAYS", 7)

# LLM
OPENAI_API_KEY: str = _env("OPENAI_API_KEY", "")
OPENAI_MODEL: str = _env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_BASE: str = _env("OPENAI_API_BASE", "")

# GLM
GLM_MODEL: str = _env("GLM_MODEL", "glm-4.7")

# Spark LLM (星火大模型 WebSocket API)
SPARK_APP_ID: str = _env("SPARK_APP_ID", "")
SPARK_API_KEY: str = _env("SPARK_API_KEY", "")
SPARK_API_SECRET: str = _env("SPARK_API_SECRET", "")

# Vision
GLM_VISION_MODEL: str = _env("GLM_VISION_MODEL", "glm-4v-flash")
GLM_API_KEY: str = _env("GLM_API_KEY", "")

# Agent
LLM_TIMEOUT: int = _env_int("LLM_TIMEOUT", 300)
MAX_MESSAGE_HISTORY: int = _env_int("MAX_MESSAGE_HISTORY", 20)
PROFILE_GATE_EVERY_N_ASSISTANT_TURNS: int = _env_int("PROFILE_GATE_EVERY_N_ASSISTANT_TURNS", 2)
CONTENT_AGENT_TIMEOUT_SECONDS: int = _env_int("CONTENT_AGENT_TIMEOUT_SECONDS", 360)
CONTENT_LLM_TIMEOUT: int = _env_int("CONTENT_LLM_TIMEOUT", 180)
MULTIMODAL_DOC_ENABLED: bool = _env_bool(

    "MULTIMODAL_DOC_ENABLED", True)

# Debug
APP_DEBUG: bool = _env_bool("APP_DEBUG", False)
LOG_LEVEL: str = _env("LOG_LEVEL", "INFO")
LANGCHAIN_DEBUG: bool = _env_bool("LANGCHAIN_DEBUG",
                                  )
LANGCHAIN_VERBOSE: bool = _env_bool("LANGCHAIN_VERBOSE", False)
LANGGRAPH_DEBUG: bool = _env_bool("LANGGRAPH_DEBUG", False)
DEEPAGENTS_DEBUG: bool = _env_bool("DEEPAGENTS_DEBUG", False)

# Spark Vision (星火图片理解) — 复用 Spark LLM 凭证
SPARK_VISION_APPID: str = _env("SPARK_VISION_APPID", SPARK_APP_ID)
SPARK_VISION_API_KEY: str = _env("SPARK_VISION_API_KEY", SPARK_API_KEY)
SPARK_VISION_API_SECRET: str = _env("SPARK_VISION_API_SECRET", SPARK_API_SECRET)

# Spark Image Generation (星火图片生成) - 复用相同凭证
SPARK_IMAGE_APPID: str = _env("APPID", "")
SPARK_IMAGE_API_KEY: str = _env("APIKey", "")
SPARK_IMAGE_API_SECRET: str = _env("APISecret", "")
SPARK_IMAGE_PATCH_ID: str = _env("SPARK_IMAGE_PATCH_ID", "")

# Avatar (数字人)
AVATAR_ASR_APP_ID: str = _env("AVATAR_ASR_APP_ID", "")
AVATAR_ASR_API_KEY: str = _env("AVATAR_ASR_API_KEY", "")
AVATAR_ASR_API_SECRET: str = _env("AVATAR_ASR_API_SECRET", "")
AVATAR_APP_ID: str = _env("AVATAR_APP_ID", "")
AVATAR_API_KEY: str = _env("AVATAR_API_KEY", "")
AVATAR_API_SECRET: str = _env("AVATAR_API_SECRET", "")
AVATAR_URL: str = _env("AVATAR_URL", "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact")
ANCHOR_ID: str = _env("ANCHOR_ID", "110017006")
VCN: str = _env("VCN", "x4_yezi")
IAT_URL: str = _env("IAT_URL", "wss://iat-api.xfyun.cn/v2/iat")
AVATAR_BRIDGE_PORT: int = _env_int("AVATAR_BRIDGE_PORT", 8765)

# Aliases for ASR (shared app_id/key/secret for ASR and Spark LLM)
ASR_SPARK_APP_ID: str = AVATAR_ASR_APP_ID or _env("ASR_SPARK_APP_ID", "")
ASR_SPARK_API_KEY: str = AVATAR_ASR_API_KEY or _env("ASR_SPARK_API_KEY", "")
ASR_SPARK_API_SECRET: str = AVATAR_ASR_API_SECRET or _env("ASR_SPARK_API_SECRET", "")

# Paths
WORKPLACE_DIR: str = _env("WORKPLACE_DIR", "workplace")
LOGS_DIR: str = _env("LOGS_DIR", "logs")
KNOWLEDGE_BASE_DIR: str = _env("KNOWLEDGE_BASE_DIR", "data")

# ChatDoc RAG (讯飞文档问答) — 复用 Spark Vision 凭证
CHATDOC_APP_ID: str = _env("CHATDOC_APP_ID", SPARK_VISION_APPID)
CHATDOC_API_SECRET: str = _env("CHATDOC_API_SECRET", SPARK_VISION_API_SECRET)
CHATDOC_ENABLED: bool = _env_bool("CHATDOC_ENABLED", False)

TAVILY_API_KEY: str = _env("TAVILY_API_KEY", "")

# Spark X (星火X模型 OpenAI兼容API)
SPARK_X_API_PASSWORD: str = _env("SPARK_X_API_PASSWORD", "")
SPARK_X_API_BASE: str = _env("SPARK_X_API_BASE", "https://spark-api-open.xf-yun.com/v2")

# Spark Max (星火语言模型 OpenAI兼容API，OpenAI SDK base_url 使用 /v1)
SPARK_MAX_API_PASSWORD: str = _env("SPARK_MAX_API_PASSWORD", "")
SPARK_MAX_API_BASE: str = _env("SPARK_MAX_API_BASE", "https://spark-api-open.xf-yun.com/v1")

# Spark (别名，使用 Spark Max 配置)
SPARK_API_PASSWORD: str = SPARK_MAX_API_PASSWORD
SPARK_API_BASE: str = SPARK_MAX_API_BASE
