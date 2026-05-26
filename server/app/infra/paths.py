"""全局路径常量。"""
from pathlib import Path

from app.config import KB_DIR as KB_DIR_NAME
from app.config import LOGS_DIR as LOG_DIR_NAME
from app.config import WORKPLACE_DIR as WORK_DIR_NAME

SERVER_DIR = Path(__file__).resolve().parents[2]
WORKPLACE_DIR = SERVER_DIR / WORK_DIR_NAME
LOGS_DIR = SERVER_DIR / LOG_DIR_NAME
KNOWLEDGE_BASE_DIR = SERVER_DIR / KB_DIR_NAME
RESOURCE_DIR = WORKPLACE_DIR / "resource"  # 资源文件统一存放目录
CHAT_DIR = WORKPLACE_DIR / "chat"  # 聊天文件统一存放目录
AVATAR_DIR = WORKPLACE_DIR / "avatars"  # 用户头像存放目录
