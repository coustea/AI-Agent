"""配置加载模块。

只负责读取 config.yaml 文件，提供嵌套路径访问接口。
不包含任何业务逻辑，所有配置项在模块加载时一次性读取并缓存。
"""

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


# ============ 数据库配置 ============
# 数据库连接 URL（如 postgresql://user:pass@host/db）
DB_URL = get("database.url", "")
# 是否打印 SQL 语句（调试用）
DB_ECHO = get("database.echo", False)
# 连接池大小：同时保持的最大连接数
DB_POOL_SIZE = get("database.pool_size", 20)
# 连接池溢出上限：超出 pool_size 后最多额外创建的连接数
DB_MAX_OVERFLOW = get("database.max_overflow", 30)
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
# 工作数据目录：server/static/（静态文件根目录）
WORKPLACE_DIR = SERVER_DIR / WORKPLACE_DIR_NAME
# 日志输出目录：server/logs/
LOGS_DIR = SERVER_DIR / LOGS_DIR_NAME
# 知识库目录：server/data/（KB_DIR 是别名，供其他模块引用）
KNOWLEDGE_BASE_DIR = SERVER_DIR / KB_DIR_NAME
KB_DIR = KNOWLEDGE_BASE_DIR


# ============ 用户路径构建函数 ============
def user_dir(username: str) -> Path:
    """获取用户静态文件根目录。

    Args:
        username: 用户名（数据库约束 unique=True）

    Returns:
        Path: static/{username}/
    """
    return WORKPLACE_DIR / username


def user_avatar_dir(username: str) -> Path:
    """获取用户头像目录：static/{username}/avatar/"""
    return user_dir(username) / "avatar"


def user_chat_dir(username: str, session_id: str) -> Path:
    """获取用户聊天会话目录：static/{username}/chat/{session_id}/"""
    return user_dir(username) / "chat" / session_id


def user_chat_uploads_dir(username: str, session_id: str) -> Path:
    """获取用户聊天附件目录：static/{username}/chat/{session_id}/uploads/"""
    return user_chat_dir(username, session_id) / "uploads"


def user_chat_videos_dir(username: str, session_id: str, message_id: str) -> Path:
    """获取用户聊天视频目录：static/{username}/chat/{session_id}/videos/{message_id}/"""
    return user_chat_dir(username, session_id) / "videos" / message_id


def user_resources_dir(username: str) -> Path:
    """获取用户资源目录：static/{username}/resources/"""
    return user_dir(username) / "resources"


def user_resource_dir(username: str, resource_id: str) -> Path:
    """获取单个资源目录：static/{username}/resources/{resource_id}/"""
    return user_resources_dir(username) / str(resource_id)


def user_resource_ppt_dir(username: str, resource_id: str) -> Path:
    """获取资源 PPT 目录：static/{username}/resources/{resource_id}/ppt/"""
    return user_resource_dir(username, resource_id) / "ppt"


def user_resource_video_dir(username: str, resource_id: str) -> Path:
    """获取资源视频目录：static/{username}/resources/{resource_id}/video/"""
    return user_resource_dir(username, resource_id) / "video"


def user_paths_dir(username: str) -> Path:
    """获取用户学习路径目录：static/{username}/paths/"""
    return user_dir(username) / "paths"


def user_path_dir(username: str, path_id: str) -> Path:
    """获取单个学习路径目录：static/{username}/paths/{path_id}/"""
    return user_paths_dir(username) / str(path_id)


def user_path_node_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点目录：static/{username}/paths/{path_id}/nodes/{node_id}/"""
    return user_path_dir(username, path_id) / "nodes" / str(node_id)


def user_path_node_ppt_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点 PPT 目录：static/{username}/paths/{path_id}/nodes/{node_id}/ppt/"""
    return user_path_node_dir(username, path_id, node_id) / "ppt"


def user_path_node_video_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点视频目录：static/{username}/paths/{path_id}/nodes/{node_id}/video/"""
    return user_path_node_dir(username, path_id, node_id) / "video"


def user_resource_cartoon_dir(username: str, resource_id: str) -> Path:
    """获取资源动画目录：static/{username}/resources/{resource_id}/cartoon/"""
    return user_resource_dir(username, resource_id) / "cartoon"


def user_path_node_cartoon_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点动画目录：static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/"""
    return user_path_node_dir(username, path_id, node_id) / "cartoon"


