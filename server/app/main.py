"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.api import router as auth_router
from app.auth.security import AuthError
from app.chat.api import router as chat_router
from app.evaluation.api import router as evaluation_router
from app.path.api import router as path_router
from app.resource.api import router as resource_router
from app.avatar.api import router as avatar_router
from app.infra.database import init_db
from app.infra.response import HttpResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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


if __name__ == "__main__":
    import uvicorn


    from app.config import DEBUG, HOST, PORT

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
