"""User resource routes."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.response import Response
from api.schemas.auth import UserLogin, UserData, TokenData, PasswordChange
from api.services.auth import AuthService
from api.db.engine import get_db

router = APIRouter(prefix="/api/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> Dict:
    try:
        auth_service = AuthService(db)
        return await auth_service.verify_token_valid(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "", response_model=Response[TokenData], status_code=status.HTTP_201_CREATED
)
async def create_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register(user_data.username, user_data.password)
        login_result = await auth_service.login(user_data.username, user_data.password)

        token_data = TokenData(
            access_token=login_result["access_token"],
            token_type=login_result["token_type"],
            expires_in=login_result["expires_in"],
            user=UserData(
                username=user["username"],
                created_at=datetime.fromisoformat(user["created_at"]),
            ),
        )
        return Response(data=token_data, message="User created successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=Response[UserData])
async def get_user_me(current_user: Dict = Depends(get_current_user)):
    user_data = UserData(
        username=current_user.get("username", ""),
        created_at=datetime.fromisoformat(current_user["created_at"]),
    )
    return Response(data=user_data)


@router.patch("/me/password", response_model=Response)
async def update_password(
    password_data: PasswordChange,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    try:
        username = current_user.get("username")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
            )
        await auth_service.change_password(
            username, password_data.old_password, password_data.new_password
        )
        return Response(message="Password updated")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
