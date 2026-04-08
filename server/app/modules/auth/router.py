from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.dependencies import get_session
from app.core.response import HttpResponse
from app.core.security import get_current_user, revoke_token
from app.models.user import User
from app.modules.auth import schemas, service
from app.modules.profile.profile_agent import profile_agent

router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("")
def create_user(data: schemas.UserRegister, session: Session = Depends(get_session)):
    """注册新用户"""
    svc = service.UserService(session)
    result = svc.register(data)
    if not result:
        body = HttpResponse.error(code=400, message="用户名已存在")
        return JSONResponse(status_code=400, content=body.model_dump())
    return HttpResponse.success(data=result)


@router.post("/auth")
def login(data: schemas.UserLogin, session: Session = Depends(get_session)):
    """登录（创建认证会话）"""
    svc = service.UserService(session)
    result = svc.authenticate(data.username, data.password)
    if not result:
        body = HttpResponse.error(code=401, message="用户名或密码错误")
        return JSONResponse(status_code=401, content=body.model_dump())
    return HttpResponse.success(data=result)


@router.delete("/auth")
def logout(
        background_tasks: BackgroundTasks,  # ⭐ 新增：注入后台任务管理器
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
):
    """登出（删除认证会话），并触发后台画像整理"""
    # 1. 正常执行退出登录逻辑
    revoke_token(credentials.credentials, session)

    # 2. ⭐ 生命周期兜底触发：启动后台画像更新
    background_tasks.add_task(profile_agent.build_profile, user_id=current_user.id)

    return HttpResponse.success(message="退出登录成功")


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return HttpResponse.success(data=current_user)


@router.patch("/me")
def update_me(
        data: schemas.UserUpdate,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
):
    """更新当前用户信息"""
    svc = service.UserService(session)
    user = svc.update(current_user.id, data)
    if not user:
        return HttpResponse.error(code=404, message="用户不存在")
    return HttpResponse.success(data=user)