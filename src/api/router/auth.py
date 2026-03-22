"""Authentication routes."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.response import Response
from api.schemas.auth import UserLogin, UserData, TokenData
from api.services.auth import AuthService
from api.db.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
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


@router.post("/login", response_model=Response[TokenData])
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        result = await auth_service.login(user_data.username, user_data.password)
        user_info = result.get("user", {})
        created_at = user_info.get("created_at")

        token_data = TokenData(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=UserData(
                username=user_info.get("username", ""),
                created_at=datetime.fromisoformat(created_at)
                if created_at
                else datetime.now(),
            ),
        )
        return Response(data=token_data, message="Login successful")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.delete("/logout", response_model=Response)
async def logout(
    current_user: Dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    username = current_user.get("username")
    if username:
        await auth_service.logout(username, token)
    return Response(message="Logged out")
