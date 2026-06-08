"""Application lifecycle hooks."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.chat.prompt_manager import chat_prompts
from app.infra.database import check_all, init_db
from app.infra.prompts import warm_prompt_loaders
from app.memory.prompt_manager import memory_prompts
from app.path.prompt_manager import path_prompts
from app.resource.prompt_manager import resource_prompts


@asynccontextmanager
async def lifespan(app: FastAPI):
    warm_prompt_loaders(
        [
            chat_prompts.loader,
            resource_prompts.loader,
            path_prompts.loader,
            memory_prompts.loader,
        ]
    )
    await init_db()
    await check_all()
    yield
