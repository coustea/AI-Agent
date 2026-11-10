"""集中日志配置模块 —— 基于 Loguru 的全链路结构化系统日志。

本模块全面摒弃旧式 logging.Logger 与包装代理，提供纯正的 Loguru 日志驱动：
- 支持基于 ContextVar 的全链路 Trace ID 与用户上下文自动补齐（无需手动层层传参）；
- 提供控制台高亮彩色输出与针对第三方噪音的智能过滤；
- 提供 app.log（天级轮转、保留30天）与 error.log（按大小轮转、保留10份备份）双文件落盘；
- 拦截并清洗 Uvicorn / FastAPI / SQLAlchemy / HTTPX 等第三方库日志到同一管道。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
import logging
from pathlib import Path
import sys
from typing import Any, Optional

from loguru import logger as _loguru_logger
from loguru._logger import Logger

from app.config import LOGS_DIR as LOG_DIR

# 全链路追踪上下文变量（协程隔离与任务继承）
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")
user_ctx: ContextVar[str] = ContextVar("user", default="-")

# 控制台格式（带有层级色彩与追踪高亮）
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>[{extra[trace_id]}]</cyan> "
    "<magenta>[{extra[user]}]</magenta> "
    "<blue>{name}:{function}:{line}</blue> - "
    "<level>{message}</level>"
)

# 文件落盘格式（去色彩纯文本，便于 grep 与自动化日志解析）
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level:<8} | "
    "[{extra[trace_id]}] "
    "[{extra[user]}] "
    "{name}:{function}:{line} - "
    "{message}"
)

# 终端过滤名单：屏蔽第三方高频低信噪比调试日志
_CONSOLE_NOISY_PREFIXES: tuple[str, ...] = (
    "httpcore",
    "httpx",
    "openai",
    "sqlalchemy",
    "sqlalchemy.engine",
    "aiomysql",
    "uvicorn.access",
)


def get_trace_id() -> str:
    """获取当前协程上下文绑定的 Trace ID。"""
    return trace_id_ctx.get()


def get_current_user_name() -> str:
    """获取当前协程上下文绑定的操作用户标识。"""
    return user_ctx.get()


def set_trace_context(
    trace_id: str | None = None,
    user: str | None = None,
) -> tuple[Token[str] | None, Token[str] | None]:
    """设置当前协程的链路追踪与用户上下文，并返回回滚 Token。"""
    token_trace = trace_id_ctx.set(trace_id) if trace_id is not None else None
    token_user = user_ctx.set(user) if user is not None else None
    return (token_trace, token_user)


def reset_trace_context(tokens: tuple[Token[str] | None, Token[str] | None]) -> None:
    """恢复先前保存的链路上下文 Token。"""
    token_trace, token_user = tokens
    if token_trace is not None:
        trace_id_ctx.reset(token_trace)
    if token_user is not None:
        user_ctx.reset(token_user)


@contextmanager
def trace_scope(trace_id: str | None = None, user: str | None = None) -> Iterator[None]:
    """链路追踪作用域上下文管理器，离开作用域自动恢复上下文。"""
    tokens = set_trace_context(trace_id=trace_id, user=user)
    try:
        yield
    finally:
        reset_trace_context(tokens)


def _context_patcher(record: dict[str, Any]) -> None:
    """为 Loguru 记录动态补齐链路上下文（Trace ID、用户、记录源组件名）。"""
    extra = record["extra"]
    if "trace_id" not in extra or extra["trace_id"] == "-":
        extra["trace_id"] = trace_id_ctx.get()
    if "user" not in extra or extra["user"] == "-":
        extra["user"] = user_ctx.get()
    if "logger_name" not in extra:
        extra["logger_name"] = record["name"]


def _console_filter(record: dict[str, Any]) -> bool:
    """控制台日志过滤器：对第三方库噪音仅在 WARNING+ 级别放行，业务日志正常放行。"""
    name = str(record["extra"].get("logger_name") or record["name"] or "")
    level_no = record["level"].no

    # 如果是已知的第三方噪音库
    for prefix in _CONSOLE_NOISY_PREFIXES:
        if name.startswith(prefix) or name == prefix:
            # 仅放行 WARNING 及以上级别
            return level_no >= 30

    return True


class _InterceptHandler(logging.Handler):
    """将标准 logging.Record 拦截并路由至统一 Loguru 管道。"""

    def emit(self, record: logging.LogRecord) -> None:
        """接收标准库日志记录，解析原始调用栈并投递至 Loguru。"""
        try:
            level = _loguru_logger.level(record.levelname).name
        except (ValueError, TypeError):
            level = record.levelno

        # 动态回溯找到非 logging 模块的真实调用帧
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _loguru_logger.bind(logger_name=record.name).opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, record.getMessage())


def get_logger(name: str | None = None) -> Logger:
    """获取项目统一的 Loguru Logger，支持按模块名称绑定。"""
    if name:
        return _loguru_logger.bind(logger_name=name)
    return _loguru_logger


# 全局默认 Loguru 实例供直接引入使用
logger: Logger = _loguru_logger


_CONFIGURED = False


def setup_logging(*, level: Optional[str] = None, force: bool = False) -> None:
    """初始化 Loguru 日志系统与标准库拦截器。"""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    target_level = level or "INFO"

    # 1. 配置全局 patcher 动态富化上下文
    _loguru_logger.remove()
    _loguru_logger.configure(patcher=_context_patcher)

    # 2. 控制台输出 Sink：高亮色彩、带链路追踪、智能噪音过滤
    _loguru_logger.add(
        sys.stderr,
        level=target_level,
        format=_CONSOLE_FORMAT,
        filter=_console_filter,
        colorize=True,
        backtrace=True,
        diagnose=False,
        enqueue=False,
    )

    # 3. 业务全量日志文件 Sink (app.log)：天级轮转、保留30天
    _loguru_logger.add(
        str(log_dir / "app.log"),
        level=target_level,
        format=_FILE_FORMAT,
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=False,
    )

    # 4. 错误排障日志文件 Sink (error.log)：ERROR 及以上、按10MB轮转、保留10份
    _loguru_logger.add(
        str(log_dir / "error.log"),
        level="ERROR",
        format=_FILE_FORMAT,
        rotation="10 MB",
        retention=10,
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=False,
    )

    # 5. 接管 Python 标准库 logging 根处理器
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # 清除常见第三方库默认的 handlers 避免双重打印
    for noisy_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy",
        "sqlalchemy.engine",
        "aiomysql",
    ):
        ext_logger = logging.getLogger(noisy_name)
        ext_logger.handlers.clear()
        ext_logger.propagate = True

    _loguru_logger.info(
        "[Logging] 全链路 Loguru 日志初始化完成: level={} console=彩色高亮 app.log=按天轮转 error.log=10MB轮转",
        target_level,
    )
    _CONFIGURED = True


def configure_logging() -> None:
    """系统启动时的统一日志配置入口函数。"""
    setup_logging(level="INFO", force=True)
