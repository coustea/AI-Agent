from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.engine import init_db
from app.modules.user.router import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Learning Platform", lifespan=lifespan)
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])


@app.get("/")
async def root():
    return {"message": "AI Learning Platform is running"}
