"""FastAPI application entry point using SQLModel."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

from api.core.error_handlers import (
    api_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from api.core.exceptions import APIError
from api.db.engine import init_db, init_redis
from api.db.models import settings
from api.router import auth, users, redis_sessions, agent

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print("=" * 60)
    print("🚀 ReAct Agent API Starting...")
    print("=" * 60)
    print(f"📋 Environment: {'Development' if settings.api_host == '0.0.0.0' else 'Production'}")
    print(f"🔌 Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    print(f"🔗 Redis: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")
    print("=" * 60)

    # Initialize database
    try:
        init_db()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

    # Initialize Redis
    try:
        init_redis()
    except Exception as e:
        print(f"❌ Redis initialization failed: {e}")
        raise

    print("=" * 60)
    print("🎉 Ready to accept requests")
    print("=" * 60)
    print(f"📚 API Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"🏥 Health Check: http://{settings.api_host}:{settings.api_port}/health")
    print("=" * 60)

    yield

    # Shutdown
    print("=" * 60)
    print("🛑 ReAct Agent API Shutting down...")
    print("=" * 60)


app = FastAPI(
    title="ReAct Agent API",
    description="API for ReAct Agent Framework - Built with SQLModel and FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, http_exception_handler)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(redis_sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(agent.router, prefix="/api", tags=["Agent"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ReAct Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "architecture": "SQLModel + FastAPI",
    }


# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    from api.db.engine import get_redis

    redis_status = "disconnected"
    try:
        redis_client = get_redis()
        redis_client.client.ping()
        redis_status = "connected"
    except:
        pass

    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected",
        "redis": redis_status,
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_host == "0.0.0.0",  # Auto-reload in development
    )
