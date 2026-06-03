"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect

from app.auth.api import router as auth_router
from app.auth.security import AuthError, _resolve_current_user_from_token
from app.chat.api import router as chat_router
from app.evaluation.api import router as evaluation_router
from app.path.api import router as path_router
from app.resource.api import router as resource_router
from app.avatar.api import router as avatar_router
from app.avatar.bridge.manager import avatar_bridge_manager
from app.infra.database import init_db, check_all
from app.infra.logging import configure_logging
from app.infra.response import HttpResponse
from app.config import DEBUG

configure_logging(debug=DEBUG)

try:
    from app.quiz.api import router as quiz_router
except ModuleNotFoundError as exc:
    if exc.name != "app.quiz":
        raise
    quiz_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await check_all()
    yield


app = FastAPI(title="AI Learning Platform", lifespan=lifespan)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Convert AuthError to HttpResponse envelope with HTTP 401."""
    return HttpResponse.error(code=401, message=exc.message)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert FastAPI's built-in HTTPException (e.g. 422 validation) to envelope."""
    return HttpResponse.error(code=exc.status_code, message=str(exc.detail))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/users", tags=["users"])
app.include_router(chat_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
app.include_router(path_router, prefix="/api/v1/ai", tags=["path"])
app.include_router(evaluation_router, prefix="/api/v1/ai", tags=["evaluation"])
app.include_router(avatar_router, prefix="/api/v1/ai", tags=["avatar"])
if quiz_router is not None:
    app.include_router(quiz_router, prefix="/api/v1/ai", tags=["quiz"])


@app.websocket("/ws/avatar")
async def avatar_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "").strip()
    if not token:
        await websocket.close(code=1008, reason="missing token")
        return

    try:
        user = await _resolve_current_user_from_token(token)
    except AuthError:
        await websocket.close(code=1008, reason="invalid token")
        return

    await websocket.accept()
    bridge = await avatar_bridge_manager.get_or_create_bridge(user.id)
    try:
        await bridge.handle_frontend(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        await avatar_bridge_manager.cleanup(user.id)


if __name__ == "__main__":
    import subprocess
    import sys

    from app.config import HOST, PORT

    cmd = [
        sys.executable, "-m", "fastapi",
        "dev", "main.py",
        "--host", HOST,
        "--port", str(PORT),
    ]
    subprocess.run(cmd)
