"""Application entrypoint."""

from __future__ import annotations

import sys
import traceback
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.infra.logging import get_logger, setup_logging
from app.infra.database import init_db
from app.shared.storage import local_file_store
from app.auth.security import decode_token
from app.avatar.bridge.manager import avatar_bridge_manager
from app.config import SERVER_HOST, SERVER_PORT
from sqlalchemy.exc import OperationalError, DBAPIError

logger = get_logger(__name__)


class _SuppressRtcCollectAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/v1/logging/collect/list" not in record.getMessage()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    setup_logging()
    logging.getLogger("uvicorn.access").addFilter(_SuppressRtcCollectAccessFilter())
    logger.info("Application starting up")

    try:
        await init_db()
    except (OperationalError, DBAPIError, ConnectionRefusedError, OSError) as exc:
        logger.error(
            "[Startup] 数据库初始化失败，应用无法启动: error_type=%s error=%s\n"
            "请检查数据库服务是否运行，以及 .env 中的数据库配置是否正确。",
            type(exc).__name__,
            exc,
        )
        raise
    except Exception as exc:
        logger.exception("[Startup] 数据库初始化发生未知异常: %s", exc)
        raise

    local_file_store.ensure_roots()
    try:
        yield
    finally:
        logger.info("Application shutting down")
        try:
            await avatar_bridge_manager.cleanup_all()
        except Exception:
            logger.exception("Avatar bridge cleanup failed during shutdown")


app = FastAPI(title="AI Learning Platform", lifespan=app_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rtc_logging_collect_bypass(request: Request, call_next):
    if request.url.path == "/api/v1/logging/collect/list":
        return JSONResponse({"code": 0, "message": "ok", "data": []})
    return await call_next(request)

# Mount feature module routers
from app.auth.api import router as auth_router
from app.chat.api import router as chat_router
from app.resource.api import router as resource_router
from app.path.api import router as path_router
from app.avatar.api import router as avatar_router
from app.evaluation.api import router as evaluation_router
from app.memory.api import router as memory_router

app.include_router(auth_router, prefix="/api/v1/users", tags=["auth"])
app.include_router(chat_router, prefix="/api/v1/ai", tags=["chat"])
app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
app.include_router(path_router, prefix="/api/v1/ai", tags=["path"])
app.include_router(avatar_router, prefix="/api/v1/ai", tags=["avatar"])
app.include_router(evaluation_router, prefix="/api/v1/ai", tags=["evaluation"])
app.include_router(memory_router, prefix="/api/v1/ai", tags=["memory"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        str(exc),
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.get("/")
async def root():
    return {"message": "AI Learning Platform is running"}


# Compatibility endpoint for third-party RTC SDK telemetry polling.
# Some RTCPlayer builds repeatedly call this path with various methods.
@app.api_route(
    "/api/v1/logging/collect/list",
    methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
)
async def rtc_logging_collect_list():
    return {"code": 0, "message": "ok", "data": []}


@app.websocket("/ws/avatar")
async def avatar_websocket(
    ws: WebSocket,
    token: str = Query(..., description="JWT token"),
):
    """Avatar WebSocket 端点（统一挂到主服务入口）。"""
    try:
        user_id = decode_token(token)
    except Exception:
        await ws.close(code=4001, reason="认证失败")
        return

    await ws.accept()
    logger.info("[AvatarBridge] 用户 %d 已连接", user_id)

    bridge = await avatar_bridge_manager.get_or_create_bridge(user_id)
    try:
        await bridge.handle_frontend(ws)
    except WebSocketDisconnect:
        logger.info("[AvatarBridge] 用户 %d 已断开", user_id)
    except Exception as exc:
        logger.error("[AvatarBridge] 连接异常: %s", exc, exc_info=exc)


def main() -> None:
    """统一后端启动入口函数。"""
    host = SERVER_HOST
    port = SERVER_PORT
    uvicorn.run(app, host=host, port=port, log_config=None)


if __name__ == "__main__":
    main()
