"""配置加载模块。

只负责读取 config.yaml 文件，提供嵌套路径访问接口。
不包含任何业务逻辑，所有配置项在模块加载时一次性读取并缓存。
"""

# 本模块负责加载并暴露全局配置：从 config.yaml 读取，提供嵌套取值与路径/URL 工具函数
from pathlib import Path

import yaml

# 配置文件路径：server/config.yaml
_CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"
# 配置缓存字典，模块加载时填充
_config: dict = {}


# 加载并解析 YAML 配置文件
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


# 按点号分隔的嵌套路径获取配置值，路径不存在时返回默认值
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
# 服务监听地址
HOST = get("app.host", "127.0.0.1")
# 服务监听端口
PORT = get("app.port", 9999)


# ============ 数据库配置 ============
# 数据库连接 URL（如 mysql+aiomysql://user:pass@host:3306/db）
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

# ============ 路径对象 ============
# 项目根目录：server/
SERVER_DIR = Path(__file__).resolve().parents[1]
# 工作数据目录：server/static/（静态文件根目录）
WORKPLACE_DIR = SERVER_DIR / get("paths.workplace", "workplace")
# 日志输出目录：server/logs/
LOGS_DIR = SERVER_DIR / get("paths.logs", "logs")


# ============ 用户路径构建函数 ============
# 获取用户静态文件根目录：static/{username}/
def user_dir(username: str) -> Path:
    """获取用户静态文件根目录。

    Args:
        username: 用户名（数据库约束 unique=True）

    Returns:
        Path: static/{username}/
    """
    return WORKPLACE_DIR / username


# 获取用户头像目录
def user_avatar_dir(username: str) -> Path:
    """获取用户头像目录：static/{username}/avatar/"""
    return user_dir(username) / "avatar"


# 获取用户聊天会话目录
def user_chat_dir(username: str, session_id: str) -> Path:
    """获取用户聊天会话目录：static/{username}/chat/{session_id}/"""
    return user_dir(username) / "chat" / session_id


# 获取用户聊天附件目录
def user_chat_uploads_dir(username: str, session_id: str) -> Path:
    """获取用户聊天附件目录：static/{username}/chat/{session_id}/uploads/"""
    return user_chat_dir(username, session_id) / "uploads"


# 获取用户资源目录
def user_resources_dir(username: str) -> Path:
    """获取用户资源目录：static/{username}/resources/"""
    return user_dir(username) / "resources"


# 获取单个资源目录
def user_resource_dir(username: str, resource_id: str) -> Path:
    """获取单个资源目录：static/{username}/resources/{resource_id}/"""
    return user_resources_dir(username) / str(resource_id)


# 获取资源 PPT 目录
def user_resource_ppt_dir(username: str, resource_id: str) -> Path:
    """获取资源 PPT 目录：static/{username}/resources/{resource_id}/ppt/"""
    return user_resource_dir(username, resource_id) / "ppt"


# 获取路径节点 PPT 目录
def user_paths_dir(username: str) -> Path:
    """获取用户学习路径目录：static/{username}/paths/"""
    return user_dir(username) / "paths"


# 获取单个学习路径目录
def user_path_dir(username: str, path_id: str) -> Path:
    """获取单个学习路径目录：static/{username}/paths/{path_id}/"""
    return user_paths_dir(username) / str(path_id)


# 获取路径节点目录
def user_path_node_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点目录：static/{username}/paths/{path_id}/nodes/{node_id}/"""
    return user_path_dir(username, path_id) / "nodes" / str(node_id)


# 获取路径节点 PPT 目录
def user_path_node_ppt_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点 PPT 目录：static/{username}/paths/{path_id}/nodes/{node_id}/ppt/"""
    return user_path_node_dir(username, path_id, node_id) / "ppt"


# 获取路径节点动画目录
def user_resource_cartoon_dir(username: str, resource_id: str) -> Path:
    """获取资源动画目录：static/{username}/resources/{resource_id}/cartoon/"""
    return user_resource_dir(username, resource_id) / "cartoon"


# 获取路径节点动画目录
def user_path_node_cartoon_dir(username: str, path_id: str, node_id: str) -> Path:
    """获取路径节点动画目录：static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/"""
    return user_path_node_dir(username, path_id, node_id) / "cartoon"


# ============ URL 构建函数 ============
# 将本地路径转换为 /static/ 开头的静态文件 URL
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


# 构建用户头像 URL
def avatar_url(username: str, ext: str) -> str:
    """构建头像 URL：/static/{username}/avatar/avatar.{ext}"""
    return f"/static/{username}/avatar/avatar.{ext}"


# 构建聊天附件 URL
def chat_upload_url(username: str, session_id: str, filename: str) -> str:
    """构建聊天附件 URL：/static/{username}/chat/{session_id}/uploads/{filename}"""
    return f"/static/{username}/chat/{session_id}/uploads/{filename}"


# ============ 聊天附件与保护机制 ============
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

# ============ Chat 扩展配置 ============
# 构建对话上下文时拉取的历史消息条数
CHAT_HISTORY_LIMIT: int = get("chat.history_limit", 20)

# ============ 路径规划配置 ============
# 路径节点测验题目数量
PATH_QUIZ_SIZE: int = get("paths_config.quiz_size", 5)
# 通过测验的最低分数
PATH_PASS_SCORE: int = get("paths_config.pass_score", 3)



