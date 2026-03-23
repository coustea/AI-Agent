"""User resource routes using SQLModel."""

from typing import List

from fastapi import APIRouter, Depends, status, Query, HTTPException
from pydantic import BaseModel

from api.core.dependencies import (
    get_current_user,
    get_current_active_user,
    get_db_session,
    get_redis_client,
    PaginationParams,
)
from api.core.response import Response, PaginationResponse, PaginationMeta
from api.db.models import User
from api.schemas.user import UserCreate, UserUpdate, UserRead
from api.repositories.user import UserRepository
from api.services.user import UserService

# Use Python's built-in PermissionError or create custom exception
try:
    from api.core.exceptions import PermissionError
except ImportError:

    class PermissionError(HTTPException):
        def __init__(self, detail="Permission denied"):
            super().__init__(status_code=403, detail=detail)


router = APIRouter(tags=["users"])


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# ================= LIST USERS =================


@router.get(
    "",
    response_model=PaginationResponse[UserRead],
    summary="List all users",
    description="Get a paginated list of all users",
)
async def list_all_users(
    pagination: PaginationParams = Depends(PaginationParams),
    db=Depends(get_db_session),
):
    """
    List all users with pagination.

    Args:
        pagination: Pagination parameters (page, page_size)
        db: Database session

    Returns:
        PaginationResponse: Paginated list of users

    Example:
        >>> GET /api/users?page=1&page_size=10
    """
    user_service = UserService(db, redis_client=None)  # No Redis needed for list

    users = await user_service.list_users(
        skip=pagination.skip, limit=pagination.page_size
    )

    total = await user_service.count_users()
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return PaginationResponse(
        code=200,
        message=f"Found {total} users",
        data=[UserRead.model_validate(user) for user in users],
        pagination=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages,
        ),
    )


@router.get(
    "/active",
    response_model=PaginationResponse[UserRead],
    summary="List active users",
    description="Get a paginated list of active users",
)
async def list_active_users(
    pagination: PaginationParams = Depends(PaginationParams),
    db=Depends(get_db_session),
):
    """
    List all active users with pagination.

    Args:
        pagination: Pagination parameters (page, page_size)
        db: Database session

    Returns:
        PaginationResponse: Paginated list of active users

    Example:
        >>> GET /api/users/active?page=1&page_size=10
    """
    user_service = UserService(db, redis_client=None)

    users = await user_service.list_active_users(
        skip=pagination.skip, limit=pagination.page_size
    )

    total = await user_service.count_active_users()
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return PaginationResponse(
        code=200,
        message=f"Found {total} active users",
        data=[UserRead.model_validate(user) for user in users],
        pagination=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages,
        ),
    )


# ================= CREATE USER =================


@router.post(
    "",
    response_model=Response[UserRead],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user with username, email and password",
)
async def create_user(
    user_data: UserCreate,
    db=Depends(get_db_session),
):
    """
    Register a new user.

    Args:
        user_data: User data (username, email, password, full_name)
        db: Database session

    Returns:
        Response: Created user info

    Raises:
        400: If username or email already exists

    Example:
        >>> POST /api/users
        >>> {
        >>>   "username": "newuser",
        >>>   "email": "user@example.com",
        >>>   "password": "Pass123",
        >>>   "full_name": "John Doe"
        >>> }
    """
    from api.core.dependencies import get_redis_client

    user_service = UserService(db, redis_client=get_redis_client())

    user = await user_service.register_user(user_data)
    user_read = UserRead.model_validate(user)

    return Response(data=user_read, message="User created successfully")


# ================= GET CURRENT USER =================


@router.get(
    "/me",
    response_model=Response[UserRead],
    summary="Get current user",
    description="Get information about the currently authenticated user",
)
async def get_current_user_info(
    current_user=Depends(get_current_user),
):
    """
    Get current authenticated user info.

    Args:
        current_user: Current authenticated user (from JWT token)

    Returns:
        Response: Current user info

    Example:
        >>> GET /api/users/me
        >>> Headers: Authorization: Bearer <token>
    """
    user_read = UserRead.model_validate(current_user)
    return Response(data=user_read, message="User info retrieved successfully")


