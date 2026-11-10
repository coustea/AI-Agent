"""认证模块 HTTP 路由。

提供用户注册、登录、登出、信息查询/更新、头像上传等 REST API 端点。
所有路由挂载在 /api/v1/users 前缀下。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import get_current_user
from app.auth.service import auth_service
from app.config import avatar_url, user_avatar_dir
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User
from app.response import HttpResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("")
async def create_user(
    data: UserRegister,
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """用户注册接口。"""
    user = await auth_service.register(session, data)
    return HttpResponse.success(data={"user": user}, status_code=201)


@router.post("/auth")
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """用户登录接口。"""
    result = await auth_service.login(session, data)
    return HttpResponse.success(data=result)


@router.post("/auth/logout")
async def logout() -> HttpResponse:
    """用户登出接口（无状态模式，前端清除本地 Token 即可）。"""
    return HttpResponse.success(message="退出登录成功")


@router.get("/auth/status")
async def check_auth_status() -> HttpResponse:
    """轻量级 Token 探活接口（已通过 JWTMiddleware 强鉴权）。"""
    return HttpResponse.success(message="Token 有效")


@router.get("/me")
async def get_me(session: AsyncSession = Depends(get_session)) -> HttpResponse:
    """获取当前登录用户的完整详细信息。"""
    user = await session.get(User, get_current_user().id)
    if not user:
        return HttpResponse.error(code=404, message="用户不存在")
    return HttpResponse.success(data=UserRead.model_validate(user))


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """上传用户头像。"""
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        return HttpResponse.error(
            code=400,
            message="不支持的图片格式，仅支持 jpg, png, gif, webp",
        )

    content = await file.read()
    max_size = 2 * 1024 * 1024  # 2MB
    if len(content) > max_size:
        return HttpResponse.error(
            code=400,
            message=f"文件大小超过限制（最大 {max_size // (1024 * 1024)}MB）",
        )

    claims = get_current_user()
    username = claims.username
    avatar_dir = user_avatar_dir(username)
    avatar_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    filename = f"avatar.{ext}"
    file_path = avatar_dir / filename
    file_path.write_bytes(content)

    avatar_url_str = avatar_url(username, ext)
    await auth_service.update_profile(
        session,
        claims.id,
        UserUpdate(avatar=avatar_url_str),
    )
    logger.info("[AuthAPI] 头像上传成功: user_id={} ext={}", claims.id, ext)
    return HttpResponse.success(data={"avatar": avatar_url_str})
