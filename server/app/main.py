"""Application entrypoint."""

from __future__ import annotations

import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from app.infra.logging import get_logger, setup_logging
from app.infra.database import init_db
from app.shared.storage import local_file_store

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting up")
    await init_db()
    local_file_store.ensure_roots()
    yield
    logger.info("Application shutting down")


app = FastAPI(title="AI Learning Platform", lifespan=app_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount feature module routers
from app.auth.api import router as auth_router
from app.chat.api import router as chat_router
from app.profile.api import router as profile_router
from app.resource.api import router as resource_router
from app.avatar.api import router as avatar_router

app.include_router(auth_router, prefix="/api/v1/users", tags=["auth"])
app.include_router(chat_router, prefix="/api/v1/ai", tags=["chat"])
app.include_router(profile_router, prefix="/api/v1/ai", tags=["profile"])
app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
app.include_router(avatar_router, prefix="/api/v1/ai", tags=["avatar"])


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


if __name__ == "__main__":
    host = __import__("os").getenv("SERVER_HOST", "0.0.0.0")
    port = int(__import__("os").getenv("SERVER_PORT", "9999"))
    uvicorn.run(app, host=host, port=port)
