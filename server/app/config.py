"""配置加载。

只负责读取 config.yaml，不负责业务逻辑。
"""

from pathlib import Path

import yaml

_CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"
_config: dict = {}


def _load() -> dict:
    """加载配置文件。"""
    if not _CONFIG_FILE.exists():
        return {}
    with open(_CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_config = _load()


def get(path: str, default=None):
    """获取配置值，支持嵌套路径。"""
    value = _config
    for key in path.split("."):
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


# ============ App ============
DEBUG = get("app.debug", False)
HOST = get("app.host", "0.0.0.0")
PORT = get("app.port", 9999)

# ============ Database ============
DB_URL = get("database.url", "")
DB_ECHO = get("database.echo", False)
DB_POOL_SIZE = get("database.pool_size", 10)
DB_MAX_OVERFLOW = get("database.max_overflow", 20)
DB_POOL_RECYCLE = get("database.pool_recycle", 1800)
DB_POOL_TIMEOUT = get("database.pool_timeout", 30)

# ============ JWT ============
JWT_SECRET = get("jwt.secret_key", "")
JWT_ALGO = get("jwt.algorithm", "HS256")
JWT_EXPIRE = get("jwt.expire_days", 7)

# ============ Paths ============
WORKPLACE_DIR_NAME = get("paths.workplace", "workplace")
LOGS_DIR_NAME = get("paths.logs", "logs")
KB_DIR_NAME = get("paths.knowledge", "data")

# ============ Path objects ============
SERVER_DIR = Path(__file__).resolve().parents[1]
WORKPLACE_DIR = SERVER_DIR / WORKPLACE_DIR_NAME
LOGS_DIR = SERVER_DIR / LOGS_DIR_NAME
KNOWLEDGE_BASE_DIR = SERVER_DIR / KB_DIR_NAME
# Backward-compatible alias for older knowledge modules.
KB_DIR = KNOWLEDGE_BASE_DIR
CHAT_DIR = WORKPLACE_DIR / "chat"
AVATAR_DIR = WORKPLACE_DIR / "avatars"

# ============ Knowledge Base ============
KB_ENABLED = get("knowledge.enabled", True)
KB_COLLECTION = get("knowledge.collection", "md_books")
KB_EMBED_MODEL = get("knowledge.embed_model", "bge-m3:latest")
KB_TOP_K = get("knowledge.top_k", 4)
KB_OLLAMA_BASE_URL = get("knowledge.ollama_base_url", "http://127.0.0.1:11434")

# ============ Logging ============
LOG_LEVEL = get("logging.level", "INFO")
LANGCHAIN_DEBUG = False
LANGCHAIN_VERBOSE = False
LANGGRAPH_DEBUG = False
DEEPAGENTS_DEBUG = False

# ============ Search ============
TAVILY_KEY = get("search.tavily_key", "")
SERPAPI_KEY = ""
SPARK_SEARCH_KEY = get("search.spark_key", "")

# ============ Avatar ============
AVATAR_APP_ID = get("avatar.app_id", "")
AVATAR_API_KEY = get("avatar.api_key", "")
AVATAR_API_SECRET = get("avatar.api_secret", "")
AVATAR_URL = get("avatar.url", "")
AVATAR_ANCHOR = get("avatar.anchor_id", "")
AVATAR_VCN = get("avatar.vcn", "")
AVATAR_IAT_URL = get("avatar.iat_url", "")
ASR_APP_ID = get("avatar.asr_app_id", "")
ASR_API_KEY = get("avatar.asr_api_key", "")
ASR_API_SECRET = get("avatar.asr_api_secret", "")

# ============ Spark WebSocket ============
SPARK_APP_ID = get("spark.app_id", "")
SPARK_API_KEY = get("spark.api_key", "")
SPARK_API_SECRET = get("spark.api_secret", "")

# ============ Chat 附件与保护机制 ============
MAX_FILE_CONTENT_CHARS = get("chat.max_file_content_chars", 15000)
MAX_ANALYZE_FILE_COUNT = get("chat.max_analyze_file_count", 8)
MAX_ANALYZE_TOTAL_CHARS = get("chat.max_analyze_total_chars", 40000)
MAX_PDF_PAGES_TO_READ = get("chat.max_pdf_pages", 80)
MAX_DOCX_PARAGRAPHS_TO_READ = get("chat.max_docx_paragraphs", 1200)
MAX_IMAGE_ANALYZE_COUNT = get("chat.max_analyze_images", 8)
MAX_UPLOAD_FILES_PER_REQUEST = get("chat.max_upload_files", 12)

