"""Database engine configuration for MySQL using SQLModel."""

from typing import AsyncGenerator, Optional

from sqlmodel import Session, create_engine

from api.db.models import settings
from api.services.redis_service import RedisService

# Create SQLModel engine (sync for simplicity, can be async later)
engine = create_engine(
    f"mysql+pymysql://{settings.db_user}:{settings.db_password}@"
    f"{settings.db_host}:{settings.db_port}/{settings.db_name}",
    echo=settings.api_host == "0.0.0.0",  # Only echo in development
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


# Session factory
def get_session() -> AsyncGenerator[Session, None]:
    """
    Get database session.

    Yields:
        Session: SQLAlchemy session
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()


# Alias for backward compatibility
def get_db() -> Session:
    """
    Get database session (alias for get_session).

    Returns:
        Session: SQLAlchemy session
    """
    return Session(engine)


# Initialize tables
def init_db():
    """Initialize database tables."""
    from sqlmodel import SQLModel
    from api.db.models import User

    print("🗄️ Creating database tables...")
    try:
        SQLModel.metadata.create_all(engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        raise


# Redis configuration
_redis_client: Optional[RedisService] = None


def get_redis() -> RedisService:
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisService(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
        )
    return _redis_client


def init_redis():
    """Initialize Redis connection."""
    global _redis_client

    print("🔗 Testing Redis connection...")
    try:
        _redis_client = get_redis()
        _redis_client.client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        raise
