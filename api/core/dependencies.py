"""Route dependencies for authentication and database."""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.db.engine import get_db, get_redis
from api.repositories.user import UserRepository
from api.db.models import User
from api.schemas.user import UserRead
from api.core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserInactiveError,
)
from api.services.redis_service import RedisService

security = HTTPBearer()


async def get_db_session():
    """
    Get database session.

    Yields:
        Session: SQLAlchemy session
    """
    session = get_db()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


async def get_redis_client() -> RedisService:
    """
    Get Redis client.

    Returns:
        RedisService: Redis client instance
    """
    return get_redis()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db_session),
    redis=Depends(get_redis_client),
) -> User:
    """
    Get current authenticated user.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        redis: Redis client

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token with Redis
    from api.utils.jwt import verify_token, get_token_username, get_token_jti

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = get_token_username(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is in Redis (use jti instead of full token)
    jti = get_token_jti(token)
    redis_key = f"token:{username}:{jti}"
    if not redis.exists(redis_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_username(username)
    if not user:
        raise UserNotFoundError()

    if not user.is_active:
        raise UserInactiveError()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (same as get_current_user, can be extended).

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


class PaginationParams:
    """Pagination parameters for listing resources."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 10,
    ):
        self.page = max(1, page)
        self.page_size = max(1, min(100, page_size))
        self.skip = (self.page - 1) * self.page_size
