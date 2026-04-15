"""Application bootstrap settings."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


def load_environment() -> None:
    load_dotenv(ENV_FILE)


def get_server_host() -> str:
    return os.getenv("SERVER_HOST", "0.0.0.0")


def get_server_port() -> int:
    return int(os.getenv("SERVER_PORT", "9999"))


__all__ = ["BASE_DIR", "ENV_FILE", "get_server_host", "get_server_port", "load_environment"]