# ============ URL 构建函数 ============
def static_url(path: Path) -> str:
    """将本地路径转换为静态文件 URL。

    Args:
        path: 相对于 WORKPLACE_DIR 的本地路径

    Returns:
        str: /static/{relative_path}
    """
    try:
        relative = path.relative_to(WORKPLACE_DIR)
        return f"/static/{relative.as_posix()}"
    except ValueError:
        # 路径不在 WORKPLACE_DIR 下，返回绝对路径
        return str(path)


def avatar_url(username: str, ext: str) -> str:
    """构建头像 URL：/static/{username}/avatar/avatar.{ext}"""
    return f"/static/{username}/avatar/avatar.{ext}"


def chat_upload_url(username: str, session_id: str, filename: str) -> str:
    """构建聊天附件 URL：/static/{username}/chat/{session_id}/uploads/{filename}"""
    return f"/static/{username}/chat/{session_id}/uploads/{filename}"



def chat_video_url(username: str, session_id: str, message_id: str) -> str:
    """构建聊天视频 URL：/static/{username}/chat/{session_id}/videos/{message_id}/video.mp4"""
    return f"/static/{username}/chat/{session_id}/videos/{message_id}/video.mp4"


def resource_ppt_url(username: str, resource_id: str) -> str:
    """构建资源 PPT URL：/static/{username}/resources/{resource_id}/ppt/slides.html"""
    return f"/static/{username}/resources/{resource_id}/ppt/slides.html"


def resource_video_url(username: str, resource_id: str) -> str:
    """构建资源视频 URL：/static/{username}/resources/{resource_id}/video/video.mp4"""
    return f"/static/{username}/resources/{resource_id}/video/video.mp4"


def path_node_ppt_url(username: str, path_id: str, node_id: str) -> str:
    """构建路径节点 PPT URL：/static/{username}/paths/{path_id}/nodes/{node_id}/ppt/slides.html"""
    return f"/static/{username}/paths/{path_id}/nodes/{node_id}/ppt/slides.html"


def path_node_video_url(username: str, path_id: str, node_id: str) -> str:
    """构建路径节点视频 URL：/static/{username}/paths/{path_id}/nodes/{node_id}/video/video.mp4"""
    return f"/static/{username}/paths/{path_id}/nodes/{node_id}/video/video.mp4"


def resource_cartoon_url(username: str, resource_id: str, filename: str = "index.html") -> str:
    """构建资源动画 URL：/static/{username}/resources/{resource_id}/cartoon/{filename}"""
    return f"/static/{username}/resources/{resource_id}/cartoon/{filename}"


def path_node_cartoon_url(username: str, path_id: str, node_id: str, filename: str = "index.html") -> str:
    """构建路径节点动画 URL：/static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/{filename}"""
    return f"/static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/{filename}"


# ============ 讲解视频渲染配置 ============
VIDEO_RENDER_TIMEOUT_SECONDS = get("video.render_timeout_seconds", 900)
VIDEO_RENDER_CONCURRENCY = get("video.concurrency", 4)
VIDEO_RENDER_CHROMIUM_GL = get("video.chromium_gl", "angle")

# ============ 知识库配置 ============
# 仅保留部署/调优参数；collection、切分、RRF 等实现细节下沉为 RAG 模块常量
# 是否启用知识库功能
KB_ENABLED = get("knowledge.enabled", True)
# 嵌入模型名（OpenAI 兼容 API）
KB_EMBED_MODEL = get("knowledge.embed_model", "bge-m3")
# 嵌入服务地址（llama.cpp /v1）
KB_EMBED_BASE_URL = get("knowledge.embed_base_url", "http://127.0.0.1:10000/v1")
# 检索时返回的最相似文档数量
KB_TOP_K = get("knowledge.top_k", 4)
# 返回给 ChatAgent 的最大上下文字符数
KB_MAX_CONTEXT_CHARS = get("knowledge.max_context_chars", 6000)
# 启动时索引不存在则自动构建
KB_AUTO_BUILD = get("knowledge.auto_build", True)

# ============ 日志配置 ============
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

# ASR 配置（回退到通用 Avatar 配置）
ASR_APP_ID = get("avatar.app_id", AVATAR_APP_ID)
ASR_API_KEY = get("avatar.api_key", AVATAR_API_KEY)
ASR_API_SECRET = get("avatar.api_secret", AVATAR_API_SECRET)

