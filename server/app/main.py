import traceback
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.engine import init_db
from app.core.logging import get_logger, setup_logging
from app.modules.user.router import router as user_router
from app.modules.profile_builder.router import router as profile_router
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting up")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Application shutting down")


app = FastAPI(title="AI Learning Platform", lifespan=lifespan)
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(profile_router,prefix="/api/v1/ai",tags=["profile_builder"])


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
    uvicorn.run(app, host="0.0.0.0", port=9999)
