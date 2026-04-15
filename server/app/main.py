"""Application entrypoint wired to the new architecture."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.bootstrap.settings import get_server_host, get_server_port, load_environment

load_environment()

from app.bootstrap.lifespan import app_lifespan
from app.core.logging import get_logger
from app.interface.http import api_router

logger = get_logger(__name__)
app = FastAPI(title="AI Learning Platform", lifespan=app_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


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
    uvicorn.run(app, host=get_server_host(), port=get_server_port())
