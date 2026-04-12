import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

# 清除代理设置，避免 ChatOpenAI 初始化时因 socks 代理报错
for _proxy_key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_key, None)

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.engine import init_db
from app.core.logging import get_logger, setup_logging
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.profile.router import router as profile_router
from app.modules.resource.router import router as resource_router
from app.modules.knowledge_base.router import router as knowledge_router
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting up")
    await init_db()
    logger.info("Database initialized")

    # 确保上传目录存在
    upload_dir = Path("workplace/chat-uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    yield
    logger.info("Application shutting down")


app = FastAPI(title="AI Learning Platform", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/users", tags=["users"])
app.include_router(chat_router, prefix="/api/v1/ai", tags=["chat"])
app.include_router(profile_router, prefix="/api/v1/ai", tags=["profile"])
app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
app.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge_base"])


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


if __name__ == '__main__':
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "9999"))
    uvicorn.run(app, host=host, port=port)
