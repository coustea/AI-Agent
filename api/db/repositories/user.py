"""User repository with CRUD operations using SQLModel."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import EmailStr
from sqlmodel import select, Session

from api.db.models import User, UserCreate, UserUpdate, UserRead


class UserRepository:
    """User repository with CRUD operations."""

    def __init__(self, session: Session):
        self.session = session

    # ================= CREATE =================

    async def create_user(
        self, user_data: UserCreate
    ) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User data with password
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if username already exists
        existing_user = await self.get_by_username(user_data.username)
        if existing_user:
            raise ValueError(f"Username '{user_data.username}' already exists")

        # Check if email already exists
        existing_email = await self.get_by_email(user_data.email)
        if existing_email:
            raise ValueError(f"Email '{user_data.email}' already exists")

        # Hash password
        from api.utils.security import get_password_hash
        password_hash = get_password_hash(user_data.password)

        # Create user object
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            full_name=user_data.full_name,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    # ================= READ =================

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        statement = select(User).where(User.username == username)
        return self.session.exec(statement).first()

    async def get_by_email(self, email: EmailStr) -> Optional[User]:
        """Get user by email."""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    async def get_all_users(
        self, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get all users with pagination."""
        statement = select(User).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    async def get_active_users(
        self, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get all active users with pagination."""
        statement = select(User).where(User.is_active == True).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    # ================= UPDATE =================

    async def update_user(
        self, user_id: int, user_data: UserUpdate
    ) -> Optional[User]:
        """
        Update user by ID.
        
        Args:
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Updated user object, or None if user not found
            
        Raises:
            ValueError: If email already exists for another user
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Get existing user data
        update_data = user_data.dict(exclude_unset=True)
        
        # Check if email is being updated and already exists
        if "email" in update_data and update_data["email"] != user.email:
            existing_email = await self.get_by_email(update_data["email"])
            if existing_email and existing_email.id != user_id:
                raise ValueError(f"Email '{update_data['email']}' already exists")

        # If password is being updated, hash it
        if "password" in update_data:
            from api.utils.security import get_password_hash
            update_data["password_hash"] = get_password_hash(update_data["password"])
            del update_data["password"]

        # Update user
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    async def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            old_password: Old password to verify
            new_password: New password
            
        Returns:
            True if password changed successfully
            
        Raises:
            ValueError: If old password is incorrect or user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify old password
        from api.utils.security import verify_password
        if not verify_password(old_password, user.password_hash):
            raise ValueError("Invalid old password")

        # Hash new password
        from api.utils.security import get_password_hash
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()

        self.session.add(user)
        self.session.commit()

        return True

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate user by ID."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_active = False
        user.updated_at = datetime.utcnow()

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    async def activate_user(self, user_id: int) -> Optional[User]:
        """Activate user by ID."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_active = True
        user.updated_at = datetime.utcnow()

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    # ================= DELETE =================

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user was deleted, False if user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        self.session.delete(user)
        self.session.commit()

        return True

    # ================= SEARCH =================

    async def search_users(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """
        Search users by username or email.
        
        Args:
            query: Search query string
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            List of matching users
        """
        statement = (
            select(User)
            .where(User.username.contains(query))
            .offset(skip)
            .limit(limit)
        )
        return self.session.exec(statement).all()

    # ================= COUNT =================

    async def count_users(self) -> int:
        """Count total number of users."""
        statement = select(User)
        return len(self.session.exec(statement).all())

    async def count_active_users(self) -> int:
        """Count number of active users."""
        statement = select(User).where(User.is_active == True)
        return len(self.session.exec(statement).all())

    # ================= EXISTS =================

    async def username_exists(self, username: str) -> bool:
        """Check if username exists."""
        return await self.get_by_username(username) is not None

    async def email_exists(self, email: EmailStr) -> bool:
        """Check if email exists."""
        return await self.get_by_email(email) is not None
