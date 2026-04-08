import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

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
from app.utils.mcp_manager import mcp_manager
from app.utils.skills_manager import skills_manager
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting up")
    await init_db()
    logger.info("Database initialized")

    mcp_manager.load_from_settings()
    # 加载外部配置
    external_mcp_config = Path("/home/couseta/.gemini/antigravity/mcp_config.json")
    if external_mcp_config.exists():
        mcp_manager.load_from_settings(external_mcp_config)
        logger.info(f"External MCP plugins registered from {external_mcp_config}")

    logger.info("MCP plugins registered")

    skills_manager.load_all_skills()
    logger.info("Agent skills loaded")

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
