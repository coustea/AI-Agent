"""集中日志配置模块 —— 基于 Loguru，异步写入。

- 业务代码统一 `logger = get_logger(__name__)`，支持 logging 风格 `%s` 占位符
- 捕获 `logging` 标准库日志与 uvicorn/fastapi/sqlalchemy 等第三方日志，统一导入 Loguru
- macOS spawn 模式下 multiprocessing SemLock 数量受限，因此不启用 enqueue

统一日志输出：
- 终端：INFO+（关键业务日志、Agent 流程、LLM 调用）
- app.log：INFO+，异步写入，按天轮转
- error.log：ERROR+，异步写入，保留 10 个文件
"""

# 本模块基于 Loguru 统一日志输出，并拦截标准 logging 与第三方库日志到同一管线
from __future__ import annotations

import logging
import sys
from typing import Any, Optional

from loguru import logger as _loguru_logger

from app.config import LOGS_DIR as LOG_DIR


# 输出格式尽量与旧 logging 版保持一致，便于 grep/排障。
_LOGURU_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {extra[logger_name]} | {message}"

# 终端过滤：过滤第三方库噪音，保留关键业务日志
_CONSOLE_NOISY_PREFIXES = (
    "httpcore",
    "httpx",
    "openai",
    "sqlalchemy",
    "aiomysql",
    "uvicorn.access",
)


# 终端日志过滤器：丢弃第三方库噪音，仅保留业务日志
def _console_filter(record: Any) -> bool:
    """终端过滤器：只保留业务日志，过滤第三方噪音。"""
    name = record["extra"].get("logger_name", "")
    # 过滤第三方库噪音
    for prefix in _CONSOLE_NOISY_PREFIXES:
        if name.startswith(prefix) or name == prefix:
            return False
    return True


# 标准库 logging 到 loguru 的拦截处理器
class _InterceptHandler(logging.Handler):
    """把标准 logging.Record 转发到 loguru。"""

    # 将标准 logging 记录转发到 loguru，并定位真实调用点
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _loguru_logger.level(record.levelname).name
        except (ValueError, TypeError):
            level = record.levelno

        # record.getMessage() 已经完成了 %-style 格式化
        msg = record.getMessage()

        # 让 loguru 的 caller 定位尽量指向"真实调用点"，而不是 logging 框架内部。
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
    """项目内统一 logger 对象，支持两种格式化写法。

    - logging 风格：logger.info("x=%s", x)
    - loguru 风格： logger.info("x={}", x)
    """

    # 初始化：分别持有标准库 logger 与 loguru 绑定对象
    def __init__(self, name: str):
        self._name = name
        self._stdlib_logger = logging.getLogger(name)
        self._logger = _loguru_logger.bind(logger_name=name)

    # 返回绑定了额外上下文的新 logger 代理
    def bind(self, **kwargs: Any) -> "LoguruLoggerProxy":
        proxy = LoguruLoggerProxy(self._name)
        proxy._logger = self._logger.bind(**kwargs)
        return proxy

    # 兼容 loguru 的 {} 与 logging 的 %-style 两种消息格式化
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

    # 统一日志入口
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

    # 记录异常堆栈（需在 except 块内调用）
    def exception(self, message: Any, *args: Any, **kwargs: Any) -> None:
        """记录当前异常堆栈（需在 except 块内调用）。"""
        msg, fmt_args = self._format_message(message, args)
        self._logger.opt(exception=True).error(msg, *fmt_args, **kwargs)


# 获取项目统一 logger（返回 LoguruLoggerProxy 而非标准库 Logger）
def get_logger(name: str) -> LoguruLoggerProxy:
    """获取项目 logger（不再返回标准库 logging.Logger）。"""
    return LoguruLoggerProxy(name)


# 配置日志系统：统一输出关键日志到终端、app.log 与 error.log
def configure_logging() -> None:
    """Configure logging - unified output of key logs.

    统一日志输出：
    - 终端：INFO+（关键业务日志、Agent 流程、LLM 调用）
    - app.log：INFO+，异步写入，按天轮转
    - error.log：ERROR+，异步写入，保留 10 个文件
    """
    setup_logging(level="INFO", force=True)


_CONFIGURED = False


# 初始化 Loguru 与标准库日志拦截，并配置各输出 sink（应用启动时调用一次）
def setup_logging(*, level: Optional[str] = None, force: bool = False) -> None:
    """初始化 Loguru + 标准库 logging 拦截。

    在应用启动时调用一次即可（FastAPI lifespan）。

    统一输出关键日志：
      - 终端：INFO+（关键业务日志、Agent 流程、LLM 调用）
      - app.log：INFO+，异步写入，按天轮转
      - error.log：ERROR+，异步写入，保留 10 个文件
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = "INFO"

    # 1) 配置 loguru sinks
    _loguru_logger.remove()
    _loguru_logger.configure(extra={"logger_name": "root"})

    # 终端：INFO+，过滤第三方噪音
    _loguru_logger.add(
        sys.stderr,
        level="INFO",
        format=_LOGURU_FORMAT,
        filter=_console_filter,
        backtrace=True,
        diagnose=False,
        enqueue=False,
    )

    # app.log：INFO+，异步写入，按天轮转
    _loguru_logger.add(
        str(LOG_DIR / "app.log"),
        level="INFO",
        format=_LOGURU_FORMAT,
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=False,
    )

    # error.log：ERROR+，保留 10 个文件
    _loguru_logger.add(
        str(LOG_DIR / "error.log"),
        level="ERROR",
        format=_LOGURU_FORMAT,
        rotation="10 MB",
        retention=10,
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
        enqueue=False,
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
        "aiomysql",
    ):
        ext_logger = logging.getLogger(name)
        ext_logger.handlers.clear()
        ext_logger.propagate = True

    _loguru_logger.bind(logger_name="root").info(
        "[Logging] 日志系统初始化完成: console=INFO(filtered) file=app.log+error.log level=%s",
        log_level,
    )

    _CONFIGURED = True