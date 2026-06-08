"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEBUG
from app.exceptions import install_exception_handlers
from app.infra.logging import configure_logging
from app.lifecycle import lifespan
from app.routes import install_routes


def create_app() -> FastAPI:
    configure_logging(debug=DEBUG)

    app = FastAPI(title="AI Learning Platform", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(app)
    install_routes(app)
    return app
