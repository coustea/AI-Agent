"""Auth HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.bootstrap.container import AppContainer
from app.core.response import HttpResponse
from app.interface.http.dependencies import get_app_container, get_current_user, get_session
from app.models.user import User
from app.shared.dto.auth import UserLogin, UserRegister, UserUpdate

router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("")
async def create_user(
    data: UserRegister,
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
):
    result = await container.auth_usecases.register(session, data)
    if not result:
        body = HttpResponse.error(code=400, message="用户名已存在")
        return JSONResponse(status_code=400, content=body.model_dump())
    return HttpResponse.success(data=result)


@router.post("/auth")
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
):
    result = await container.auth_usecases.login(session, data)
    if not result:
        body = HttpResponse.error(code=401, message="用户名或密码错误")
        return JSONResponse(status_code=401, content=body.model_dump())
    return HttpResponse.success(data=result)


@router.delete("/auth")
async def logout(
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
):
    await container.auth_usecases.logout(session, credentials.credentials)
    background_tasks.add_task(container.auth_usecases.build_profile_on_logout, current_user.id)
    return HttpResponse.success(message="退出登录成功")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return HttpResponse.success(data=current_user)


@router.patch("/me")
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
):
    user = await container.auth_usecases.update_me(session, current_user.id, data)
    if not user:
        return HttpResponse.error(code=404, message="用户不存在")
    return HttpResponse.success(data=user)
