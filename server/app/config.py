"""配置加载模块。

只负责读取 config.yaml 文件，提供嵌套路径访问接口。
不包含任何业务逻辑，所有配置项在模块加载时一次性读取并缓存。
"""

import json
from pathlib import Path

import yaml

# 配置文件路径：server/config.yaml
_CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"
# 配置缓存字典，模块加载时填充
_config: dict = {}


def _load() -> dict:
    """加载配置文件。

    读取 config.yaml 并解析为字典。
    如果文件不存在则返回空字典，避免启动时报错。
    """
    if not _CONFIG_FILE.exists():
        return {}
    # 以 UTF-8 编码读取 YAML 文件，safe_load 防止执行任意 Python 对象
    with open(_CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# 模块加载时立即读取配置
_config = _load()


def _load_knowledge_routes() -> dict:
    routes_file = Path(__file__).resolve().parent / "rag" / "config" / "knowledge_routes.json"
    if not routes_file.exists():
        return {}
    with open(routes_file, encoding="utf-8") as f:
        return json.load(f) or {}


def get(path: str, default=None):
    """获取配置值，支持点号分隔的嵌套路径。

    示例：get("database.url") 等价于 _config["database"]["url"]

    Args:
        path: 用点号分隔的配置路径，如 "app.debug"
        default: 路径不存在时的默认返回值

    Returns:
        配置值或默认值
    """
    value = _config
    # 按点号分割路径，逐层查找
    for key in path.split("."):
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


# ============ 应用配置 ============
# 调试模式开关
DEBUG = get("app.debug", False)
# 监听主机地址
HOST = get("app.host", "0.0.0.0")
# 监听端口号
PORT = get("app.port", 9999)

# ============ 数据库配置 ============
# 数据库连接 URL（如 postgresql://user:pass@host/db）
DB_URL = get("database.url", "")
# 是否打印 SQL 语句（调试用）
DB_ECHO = get("database.echo", False)
# 连接池大小：同时保持的最大连接数
DB_POOL_SIZE = get("database.pool_size", 10)
# 连接池溢出上限：超出 pool_size 后最多额外创建的连接数
DB_MAX_OVERFLOW = get("database.max_overflow", 20)
# 连接池回收时间（秒）：超过此时间的空闲连接会被关闭并重建
DB_POOL_RECYCLE = get("database.pool_recycle", 1800)
# 从连接池获取连接的超时时间（秒）
DB_POOL_TIMEOUT = get("database.pool_timeout", 30)

# ============ JWT 认证配置 ============
# JWT 签名密钥（必须保密）
JWT_SECRET = get("jwt.secret_key", "")
# JWT 签名算法
JWT_ALGO = get("jwt.algorithm", "HS256")
# JWT 过期天数
JWT_EXPIRE = get("jwt.expire_days", 7)

# ============ 路径配置 ============
# 工作目录名称（存储用户工作数据）
WORKPLACE_DIR_NAME = get("paths.workplace", "workplace")
# 日志目录名称
LOGS_DIR_NAME = get("paths.logs", "logs")
# 知识库数据目录名称
KB_DIR_NAME = get("paths.knowledge", "data")

# ============ 路径对象 ============
# 项目根目录：server/
SERVER_DIR = Path(__file__).resolve().parents[1]
# 工作数据目录：server/workplace/
WORKPLACE_DIR = SERVER_DIR / WORKPLACE_DIR_NAME
# 日志输出目录：server/logs/
LOGS_DIR = SERVER_DIR / LOGS_DIR_NAME
# 知识库目录：server/data/
KNOWLEDGE_BASE_DIR = SERVER_DIR / KB_DIR_NAME
# 向后兼容别名（旧模块引用 KB_DIR）
KB_DIR = KNOWLEDGE_BASE_DIR
# 聊天记录目录：server/workplace/chat/
CHAT_DIR = WORKPLACE_DIR / "chat"
# 数字人头像数据目录：server/workplace/avatars/
AVATAR_DIR = WORKPLACE_DIR / "avatars"

# ============ 知识库配置 ============
# 是否启用知识库功能
KB_ENABLED = get("knowledge.enabled", True)
# 知识库集合名称（向量数据库中的 collection 名）
KB_COLLECTION = get("knowledge.collection", "md_books")
# 嵌入模型名称（用于生成文本向量）
KB_EMBED_MODEL = get("knowledge.embed_model", "bge-m3:latest")
# 检索时返回的最相似文档数量
KB_TOP_K = get("knowledge.top_k", 4)
# Ollama 本地模型服务地址
KB_OLLAMA_BASE_URL = get("knowledge.ollama_base_url", "http://127.0.0.1:11434")

# ============ 知识库路由配置 ============
_knowledge_routes = _load_knowledge_routes()
KB_COURSE_ROUTING: dict = _knowledge_routes.get("course_routing", {})
KB_COURSE_LINKAGE: dict = _knowledge_routes.get("course_linkage", {})
KB_ROUTING_LLM_MODEL: str = get("knowledge.routing.llm_model", "qwen2.5:1.5b")
KB_ROUTING_LLM_CONFIDENCE: float = get("knowledge.routing.llm_confidence_threshold", 0.6)
KB_ROUTING_KEYWORD_THRESHOLD: float = get("knowledge.routing.keyword_score_threshold", 3.0)

# ============ 知识库查询改写配置 ============
KB_REWRITE_ENABLED: bool = get("knowledge.rewrite.enabled", True)
KB_REWRITE_LLM_MODEL: str = get("knowledge.rewrite.llm_model", "qwen2.5:1.5b")
KB_REWRITE_MAX_VARIANTS: int = get("knowledge.rewrite.max_variants", 3)
KB_REWRITE_SIMILARITY_THRESHOLD: float = get("knowledge.rewrite.similarity_threshold", 0.6)
KB_REWRITE_CONFIDENCE_THRESHOLD: float = get("knowledge.rewrite.confidence_threshold", 1.4)
KB_REWRITE_BUDGET_MS: int = get("knowledge.rewrite.budget_ms", 800)
KB_REWRITE_EFFECTIVENESS_CACHE_SIZE: int = get("knowledge.rewrite.effectiveness_cache_size", 200)

# ============ 知识库检索配置 ============
KB_RRF_K: int = get("knowledge.retrieval.rrf_k", 60)
KB_SNIPPET_MIN: int = get("knowledge.retrieval.snippet_min", 500)
KB_SNIPPET_MAX: int = get("knowledge.retrieval.snippet_max", 900)

# ============ 日志配置 ============
# 日志级别（DEBUG / INFO / WARNING / ERROR）
LOG_LEVEL = get("logging.level", "INFO")
# LangChain 调试开关
LANGCHAIN_DEBUG = False
# LangChain 详细输出开关
LANGCHAIN_VERBOSE = False
# LangGraph 调试开关
LANGGRAPH_DEBUG = False
# DeepAgents 调试开关
DEEPAGENTS_DEBUG = False

# ============ 搜索引擎 API 密钥 ============
# Tavily 搜索 API 密钥
TAVILY_KEY = get("search.tavily_key", "")
# 讯飞星火搜索 API 密钥
SPARK_SEARCH_KEY = get("search.spark_key", "")

# ============ 数字人（Avatar）配置 ============
# 讯飞数字人应用 ID
AVATAR_APP_ID = get("avatar.app_id", "")
# 讯飞数字人 API 密钥
AVATAR_API_KEY = get("avatar.api_key", "")
# 讯飞数字人 API 密钥签名
AVATAR_API_SECRET = get("avatar.api_secret", "")
# 数字人 WebSocket 服务地址
AVATAR_URL = get("avatar.url", "")
# 数字人锚点 ID（用于定位数字人形象）
AVATAR_ANCHOR = get("avatar.anchor_id", "")
# 虚拟通道号（Virtual Channel Number）
AVATAR_VCN = get("avatar.vcn", "")
# 图片转动画（IAT）服务地址
AVATAR_IAT_URL = get("avatar.iat_url", "")
# 语音识别（ASR）应用 ID
ASR_APP_ID = get("avatar.asr_app_id", "")
# 语音识别 API 密钥
ASR_API_KEY = get("avatar.asr_api_key", "")
# 语音识别 API 密钥签名
ASR_API_SECRET = get("avatar.asr_api_secret", "")

# ============ 星火 Spark WebSocket 配置 ============
# 星火大模型应用 ID
SPARK_APP_ID = get("spark.app_id", "")
# 星火大模型 API 密钥
SPARK_API_KEY = get("spark.api_key", "")
# 星火大模型 API 密钥签名
SPARK_API_SECRET = get("spark.api_secret", "")

# 星火 TTS 配置（回退到通用 Spark 配置）
SPARK_TTS_APP_ID = get("spark_tts.app_id", SPARK_APP_ID)
SPARK_TTS_API_KEY = get("spark_tts.api_key", SPARK_API_KEY)
SPARK_TTS_API_SECRET = get("spark_tts.api_secret", SPARK_API_SECRET)

# ============ 聊天附件与保护机制 ============
# 单个文件内容最大读取字符数（防止超大文件撑爆上下文）
MAX_FILE_CONTENT_CHARS = get("chat.max_file_content_chars", 15000)
# 单次分析的最大文件数量
MAX_ANALYZE_FILE_COUNT = get("chat.max_analyze_file_count", 8)
# 单次分析的所有文件内容总字符数上限
MAX_ANALYZE_TOTAL_CHARS = get("chat.max_analyze_total_chars", 40000)
# PDF 文件最大读取页数
MAX_PDF_PAGES_TO_READ = get("chat.max_pdf_pages", 80)
# DOCX 文件最大读取段落数
MAX_DOCX_PARAGRAPHS_TO_READ = get("chat.max_docx_paragraphs", 1200)
# 单次分析的最大图片数量
MAX_IMAGE_ANALYZE_COUNT = get("chat.max_analyze_images", 8)
# 单次请求最大上传文件数
MAX_UPLOAD_FILES_PER_REQUEST = get("chat.max_upload_files", 12)

# ============ 记忆压缩与长期记忆 ============
# 保留最近多少条原始消息（不压缩）
RECENT_RAW_MESSAGES = get("memory.recent_raw_messages", 8)
# 压缩后保留的最近原始消息条数
COMPRESS_KEEP_RECENT_MESSAGES = get("memory.compress_keep_recent_messages", 4)
# 触发压缩的最少消息数
COMPRESS_MIN_MESSAGES = get("memory.compress_min_messages", 14)
# 触发压缩的最少 Token 数
COMPRESS_MIN_TOKENS = get("memory.compress_min_tokens", 3500)
# 压缩摘要时保留的上下文块数
SUMMARY_CONTEXT_BLOCKS = get("memory.summary_context_blocks", 3)
# 写入长期记忆的最少消息数
LTM_MIN_MESSAGES = get("memory.ltm_min_messages", 12)
# 写入长期记忆的最少 Token 数
LTM_MIN_TOKENS = get("memory.ltm_min_tokens", 3500)
# 写入长期记忆的最低置信度阈值
LTM_MIN_CONFIDENCE = get("memory.ltm_min_confidence", 0.75)
# 长期记忆写入冷却时间（分钟），避免频繁写入
LTM_COOLDOWN_MINUTES = get("memory.ltm_cooldown_minutes", 30)

# ============ 模型推理参数 ============
# 通用模型温度参数（控制输出随机性，0=确定性，1=高随机性）
INFERENCE_TEMPERATURE = get("models.temperature", 0.3)
# 结构化输出策略：json_schema_first / json_mode_first / prompt_first
# json_schema_first — 优先 json_schema strict，失败后降级 json_mode → prompt
# json_mode_first — 跳过 json_schema，直接 json_mode，失败后降级 prompt
# prompt_first — 仅 prompt 注入 + 手动解析
STRUCTURED_OUTPUT_STRATEGY = get("models.structured_output_strategy", "json_schema_first")
# 视觉模型温度参数（通常需要更高的创造性）
VISION_TEMPERATURE = get("models.vision.temperature", 0.7)

# ============ Chat 扩展配置 ============
# 支持的图片扩展名集合
IMAGE_EXTENSIONS: set[str] = set(get("chat.image_extensions", ["png", "jpg", "jpeg", "gif", "webp"]))
# 构建对话上下文时拉取的历史消息条数
CHAT_HISTORY_LIMIT: int = get("chat.history_limit", 20)
# 查询 embedding 缓存大小
KB_QUERY_EMBEDDING_CACHE_SIZE: int = get("chat.query_embedding_cache_size", 500)
# 稀疏检索加载的文档上限
KB_SPARSE_CORPUS_LIMIT: int = get("chat.sparse_corpus_limit", 12000)

# ============ 安全过滤配置 ============
SAFETY_SENSITIVE_TERMS: tuple[str, ...] = tuple(get("safety.sensitive_terms", ["色情", "赌博", "毒品", "暴力"]))

# ============ 评估配置 ============
# 连续学习天数判定阈值（秒），每天至少这么多秒才算活跃
STREAK_MIN_SECONDS: int = get("evaluation.streak_min_seconds", 300)

# ============ 路径规划配置 ============
# 节点估计时长下限（分钟）
PATH_MIN_ESTIMATED_MINUTES: int = get("paths_config.min_estimated_minutes", 10)
# 节点估计时长上限（分钟）
PATH_MAX_ESTIMATED_MINUTES: int = get("paths_config.max_estimated_minutes", 180)
# 路径节点测验题目数量
PATH_QUIZ_SIZE: int = get("paths_config.quiz_size", 5)
# 通过测验的最低分数
PATH_PASS_SCORE: int = get("paths_config.pass_score", 3)

# ============ 资源生成配置 ============
# 审核时单个资源内容截断上限（字符数）
REVIEW_CONTENT_LIMIT: int = get("resource.review_content_limit", 12000)

# ============ 题库导入配置 ============
# 批量写入的批次大小
QUIZ_IMPORT_BATCH_SIZE: int = get("quiz.import_batch_size", 200)

# ============ ASR 配置 ============
# VAD 结束静默时长（毫秒）
ASR_VAD_EOS: int = get("asr.vad_eos", 1000)
