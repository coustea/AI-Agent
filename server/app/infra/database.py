"""Database engine and session factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    APP_DEBUG,
    DATABASE_URL,
    DB_ECHO,
    DB_INIT_MAX_RETRIES,
    DB_INIT_RETRY_DELAY_SEC,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)
from app.infra.logging import get_logger
from app.infra.models import import_all_models

logger = get_logger(__name__)


def _validate_database_settings() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required. Set it in .env before starting the app.")
    logger.debug("[Database] Using DATABASE_URL: %s", DATABASE_URL[:50] + "...")


_validate_database_settings()

engine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)


async def _test_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, DBAPIError, ConnectionRefusedError, OSError) as exc:
        logger.error(
            "[Database] Connection test failed url=%s error_type=%s error=%s",
            engine.url.render_as_string(hide_password=True),
            type(exc).__name__,
            exc,
        )
        return False
    except Exception as exc:
        logger.error(
            "[Database] Unexpected connection test error url=%s error_type=%s error=%s",
            engine.url.render_as_string(hide_password=True),
            type(exc).__name__,
            exc,
        )
        return False


async def init_db() -> None:
    max_retries = DB_INIT_MAX_RETRIES
    retry_delay_sec = DB_INIT_RETRY_DELAY_SEC

    if not await _test_connection():
        logger.error(
            "[Database] Unable to establish database connection: url=%s",
            engine.url.render_as_string(hide_password=True),
        )

    import_all_models()

    async def _run_once() -> None:
        if APP_DEBUG:
            logger.warning("[Database] APP_DEBUG=true, dropping and recreating all tables.")
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
                table_names = [row[0] for row in result.fetchall()]
                for table_name in table_names:
                    await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                if table_names:
                    logger.info("[Database] Dropped %d tables", len(table_names))

        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await _ensure_learning_events_columns(conn)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "[Database] Initializing database url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                APP_DEBUG,
                attempt,
                max_retries,
            )
            await _run_once()

            from app.infra.school_import import import_schools

            async with AsyncSession(engine, expire_on_commit=False) as session:
                await import_schools(session)

            logger.info(
                "[Database] Database initialization finished url=%s debug=%s attempt=%s/%s",
                engine.url.render_as_string(hide_password=True),
                APP_DEBUG,
                attempt,
                max_retries,
            )
            return
        except (OperationalError, DBAPIError, ConnectionRefusedError, OSError) as exc:
            if attempt >= max_retries:
                logger.exception(
                    "[Database] Initialization failed after retries attempts=%s error_type=%s error=%s",
                    max_retries,
                    type(exc).__name__,
                    exc,
                )
                raise
            logger.warning(
                "[Database] Initialization failed, retrying attempt=%s/%s retry_after=%.1fs error_type=%s error=%s",
                attempt,
                max_retries,
                retry_delay_sec,
                type(exc).__name__,
                exc,
            )
            await asyncio.sleep(retry_delay_sec)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    except OperationalError as exc:
        logger.warning("[Database] Ignoring cleanup connection error in get_session: %s", exc)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    except OperationalError as exc:
        logger.warning("[Database] Ignoring cleanup connection error in session_scope: %s", exc)


async def _ensure_learning_events_columns(conn) -> None:
    """Patch legacy tables to match current ORM fields."""
    statements = [
        'ALTER TABLE learning_events ADD COLUMN IF NOT EXISTS resource_item_id INTEGER',
        'ALTER TABLE learning_events ADD COLUMN IF NOT EXISTS path_id INTEGER',
        'ALTER TABLE learning_events ADD COLUMN IF NOT EXISTS path_node_id INTEGER',
        'ALTER TABLE learning_events ADD COLUMN IF NOT EXISTS node_id VARCHAR(50)',
        'ALTER TABLE learning_paths ADD COLUMN IF NOT EXISTS path_key VARCHAR(100)',
        'ALTER TABLE learning_paths ADD COLUMN IF NOT EXISTS title VARCHAR(200)',
        'ALTER TABLE learning_paths ADD COLUMN IF NOT EXISTS course VARCHAR(200)',
        'ALTER TABLE learning_paths ADD COLUMN IF NOT EXISTS topic VARCHAR(200)',
        'ALTER TABLE learning_paths ADD COLUMN IF NOT EXISTS source_resource_id INTEGER',
        "ALTER TABLE learning_paths ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active'",
        'ALTER TABLE learning_path_nodes ADD COLUMN IF NOT EXISTS resource_item_id INTEGER',
        'ALTER TABLE learning_path_nodes ADD COLUMN IF NOT EXISTS knowledge_points JSONB',
        'ALTER TABLE learning_path_nodes ADD COLUMN IF NOT EXISTS weak_points JSONB',
        'CREATE INDEX IF NOT EXISTS ix_learning_events_resource_item_id ON learning_events (resource_item_id)',
        'CREATE INDEX IF NOT EXISTS ix_learning_events_path_id ON learning_events (path_id)',
        'CREATE INDEX IF NOT EXISTS ix_learning_events_path_node_id ON learning_events (path_node_id)',
        'CREATE INDEX IF NOT EXISTS ix_learning_events_node_id ON learning_events (node_id)',
        'CREATE INDEX IF NOT EXISTS ix_learning_paths_path_key ON learning_paths (path_key)',
        'CREATE INDEX IF NOT EXISTS ix_learning_paths_topic ON learning_paths (topic)',
        'CREATE INDEX IF NOT EXISTS ix_learning_paths_source_resource_id ON learning_paths (source_resource_id)',
        'CREATE INDEX IF NOT EXISTS ix_learning_paths_status ON learning_paths (status)',
        'CREATE INDEX IF NOT EXISTS ix_learning_path_nodes_resource_item_id ON learning_path_nodes (resource_item_id)',
    ]
    for statement in statements:
        await conn.execute(text(statement))
