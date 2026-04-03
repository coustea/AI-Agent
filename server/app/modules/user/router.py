from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.dependencies import get_session
from app.core.response import HttpResponse
from app.core.security import blacklist_token, get_current_user
from app.models.user import User
from app.modules.user import schemas, service

router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("/register")
def register(data: schemas.UserRegister, session: Session = Depends(get_session)):
    svc = service.UserService(session)
    if svc.repo.get_by_username(data.username):
        return HttpResponse.error(code=400, message="用户名已存在")
    user = svc.register(data)
    return HttpResponse.success(data=user)


@router.post("/login")
def login(data: schemas.UserLogin, session: Session = Depends(get_session)):
    svc = service.UserService(session)
    result = svc.authenticate(data.username, data.password)
    if not result:
        return HttpResponse.error(code=401, message="用户名或密码错误")
    return HttpResponse.success(data=result)


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    blacklist_token(credentials.credentials, session)
    return HttpResponse.success(message="退出登录成功")


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return HttpResponse.success(data=current_user)


@router.patch("/me")
def update_me(
    data: schemas.UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    svc = service.UserService(session)
    user = svc.update(current_user.id, data)
    if not user:
        return HttpResponse.error(code=404, message="用户不存在")
    return HttpResponse.success(data=user)
