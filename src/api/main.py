"""FastAPI application entry point."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import auth, users
from api.db.database import init_db
from api.core.redis import init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_redis()
    await init_db()
    yield


app = FastAPI(
    title="ReAct Agent API",
    description="API for the ReAct Agent Framework",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return {"message": "ReAct Agent API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)
