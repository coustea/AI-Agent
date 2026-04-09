from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.dependencies import get_session
from app.core.response import HttpResponse
from app.core.security import get_current_user, revoke_token
from app.models.user import User
from app.modules.auth import schemas, service
from app.modules.profile.profile_agent import profile_agent

router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("")
async def create_user(data: schemas.UserRegister, session: AsyncSession = Depends(get_session)):
    """注册新用户"""
    svc = service.UserService(session)
    result = await svc.register(data)
    if not result:
        body = HttpResponse.error(code=400, message="用户名已存在")
        return JSONResponse(status_code=400, content=body.model_dump())
    return HttpResponse.success(data=result)


@router.post("/auth")
async def login(data: schemas.UserLogin, session: AsyncSession = Depends(get_session)):
    """登录（创建认证会话）"""
    svc = service.UserService(session)
    result = await svc.authenticate(data.username, data.password)
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
):
    """登出（删除认证会话），并触发后台画像整理"""
    await revoke_token(credentials.credentials, session)

    background_tasks.add_task(profile_agent.build_profile, user_id=current_user.id)

    return HttpResponse.success(message="退出登录成功")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return HttpResponse.success(data=current_user)


@router.patch("/me")
async def update_me(
        data: schemas.UserUpdate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
):
    """更新当前用户信息"""
    svc = service.UserService(session)
    user = await svc.update(current_user.id, data)
    if not user:
        return HttpResponse.error(code=404, message="用户不存在")
    return HttpResponse.success(data=user)
