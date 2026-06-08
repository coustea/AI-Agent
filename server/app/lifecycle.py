"""Application lifecycle hooks."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.database import check_all, init_db
from app.prompts import init_prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_prompts()
    await init_db()
    await check_all()
    yield
