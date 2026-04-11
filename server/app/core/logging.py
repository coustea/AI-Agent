"""
集中日志配置模块。

使用方式：
    from app.core.logging import get_logger
    logger = get_logger(__name__)
"""

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

from app.utils.paths import LOGS_DIR as LOG_DIR

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """获取子 logger，各模块通过 get_logger(__name__) 使用。"""
    return logging.getLogger(name)


def setup_logging() -> None:
    """
    配置 root logger，同时输出到文件和控制台。
    在应用启动时调用一次。
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # 防止热重载时重复添加 handler
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 全量日志：按天轮转，保留 30 天
    timed_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    timed_handler.suffix = "%Y-%m-%d"
    timed_handler.setLevel(logging.INFO)
    timed_handler.setFormatter(formatter)

    # 错误日志：按大小轮转，10MB 一个文件，保留 10 份
    error_handler = RotatingFileHandler(
        filename=LOG_DIR / "error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(timed_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
