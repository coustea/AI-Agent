"""
集中日志配置模块。

使用方式：
    from app.infra.logging import get_logger
    logger = get_logger(__name__)

配置三个输出通道：
  1. 全量日志文件（app.log）— 按天轮转，保留 30 天
  2. 错误日志文件（error.log）— 按大小轮转，10MB/份，保留 10 份
  3. 控制台输出 — 开发调试用
"""

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

from app.shared.paths import LOGS_DIR as LOG_DIR

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"  # 统一日志格式
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """获取子 logger，各模块通过 get_logger(__name__) 使用。
    返回的是 Python 标准 logging.Logger，日志级别和 handler 由 root logger 统一控制。"""
    return logging.getLogger(name)


def setup_logging() -> None:
    """
    配置 root logger，同时输出到文件和控制台。
    在应用启动时由 lifespan 调用一次。

    注意：每次调用会先清空已有 handler，防止 FastAPI 热重载时重复添加导致日志重复输出。
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # 全局最低级别 INFO
    # 防止热重载时重复添加 handler
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 通道 1：全量日志 — 按天轮转（每天一个文件），保留最近 30 天
    timed_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "app.log",
        when="midnight",  # 每天午夜轮转
        interval=1,
        backupCount=30,  # 保留 30 天
        encoding="utf-8",
    )
    timed_handler.suffix = "%Y-%m-%d"  # 轮转后的文件名后缀格式
    timed_handler.setLevel(logging.INFO)
    timed_handler.setFormatter(formatter)

    # 通道 2：错误日志 — 按大小轮转，10MB 一个文件，保留 10 份
    error_handler = RotatingFileHandler(
        filename=LOG_DIR / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,  # 最多保留 10 个备份文件
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)  # 只记录 ERROR 及以上级别
    error_handler.setFormatter(formatter)

    # 通道 3：控制台输出 — 开发调试时直接在终端查看日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(timed_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    root_logger.info("[Logging] 日志系统初始化完成: log_dir=%s", LOG_DIR)