"""Application lifecycle hooks."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.database import check_all, init_db
from app.infra.prompts import prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    prompts.warm_all()
    await init_db()
    await check_all()
    yield
