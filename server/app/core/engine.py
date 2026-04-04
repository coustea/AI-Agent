import os
from collections.abc import Generator
from pathlib import Path

import redis
from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

# .env 在 server 目录下
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ── MySQL ──
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Aa123456")
DB_NAME = os.getenv("DB_NAME", "agent")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

mysql_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    mysql_url,
    echo=DB_ECHO,
    pool_pre_ping=True,
)

# ── Redis ──
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)


APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"


def init_db() -> None:
    """导入所有模型并创建表"""
    import app.models  # noqa: F401

    if APP_DEBUG:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
