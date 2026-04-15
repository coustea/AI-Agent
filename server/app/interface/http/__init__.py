"""HTTP router aggregation."""

from fastapi import APIRouter

from app.interface.http.auth import router as auth_router
from app.interface.http.chat import router as chat_router
from app.interface.http.profile import router as profile_router
from app.interface.http.resource import router as resource_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api/v1/users", tags=["users"])
api_router.include_router(chat_router, prefix="/api/v1/ai", tags=["chat"])
api_router.include_router(profile_router, prefix="/api/v1/ai", tags=["profile"])
api_router.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])

__all__ = ["api_router"]