# ============ 星火 Spark WebSocket 配置 ============
# 星火大模型应用 ID
SPARK_APP_ID = get("spark.app_id", "")
# 星火大模型 API 密钥
SPARK_API_KEY = get("spark.api_key", "")
# 星火大模型 API 密钥签名
SPARK_API_SECRET = get("spark.api_secret", "")

# 星火 TTS 配置（回退到通用 Spark 配置）
SPARK_TTS_APP_ID = get("spark.app_id", SPARK_APP_ID)
SPARK_TTS_API_KEY = get("spark.api_key", SPARK_API_KEY)
SPARK_TTS_API_SECRET = get("spark.api_secret", SPARK_API_SECRET)

# ============ 聊天附件与保护机制 ============
# 单个文件内容最大读取字符数（防止超大文件撑爆上下文）
MAX_FILE_CONTENT_CHARS = get("chat.max_file_content_chars", 15000)
# 单次请求最大上传文件数
MAX_UPLOAD_FILES_PER_REQUEST = get("chat.max_upload_files", 12)

# ============ 记忆压缩与长期记忆 ============
# 压缩后保留的最近原始消息条数
COMPRESS_KEEP_RECENT_MESSAGES = get("memory.compress_keep_recent_messages", 4)
# 触发压缩的最少消息数
COMPRESS_MIN_MESSAGES = get("memory.compress_min_messages", 16)
# 触发压缩的最少 Token 数
COMPRESS_MIN_TOKENS = get("memory.compress_min_tokens", 4000)
# 压缩摘要时保留的上下文块数
SUMMARY_CONTEXT_BLOCKS = get("memory.summary_context_blocks", 3)
# 画像/长期记忆更新阈值（累积够了就触发）
UPDATE_MIN_MESSAGES = get("memory.update_min_messages", 12)
UPDATE_MIN_TOKENS = get("memory.update_min_tokens", 6000)
# 长期记忆最低置信度
LTM_MIN_CONFIDENCE = get("memory.ltm_min_confidence", 0.75)

# ============ 模型推理参数 ============
# JSON 结构化输出温度（低温度确保格式稳定，必须在 config.yaml 中配置 models.json_temp）
JSON_TEMPERATURE = get("models.json_temp")
assert JSON_TEMPERATURE is not None, "config.yaml 缺少 models.json_temp 配置"
# 流式对话输出温度（高温度增加创意性和自然感，必须在 config.yaml 中配置 models.stream_temp）
STREAM_TEMPERATURE = get("models.stream_temp")
assert STREAM_TEMPERATURE is not None, "config.yaml 缺少 models.stream_temp 配置"
# 普通文本生成温度（中等温度平衡确定性和多样性，必须在 config.yaml 中配置 models.default_temp）
DEFAULT_TEMPERATURE = get("models.default_temp")
assert DEFAULT_TEMPERATURE is not None, "config.yaml 缺少 models.default_temp 配置"
# 结构化输出策略：function_calling_first / json_mode_first / prompt_first
# function_calling_first — 优先 function_calling，失败后降级 json_mode → prompt
# json_mode_first — 跳过 function_calling，直接 json_mode，失败后降级 prompt
# prompt_first — 仅 prompt 注入 + 手动解析
STRUCTURED_OUTPUT_STRATEGY = get("models.structured_output_strategy", "function_calling_first")
# 视觉模型温度参数（必须在 config.yaml 中配置 models.vision.temperature）
VISION_TEMPERATURE = get("models.vision.temperature")
assert VISION_TEMPERATURE is not None, "config.yaml 缺少 models.vision.temperature 配置"

# ============ Chat 扩展配置 ============
# 支持的图片扩展名集合
IMAGE_EXTENSIONS: set[str] = set(get("chat.image_extensions", ["png", "jpg", "jpeg", "gif", "webp"]))
# 构建对话上下文时拉取的历史消息条数
CHAT_HISTORY_LIMIT: int = get("chat.history_limit", 20)

# ============ 评估配置 ============
# 连续学习天数判定阈值（秒），每天至少这么多秒才算活跃
STREAK_MIN_SECONDS: int = get("evaluation.streak_min_seconds", 300)

# ============ 路径规划配置 ============
# 路径节点测验题目数量
PATH_QUIZ_SIZE: int = get("paths_config.quiz_size", 5)
# 通过测验的最低分数
PATH_PASS_SCORE: int = get("paths_config.pass_score", 3)

# ============ ASR 配置 ============
# VAD 结束静默时长（毫秒）
ASR_VAD_EOS: int = get("asr.vad_eos", 1000)
