"""User service with business logic using SQLModel and Repository."""

from typing import Optional, List, Dict, Any

from sqlmodel import Session, select

from api.core.response import Response
from api.core.exceptions import (
    UserNotFoundError,
    DuplicateUsernameError,
    DuplicateEmailError,
    InvalidCredentialsError,
    WrongPasswordError,
)
from api.db.models import User
from api.schemas.user import UserCreate, UserUpdate, UserRead, UserLogin, PasswordChange
from api.schemas.auth import Token
from api.repositories.user import UserRepository
from api.utils.security import verify_password, get_password_hash
from api.utils.jwt import create_access_token, get_token_jti


TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 days in seconds


class UserService:
    """User service with business logic."""

    def __init__(self, session: Session, redis_client):
        """
        Initialize user service.

        Args:
            session: Database session
            redis_client: Redis client for token management
        """
        self.session = session
        self.redis = redis_client
        self.user_repo = UserRepository(session)

    # ================= REGISTER =================

    async def register_user(self, user_data: UserCreate) -> UserRead:
        """
        Register a new user.

        Args:
            user_data: User data with password

        Returns:
            UserRead: Created user info

        Raises:
            DuplicateUsernameError: If username already exists
            DuplicateEmailError: If email already exists
        """
        try:
            # Create user (Repository will hash password)
            user = await self.user_repo.create_user(user_data)
            return UserRead.model_validate(user)
        except ValueError as e:
            if "already exists" in str(e):
                if "Username" in str(e):
                    raise DuplicateUsernameError(message=str(e))
                elif "Email" in str(e):
                    raise DuplicateEmailError(message=str(e))
            raise

    # ================= LOGIN =================

    async def login_user(self, user_data: UserLogin) -> Token:
        """
        Login user and return JWT token.

        Args:
            user_data: Login credentials (username, password)

        Returns:
            Token: JWT token with user info

        Raises:
            InvalidCredentialsError: If username or password is wrong
            UserInactiveError: If user account is inactive
        """
        username = user_data.username.lower()
        password = user_data.password

        # Get user by username
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise InvalidCredentialsError(message="Invalid username or password")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError(message="Invalid username or password")

        # Check if user is active
        if not user.is_active:
            raise UserInactiveError(message="User account is inactive")

        # Create JWT token
        access_token, expires_in = create_access_token(username)
        jti = get_token_jti(access_token)

        # Store token in Redis (blacklist)
        redis_key = f"token:{username}:{jti}"
        self.redis.set(redis_key, access_token, ex=TOKEN_EXPIRE_SECONDS)

        # Return token with user info
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserRead.model_validate(user),
        )

    # ================= LOGOUT =================

    async def logout_user(self, username: str, token: str) -> bool:
        """
        Logout user by revoking token.

        Args:
            username: Username
            token: JWT token to revoke

        Returns:
            bool: True if logout successful
        """
        jti = get_token_jti(token)
        redis_key = f"token:{username}:{jti}"
        self.redis.delete(redis_key)
        return True

    # ================= GET USER =================

    async def get_user_by_id(self, user_id: int) -> UserRead:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            UserRead: User info

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        return UserRead.model_validate(user)

    async def get_user_by_username(self, username: str) -> UserRead:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            UserRead: User info

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_by_username(username.lower())
        if not user:
            raise UserNotFoundError()

        return UserRead.model_validate(user)

    async def get_current_user_info(self, username: str) -> UserRead:
        """
        Get current authenticated user info.

        Args:
            username: Username

        Returns:
            UserRead: User info

        Raises:
            UserNotFoundError: If user not found
        """
        return await self.get_user_by_username(username)

    # ================= LIST USERS =================

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserRead]:
        """
        List all users with pagination.

        Args:
            skip: Number of items to skip
            limit: Number of items to return

        Returns:
            List[UserRead]: List of users
        """
        users = await self.user_repo.get_all_users(skip=skip, limit=limit)
        return [UserRead.model_validate(user) for user in users]

    async def list_active_users(
        self, skip: int = 0, limit: int = 100
    ) -> List[UserRead]:
        """
        List all active users with pagination.

        Args:
            skip: Number of items to skip
            limit: Number of items to return

        Returns:
            List[UserRead]: List of active users
        """
        users = await self.user_repo.get_active_users(skip=skip, limit=limit)
        return [UserRead.model_validate(user) for user in users]

    # ================= UPDATE USER =================

    async def update_user(
        self, user_id: int, user_data: UserUpdate, current_username: str
    ) -> UserRead:
        """
        Update user by ID.

        Args:
            user_id: User ID
            user_data: User data to update
            current_username: Current authenticated username (for permission check)

        Returns:
            UserRead: Updated user info

        Raises:
            UserNotFoundError: If user not found
            DuplicateEmailError: If email already exists for another user
            PermissionError: If current user is not the owner
        """
        # Check if user exists and if current user is the owner
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if user.username != current_username:
            raise PermissionError("You can only update your own account")

        # Update user
        updated_user = await self.user_repo.update_user(user_id, user_data)
        return UserRead.model_validate(updated_user)

    # ================= CHANGE PASSWORD =================

    async def change_password(
        self, username: str, password_data: PasswordChange
    ) -> bool:
        """
        Change user password.

        Args:
            username: Username
            password_data: Password change data (old_password, new_password)

        Returns:
            bool: True if password changed successfully

        Raises:
            WrongPasswordError: If old password is incorrect
            UserNotFoundError: If user not found
        """
        # Get user
        user = await self.user_repo.get_by_username(username.lower())
        if not user:
            raise UserNotFoundError()

        # Change password
        try:
            await self.user_repo.change_password(
                user.id, password_data.old_password, password_data.new_password
            )
            return True
        except ValueError as e:
            if "Wrong old password" in str(e):
                raise WrongPasswordError(message=str(e))
            raise

    # ================= DELETE/DEACTIVATE =================

    async def deactivate_user(self, user_id: int) -> UserRead:
        """
        Deactivate user by ID.

        Args:
            user_id: User ID

        Returns:
            UserRead: Deactivated user info

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.deactivate_user(user_id)
        if not user:
            raise UserNotFoundError()

        return UserRead.model_validate(user)

    async def activate_user(self, user_id: int) -> UserRead:
        """
        Activate user by ID.

        Args:
            user_id: User ID

        Returns:
            UserRead: Activated user info

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.activate_user(user_id)
        if not user:
            raise UserNotFoundError()

        return UserRead.model_validate(user)

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user by ID.

        Args:
            user_id: User ID

        Returns:
            bool: True if user was deleted successfully

        Raises:
            UserNotFoundError: If user not found
        """
        result = await self.user_repo.delete_user(user_id)
        if not result:
            raise UserNotFoundError()

        return True

    # ================= SEARCH =================

    async def search_users(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[UserRead]:
        """
        Search users by username or email.

        Args:
            query: Search query string
            skip: Number of items to skip
            limit: Number of items to return

        Returns:
            List[UserRead]: List of matching users
        """
        users = await self.user_repo.search_users(query, skip=skip, limit=limit)
        return [UserRead.model_validate(user) for user in users]

    # ================= COUNT =================

    async def count_users(self) -> int:
        """
        Count total number of users.

        Returns:
            int: Total number of users
        """
        return await self.user_repo.count_users()

    async def count_active_users(self) -> int:
        """
        Count number of active users.

        Returns:
            int: Number of active users
        """
        return await self.user_repo.count_active_users()
