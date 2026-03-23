import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional

LOGS_DIR = Path(__file__).parent.parent / "logs"


class AsyncLogger:
    def __init__(
        self,
        name: str = "agent",
        level: int = logging.INFO,
        log_prefix: str = "agent",
        session_id: Optional[str] = None
    ):
        self.name = name
        self.level = level
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self._create_log_file(log_prefix)

        self._queue = Queue()
        self._queue_handler = logging.handlers.QueueHandler(self._queue)
        self._queue_handler.setLevel(level)

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

        self._listener = logging.handlers.QueueListener(
            self._queue,
            file_handler,
            respect_handler_level=True
        )
        self._listener.start()

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []
        self.logger.addHandler(self._queue_handler)
        self.logger.propagate = False

        self._log_startup()

    def _create_log_file(self, log_prefix: str) -> Path:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return LOGS_DIR / f"{log_prefix}_{timestamp}.log"

    def _log_startup(self):
        self.logger.info("=" * 60)
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Log File: {self.log_file}")
        self.logger.info("=" * 60)

    def _log(self, level: int, stage: str, message: str, emoji: str = "📝"):
        self.logger.log(level, f"{emoji} [{stage}] {message}")

    def retrieve(self, message: str):
        self._log(logging.INFO, "RETRIEVE", message, "📚")

    def think(self, message: str):
        self._log(logging.INFO, "THINK", message, "🤔")

    def plan(self, message: str):
        self._log(logging.INFO, "PLAN", message, "🛠️")

    def act(self, message: str):
        self._log(logging.INFO, "ACT", message, "⚡")

    def reflect(self, message: str):
        self._log(logging.INFO, "REFLECT", message, "👀")

    def success(self, message: str):
        self._log(logging.INFO, "SUCCESS", message, "✅")

    def error(self, message: str):
        self._log(logging.ERROR, "ERROR", message, "❌")

    def warning(self, message: str):
        self._log(logging.WARNING, "WARNING", message, "⚠️")

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def log_request(self, method: str, path: str, client: str, params: dict = None):
        msg = f"{method} {path} from {client}"
        if params:
            msg += f" | params: {params}"
        self._log(logging.INFO, "REQUEST", msg, "🌐")

    def log_response(self, status: int, duration: float, path: str = ""):
        msg = f"Status {status} | {duration:.3f}s"
        if path:
            msg = f"{path} - {msg}"
        self._log(logging.INFO, "RESPONSE", msg, "📤")

    def close(self):
        self.logger.info("=" * 60)
        self.logger.info("Session ended")
        self.logger.info("=" * 60)
        self._listener.stop()


_global_logger: Optional[AsyncLogger] = None


def setup_logger(
    name: str = "agent",
    level: int = logging.INFO,
    log_prefix: str = "agent"
) -> AsyncLogger:
    global _global_logger
    if _global_logger:
        return _global_logger
    _global_logger = AsyncLogger(name, level, log_prefix)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []
    root_logger.addHandler(_global_logger._queue_handler)
    return _global_logger


def get_logger() -> Optional[AsyncLogger]:
    return _global_logger


def close_logger():
    global _global_logger
    if _global_logger:
        _global_logger.close()
        _global_logger = None


async def log_middleware(request, call_next):
    import time
    logger = get_logger()
    if logger:
        start_time = time.time()
        logger.log_request(
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown"
        )

    response = await call_next(request)

    if logger:
        duration = time.time() - start_time
        logger.log_response(
            status=response.status_code,
            duration=duration,
            path=request.url.path
        )

    return response
