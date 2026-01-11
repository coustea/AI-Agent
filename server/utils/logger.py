import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "server.log")

def setup_logging():
    """配置根日志记录器，将日志输出到控制台和文件。"""
    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 日志格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # 文件处理器（滚动日志）
    # 单个文件最大 10MB，最多保留 5 个备份文件
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # 防止 uvicorn 在已有处理器时重复记录日志
    # 但通常我们也希望捕获 uvicorn 的日志
    # Uvicorn 会配置自己的日志记录器。我们可以传播或捕获它们
    # 为简单起见，确保我们的根日志记录器捕获所有日志

    logging.info("日志设置完成，日志写入至 %s", LOG_FILE_PATH)

def get_logger(name: str):
    """返回指定名称的日志记录器实例。

    Args:
        name: 日志记录器名称。

    Returns:
        logging.Logger: 日志记录器实例。
    """
    return logging.getLogger(name)
