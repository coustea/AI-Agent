"""Application route registration."""

from __future__ import annotations

from fastapi import FastAPI

from app.auth.api import router as auth_router
from app.avatar.api import router as avatar_router
from app.chat.api import router as chat_router
from app.dashboard.api import router as dashboard_router
from app.evaluation.api import router as evaluation_router
from app.path.api import router as path_router
from app.resource.api import router as resource_router
from app.websockets import router as websocket_router

try:
    from app.quiz.api import router as quiz_router
except ModuleNotFoundError as exc:
    if exc.name != "app.quiz":
        raise
    quiz_router = None


def install_routes(app: FastAPI) -> None:
    app.include_router(auth_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(chat_router, prefix="/api/v1/ai", tags=["ai"])
    app.include_router(dashboard_router, prefix="/api/v1/ai", tags=["dashboard"])
    app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
    app.include_router(path_router, prefix="/api/v1/ai", tags=["path"])
    app.include_router(evaluation_router, prefix="/api/v1/ai", tags=["evaluation"])
    app.include_router(avatar_router, prefix="/api/v1/ai", tags=["avatar"])
    if quiz_router is not None:
        app.include_router(quiz_router, prefix="/api/v1/ai", tags=["quiz"])
    app.include_router(websocket_router)