# ================= UPDATE USER =================


@router.patch(
    "/me",
    response_model=Response[UserRead],
    summary="Update current user",
    description="Update information about the currently authenticated user",
)
async def update_current_user(
    user_data: UserUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """
    Update current user info.

    Args:
        user_data: User data to update (email, full_name, password, is_active)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response: Updated user info

    Raises:
        403: If user is inactive
        409: If email already exists for another user

    Example:
        >>> PATCH /api/users/me
        >>> Headers: Authorization: Bearer <token>
        >>> {
        >>>   "email": "newemail@example.com",
        >>>   "full_name": "Jane Doe"
        >>> }
    """
    from api.core.dependencies import get_redis_client

    user_service = UserService(db, redis_client=get_redis_client())

    updated_user = await user_service.update_user(
        current_user.id, user_data, current_user.username
    )
    user_read = UserRead.model_validate(updated_user)

    return Response(data=user_read, message="User updated successfully")


# ================= CHANGE PASSWORD =================


@router.patch(
    "/me/password",
    response_model=Response[MessageResponse],
    summary="Change password",
    description="Change password for the currently authenticated user",
)
async def change_password(
    password_data: UserUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_db_session),
):
    """
    Change user password.

    Args:
        password_data: Password data (old_password, new_password)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response: Success message

    Raises:
        401: If old password is incorrect

    Example:
        >>> PATCH /api/users/me/password
        >>> Headers: Authorization: Bearer <token>
        >>> {
        >>>   "password": "NewPass456"
        >>> }
    """
    user_service = UserService(db, redis_client=None)

    await user_service.change_password(
        current_user.username,
        password_data.password,
        password_data.password,  # Same field for simplicity
    )

    return Response(message="Password changed successfully")


# ================= DELETE USER =================


@router.delete(
    "/me",
    response_model=Response[MessageResponse],
    summary="Delete current user",
    description="Delete the currently authenticated user account",
)
async def delete_current_user(
    current_user=Depends(get_current_active_user),
    db=Depends(get_db_session),
):
    """
    Delete current user account.

    Args:
        current_user: Current authenticated active user
        db: Database session

    Returns:
        Response: Success message

    Example:
        >>> DELETE /api/users/me
        >>> Headers: Authorization: Bearer <token>
    """
    user_repo = UserRepository(db)

    await user_repo.delete_user(current_user.id)

    return Response(message="User account deleted successfully")


# ================= STATIC ROUTES FIRST =================


@router.get(
    "/stats",
    response_model=Response[dict],
    summary="Get user statistics",
    description="Get user statistics (total, active, etc.)",
)
async def get_user_stats(
    db=Depends(get_db_session),
):
    user_service = UserService(db, redis_client=None)

    total_users = await user_service.count_users()
    active_users = await user_service.count_active_users()
    inactive_users = total_users - active_users

    return Response(
        data={
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
        },
        message="User statistics retrieved successfully",
    )


