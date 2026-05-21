"""Application entrypoint."""

from __future__ import annotations

import sys
import traceback
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger, setup_logging
from app.infra.database import init_db, engine
from app.infra.errors import AppError, ServiceError, NotFoundError, ForbiddenError
from app.infra.health import check_all
from app.infra.school_import import import_schools
from app.prompts import init_prompts
from app.utils.storage import local_file_store
from app.auth.security import decode_token
from app.avatar.bridge.manager import avatar_bridge_manager
from app.config import HOST, PORT

logger = get_logger(__name__)


class _SuppressRtcCollectAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/v1/logging/collect/list" not in record.getMessage()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    setup_logging()
    logging.getLogger("uvicorn.access").addFilter(_SuppressRtcCollectAccessFilter())
    logger.info("Application starting up")

    # 启动健康检测：并行检测数据库和 LLM，失败不阻塞
    report = await check_all()
    app.state.health_report = report

    # 数据库初始化：失败时警告但不阻塞
    try:
        await init_db()
    except Exception as exc:
        logger.error(
            "[Startup] 数据库初始化失败，部分功能不可用: %s: %s",
            type(exc).__name__,
            exc,
        )

    local_file_store.ensure_roots()

    # 导入学校数据
    try:
        async with AsyncSession(engine) as session:
            await import_schools(session)
    except Exception:
        logger.exception("[Startup] 学校数据导入失败")

    # 预加载所有 prompt 到内存
    try:
        init_prompts()
        logger.info("[Startup] Prompt 预加载完成")
    except Exception:
        logger.exception("[Startup] Prompt 预加载失败")

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
async def rtc_logging_collect_bypass(
    request: Request, call_next: Any
) -> JSONResponse:
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

app.include_router(auth_router, prefix="/api/v1/users", tags=["auth"])
app.include_router(chat_router, prefix="/api/v1/ai", tags=["chat"])
app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
app.include_router(path_router, prefix="/api/v1/ai", tags=["path"])
app.include_router(avatar_router, prefix="/api/v1/ai", tags=["avatar"])
app.include_router(evaluation_router, prefix="/api/v1/ai", tags=["evaluation"])


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_map = {
        ServiceError: 503,
        NotFoundError: 404,
        ForbiddenError: 403,
    }
    status = status_map.get(type(exc), 500)
    logger.error(
        "[%s] %s %s: %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc.message,
    )
    return JSONResponse(
        status_code=status,
        content={"code": status, "message": exc.message, "data": None},
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
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
async def root() -> dict[str, str]:
    return {"message": "AI Learning Platform is running"}


@app.get("/api/v1/health")
async def health_check(request: Request) -> dict:
    report = getattr(request.app.state, "health_report", None)
    if report:
        return report.to_dict()
    return {"status": "unknown", "services": {}}


@app.api_route(
    "/api/v1/logging/collect/list",
    methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
)
async def rtc_logging_collect_list() -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": []}


@app.websocket("/ws/avatar")
async def avatar_websocket(
    ws: WebSocket,
    token: str = Query(..., description="JWT token"),
) -> None:
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
    host = HOST
    port = PORT
    uvicorn.run(app, host=host, port=port, log_config=None)


if __name__ == "__main__":
    main()
