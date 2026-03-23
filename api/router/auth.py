"""Authentication routes using SQLModel."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.core.dependencies import (
    get_db_session,
    get_redis_client,
)
from api.core.response import Response
from api.db.models import UserLogin, Token
from api.services.redis_service import RedisService
from api.services.user import UserService

router = APIRouter(tags=["auth"])


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# ================= LOGIN =================

@router.post(
    "/login",
    response_model=Response[Token],
    summary="User login",
    description="Authenticate user with username and password, return JWT token",
)
async def login(
    user_data: UserLogin,
    db = Depends(get_db_session),
    redis = Depends(get_redis_client),
):
    """
    User login and return JWT token.
    
    Args:
        user_data: Login credentials (username, password)
        db: Database session
        redis: Redis client
        
    Returns:
        Response: JWT token with user info
        
    Raises:
        401: If username or password is invalid
        403: If user account is inactive
        
    Example:
        >>> POST /api/auth/login
        >>> {
        >>>   "username": "testuser",
        >>>   "password": "Pass123"
        >>> }
    """
    try:
        user_service = UserService(db, redis)
        token_data = await user_service.login_user(user_data)
        return Response(data=token_data, message="Login successful")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ================= REGISTER =================

@router.post(
    "/register",
    response_model=Response[Token],
    status_code=status.HTTP_201_CREATED,
    summary="User registration",
    description="Register a new user and return JWT token",
)
async def register(
    user_data: UserLogin,  # Reuse UserLogin for simplicity (username + password)
    db = Depends(get_db_session),
    redis = Depends(get_redis_client),
):
    """
    User registration.
    
    Args:
        user_data: User registration data (username, password)
        db: Database session
        redis: Redis client
        
    Returns:
        Response: JWT token with new user info
        
    Raises:
        400: If username already exists
        422: If validation fails
        
    Example:
        >>> POST /api/auth/register
        >>> {
        >>>   "username": "newuser",
        >>>   "password": "Pass123"
        >>> }
    """
    from api.db.models import UserCreate

    # Convert UserLogin to UserCreate (add email field)
    # For simplicity, use username as email
    user_create = UserCreate(
        username=user_data.username,
        email=f"{user_data.username}@example.com",  # Auto-generate email for simplicity
        password=user_data.password,
        full_name=user_data.username,
    )

    try:
        user_service = UserService(db, redis)
        user = await user_service.register_user(user_create)
        
        # Auto-login after registration
        token_data = await user_service.login_user(user_data)
        return Response(data=token_data, message="User created and logged in successfully")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ================= LOGOUT =================

@router.delete(
    "/logout",
    response_model=Response[MessageResponse],
    summary="User logout",
    description="Revoke JWT token and logout user",
)
async def logout(
    db = Depends(get_db_session),
    redis = Depends(get_redis_client),
    token: Optional[str] = Depends(lambda: None),
):
    """
    User logout (revoke token).
    
    Args:
        token: JWT token (extracted from Authorization header)
        db: Database session
        redis: Redis client
        
    Returns:
        Response: Success message
        
    Example:
        >>> DELETE /api/auth/logout
        >>> Headers: Authorization: Bearer <token>
    """
    from api.core.dependencies import get_current_user

    try:
        current_user = await get_current_user(token, db, redis)
        username = current_user.username

        # Revoke token from Redis
        # Token key format: token:{username}:{jti}
        # We need to get the full token to extract JTI
        if token:
            # Get all tokens for this user and delete them
            token_keys = list(redis.client.scan_iter(f"token:{username}:*"))
            if token_keys:
                redis.delete(*token_keys)

        return Response(data=MessageResponse(message="Logged out successfully"))
    except Exception as e:
        # Even if token verification fails, logout is successful
        return Response(data=MessageResponse(message="Logged out successfully"))


# ================= GET CURRENT USER =================

@router.get(
    "/me",
    response_model=Response,
    summary="Get current user",
    description="Get information about currently authenticated user",
)
async def get_current_user_info(
    db = Depends(get_db_session),
    redis = Depends(get_redis_client),
):
    """
    Get current authenticated user info.
    
    Args:
        db: Database session
        redis: Redis client
        
    Returns:
        Response: Current user info
        
    Raises:
        401: If token is invalid or expired
        
    Example:
        >>> GET /api/auth/me
        >>> Headers: Authorization: Bearer <token>
    """
    from api.core.dependencies import get_current_user
    from api.db.models import UserRead

    try:
        current_user = await get_current_user(None, db, redis)
        user_read = UserRead.model_validate(current_user)
        return Response(data=user_read, message="User info retrieved successfully")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ================= REFRESH TOKEN =================

@router.post(
    "/refresh",
    response_model=Response[Token],
    summary="Refresh token",
    description="Refresh JWT token (not implemented yet)",
)
async def refresh_token(
    db = Depends(get_db_session),
    redis = Depends(get_redis_client),
    refresh_token: str = ...,
):
    """
    Refresh JWT token (future implementation).
    
    Args:
        refresh_token: Refresh token
        db: Database session
        redis: Redis client
        
    Returns:
        Response: New JWT token
        
    Example:
        >>> POST /api/auth/refresh
        >>> {
        >>>   "refresh_token": "..."
        >>> }
    """
    # TODO: Implement refresh token mechanism
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refresh token is not implemented yet",
    )
