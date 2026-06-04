"""集中日志配置模块（Loguru 版本，异步写入）。

兼容性目标：
- 代码侧仍然可以继续使用 `logger = get_logger(__name__)` 与 logging 风格的 `%s` 占位符
- 底层输出统一由 Loguru 负责（文件 + 控制台），并启用 `enqueue=True` 异步写入
- 捕获 `logging` 标准库日志、uvicorn/fastapi/sqlalchemy 等第三方日志，统一导入 Loguru
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

from loguru import logger as _loguru_logger

from app.config import (
    DEEPAGENTS_DEBUG,
    LANGCHAIN_DEBUG,
    LANGCHAIN_VERBOSE,
    LANGGRAPH_DEBUG,
    LOG_LEVEL,
)
from app.config import LOGS_DIR as LOG_DIR


# 输出格式尽量与旧 logging 版保持一致，便于 grep/排障。
_LOGURU_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {extra[logger_name]} | {message}"

# 终端过滤：DEBUG 模式下只输出关键日志，过滤第三方噪音
_CONSOLE_NOISY_PREFIXES = (
    "httpcore",
    "httpx",
    "openai",
    "sqlalchemy",
    "asyncpg",
    "uvicorn.access",
)


def _console_filter(record: "loguru.Message") -> bool:
    """DEBUG 模式终端过滤器：只保留业务日志，过滤第三方 DEBUG 噪音。"""
    name = record["extra"].get("logger_name", "")
    # LLM 调用只输出失败（WARNING+），成功太频繁
    if name == "app.infra.llm" and record["level"].name == "DEBUG":
        return False
    # 过滤第三方库噪音
    for prefix in _CONSOLE_NOISY_PREFIXES:
        if name.startswith(prefix) or name == prefix:
            return False
    return True


class _InterceptHandler(logging.Handler):
    """把标准 logging.Record 转发到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _loguru_logger.level(record.levelname).name
        except (ValueError, TypeError):
            level = record.levelno

        # record.getMessage() 已经完成了 %-style 格式化
        msg = record.getMessage()

        # 让 loguru 的 caller 定位尽量指向“真实调用点”，而不是 logging 框架内部。
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _loguru_logger.bind(logger_name=record.name).opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, msg)