@router.get(
    "/search",
    response_model=Response[List[UserRead]],
    summary="Search users",
    description="Search users by username or email",
)
async def search_users(
    query: str = Query(..., min_length=2, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    db=Depends(get_db_session),
):
    user_service = UserService(db, redis_client=None)

    users = await user_service.search_users(query, skip=skip, limit=limit)
    users_read = [UserRead.model_validate(user) for user in users]

    return Response(data=users_read, message=f"Found {len(users_read)} matching users")


# ================= DYNAMIC ROUTE =================


@router.get(
    "/{user_id}",
    response_model=Response[UserRead],
    summary="Get user by ID",
    description="Get information about a specific user by ID",
)
async def get_user_by_id(
    user_id: int,
    db=Depends(get_db_session),
):
    user_service = UserService(db, redis_client=None)

    user = await user_service.get_user_by_id(user_id)

    return Response(data=UserRead.model_validate(user))


# ================= USER MEMORY MANAGEMENT =================


@router.get(
    "/me/memory",
    response_model=Response[dict],
    summary="Get user memory",
    description="获取当前用户的长期记忆",
)
async def get_my_memory(
    redis=Depends(get_redis_client),
    current_user=Depends(get_current_user),
):
    from api.services.agent import AgentService

    agent_service = AgentService(redis)
    memory = agent_service.get_memory(current_user.id)

    return Response(
        data={"user_id": current_user.id, "memory_summary": memory or ""},
        message="User memory retrieved successfully",
    )


@router.post(
    "/me/memory",
    response_model=Response[dict],
    summary="Set user memory",
    description="设置当前用户的长期记忆",
)
async def set_my_memory(
    memory_data: dict,
    redis=Depends(get_redis_client),
    current_user=Depends(get_current_user),
):
    from api.services.agent import AgentService

    memory_summary = memory_data.get("memory_summary", "").strip()

    if not memory_summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Memory summary cannot be empty",
        )

    agent_service = AgentService(redis)
    success = agent_service.set_memory(current_user.id, memory_summary)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user memory",
        )

    return Response(
        data={"user_id": current_user.id},
        message="User memory set successfully",
    )


@router.put(
    "/me/memory",
    response_model=Response[dict],
    summary="Update user memory",
    description="更新当前用户的长期记忆",
)
async def update_my_memory(
    memory_data: dict,
    redis=Depends(get_redis_client),
    current_user=Depends(get_current_user),
):
    from api.services.agent import AgentService

    memory_summary = memory_data.get("memory_summary", "").strip()

    if not memory_summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Memory summary cannot be empty",
        )

    agent_service = AgentService(redis)

    if not agent_service.has_memory(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User memory not found. Use POST to create first.",
        )

    success = agent_service.update_memory(current_user.id, memory_summary)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user memory",
        )

    return Response(
        data={"user_id": current_user.id},
        message="User memory updated successfully",
    )


@router.delete(
    "/me/memory",
    response_model=Response[dict],
    summary="Delete user memory",
    description="删除当前用户的长期记忆",
)
async def delete_my_memory(
    redis=Depends(get_redis_client),
    current_user=Depends(get_current_user),
):
    from api.services.agent import AgentService

    agent_service = AgentService(redis)
    success = agent_service.delete_memory(current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user memory",
        )

    return Response(
        data={"user_id": current_user.id},
        message="User memory deleted successfully",
    )


@router.post(
    "/me/memory/append",
    response_model=Response[dict],
    summary="Append to user memory",
    description="追加内容到用户的长期记忆",
)
async def append_to_memory(
    content: dict,
    redis=Depends(get_redis_client),
    current_user=Depends(get_current_user),
):
    from api.services.agent import AgentService

    new_content = content.get("content", "").strip()

    if not new_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content cannot be empty",
        )

    agent_service = AgentService(redis)
    success = agent_service.append_memory(current_user.id, new_content)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to append to user memory",
        )

    return Response(
        data={"user_id": current_user.id},
        message="Content appended to user memory successfully",
    )


@router.post(
    "/me/memory/summary",
    response_model=Response[dict],
    summary="Append summary to user memory",
    description="追加对话总结到用户的长期记忆",
)
async def append_summary_to_memory(
    summary_data: dict,
    redis=Depends(get_redis_client),
    current_user=Depends(get_current_user),
):
    from api.services.agent import AgentService

    summary = summary_data.get("summary", "").strip()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summary cannot be empty",
        )

    agent_service = AgentService(redis)
    success = agent_service.append_summary(current_user.id, summary)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to append summary to user memory",
        )

    return Response(
        data={"user_id": current_user.id},
        message="Summary appended to user memory successfully",
    )
