"""Application lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.db.session import init_db
from app.bootstrap.container import get_container
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting up")
    await init_db()
    container = get_container()
    container.file_store.ensure_roots()
    yield
    logger.info("Application shutting down")
    await container.aclose()