class LoguruLoggerProxy:
    """项目内统一 logger 对象。

    目标：不用改全项目日志调用代码，就能把输出切到 Loguru，并启用异步写入。
    同时支持两种常见写法：
    - logging 风格：logger.info("x=%s", x)
    - loguru 风格： logger.info("x={}", x)
    """

    def __init__(self, name: str):
        self._name = name
        self._logger = _loguru_logger.bind(logger_name=name)

    def bind(self, **kwargs: Any) -> "LoguruLoggerProxy":
        proxy = LoguruLoggerProxy(self._name)
        proxy._logger = self._logger.bind(**kwargs)  # type: ignore[attr-defined]
        return proxy

    def _format_message(self, message: Any, args: tuple[Any, ...]) -> tuple[str, tuple[Any, ...]]:
        if not args:
            return (str(message), ())

        if not isinstance(message, str):
            return (str(message), ())

        # 优先保留 loguru 的 {} 格式化能力
        if "{" in message and "}" in message:
            return (message, args)

        # 兼容 logging 的 %-style 格式化
        try:
            return (message % args, ())
        except (TypeError, ValueError):
            # 兜底：不让日志调用因为格式问题崩掉
            return (f"{message} args={args!r}", ())

    def _log(self, level: str, message: Any, *args: Any, **kwargs: Any) -> None:
        exc_info = kwargs.pop("exc_info", None)
        msg, fmt_args = self._format_message(message, args)

        l = self._logger
        if exc_info:
            if exc_info is True:
                l = l.opt(exception=True)
            else:
                l = l.opt(exception=exc_info)
        l.log(level, msg, *fmt_args, **kwargs)

    def debug(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("DEBUG", message, *args, **kwargs)

    def info(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("INFO", message, *args, **kwargs)

    def warning(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("WARNING", message, *args, **kwargs)

    def error(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("ERROR", message, *args, **kwargs)

    def exception(self, message: Any, *args: Any, **kwargs: Any) -> None:
        # 与 logging 行为一致：记录当前异常堆栈（需要在 except 块内调用）
        msg, fmt_args = self._format_message(message, args)
        self._logger.opt(exception=True).error(msg, *fmt_args, **kwargs)

    def critical(self, message: Any, *args: Any, **kwargs: Any) -> None:
        self._log("CRITICAL", message, *args, **kwargs)


def get_logger(name: str) -> LoguruLoggerProxy:
    """获取项目 logger（不再返回标准库 logging.Logger）。"""
    return LoguruLoggerProxy(name)


# Module-level logger factory for structured [Module][Sub] prefixes
def get_module_logger(module: str, *, sub: str = "") -> LoguruLoggerProxy:
    """Get a logger with [Module][Sub] prefix format.

    Usage:
        logger = get_module_logger("resource", sub="workflow")
        logger.info("启动资源生成")  # outputs: [Resource][Workflow] 启动资源生成

    The prefix is embedded in the logger name so it appears in the {extra[logger_name]} field.
    """
    if sub:
        name = f"[{module.capitalize()}][{sub.capitalize()}]"
    else:
        name = f"[{module.capitalize()}]"
    return LoguruLoggerProxy(name)


# Global flag for debug mode
_APP_DEBUG_MODE: bool = False


def is_debug_mode() -> bool:
    """Check if the application is running in debug mode."""
    return _APP_DEBUG_MODE


def configure_logging(*, debug: bool = False) -> None:
    """Configure logging based on APP_DEBUG flag.

    Must be called once at application startup (in main.py lifespan).
    - debug=True (development): log level = INFO, all module logs visible
    - debug=False (production): log level = INFO, step details and LLM calls at DEBUG
    """
    global _APP_DEBUG_MODE
    _APP_DEBUG_MODE = debug

    level = "DEBUG" if debug else "INFO"
    setup_logging(level=level, force=True)


def _parse_level(raw: str) -> str:
    value = (raw or "").strip().upper()
    return value if value in {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else "INFO"


def _debug_logging_enabled() -> bool:
    return LANGCHAIN_DEBUG or LANGGRAPH_DEBUG or DEEPAGENTS_DEBUG


def _configure_langchain_debug_flags() -> None:
    try:
        from langchain_core.globals import set_debug, set_verbose
    except Exception:
        _loguru_logger.bind(logger_name="root").warning(
            "[Logging] LangChain debug flags unavailable"
        )
        return

    set_debug(LANGCHAIN_DEBUG or LANGGRAPH_DEBUG or DEEPAGENTS_DEBUG)
    set_verbose(LANGCHAIN_VERBOSE)


def _configure_external_logger_levels() -> None:
    debug_names = {
        "langchain",
        "langchain_core",
        "langgraph",
        "deepagents",
    }
    debug_level = logging.DEBUG if _debug_logging_enabled() else logging.WARNING

    for name in debug_names:
        ext_logger = logging.getLogger(name)
        ext_logger.setLevel(debug_level)
        ext_logger.handlers.clear()
        ext_logger.propagate = True

_CONFIGURED = False


def setup_logging(*, level: Optional[str] = None, force: bool = False) -> None:
    """初始化 Loguru + 标准库 logging 拦截。

    在应用启动时调用一次即可（FastAPI lifespan）。

    DEBUG 模式：
      - 终端：INFO+（业务操作、Agent 流程、LLM 失败）
      - error.log：ERROR+，异步写入
      - app.log：不写
    生产模式：
      - 终端：WARNING+（只看错误和警告）
      - app.log：INFO+，异步写入
      - error.log：ERROR+，异步写入
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = _parse_level(level or ("DEBUG" if _debug_logging_enabled() else LOG_LEVEL))

    # 1) 配置 loguru sinks
    _loguru_logger.remove()
    _loguru_logger.configure(extra={"logger_name": "root"})

    if _APP_DEBUG_MODE:
        # DEBUG 模式：终端输出关键日志，不写 app.log
        _loguru_logger.add(
            sys.stderr,
            level="INFO",
            format=_LOGURU_FORMAT,
            filter=_console_filter,
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )
    else:
        # 生产模式：终端只看 WARNING+，app.log 写 INFO+
        _loguru_logger.add(
            sys.stderr,
            level="WARNING",
            format=_LOGURU_FORMAT,
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )
        _loguru_logger.add(
            str(LOG_DIR / "app.log"),
            level="INFO",
            format=_LOGURU_FORMAT,
            rotation="00:00",
            retention="30 days",
            encoding="utf-8",
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )

    # error.log：两种模式都写
    _loguru_logger.add(
        str(LOG_DIR / "error.log"),
        level="ERROR",
        format=_LOGURU_FORMAT,
        rotation="10 MB",
        retention=10,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )

    # 2) 拦截标准 logging：所有旧代码 logger.info("x=%s", x) 都会被转发到 loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # 清理常见第三方 logger 的 handler，避免重复输出
    for name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy",
        "sqlalchemy.engine",
        "asyncpg",
    ):
        ext_logger = logging.getLogger(name)
        ext_logger.handlers.clear()
        ext_logger.propagate = True

    _configure_langchain_debug_flags()
    _configure_external_logger_levels()

    _loguru_logger.bind(logger_name="root").info(
        "[Logging] 日志系统初始化完成: mode={mode} console={console} file={file} level={level}",
        mode="DEBUG(终端+error.log)" if _APP_DEBUG_MODE else "PROD(终端WARNING+app.log+error.log)",
        console="INFO(filtered)" if _APP_DEBUG_MODE else "WARNING+",
        file="error.log" if _APP_DEBUG_MODE else "app.log+error.log",
        level=log_level,
    )

    _CONFIGURED = True
