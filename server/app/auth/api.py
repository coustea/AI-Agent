"""认证模块 HTTP 路由。

提供用户注册、登录、登出、信息查询/更新、头像上传等 REST API 端点。
所有路由挂载在 /api/v1/users 前缀下。
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import get_current_user
from app.auth.service import auth_usecases
from app.infra.database import get_session
from app.infra.models import User
from app.config import user_avatar_dir, avatar_url
from app.infra.response import HttpResponse

# 创建路由实例，挂载在 /api/v1/users 下
router = APIRouter()
# Bearer Token 认证方案，自动从 Authorization 头提取 Token
bearer_scheme = HTTPBearer()


# POST /api/v1/users — 用户注册
@router.post("")
async def create_user(
    data: UserRegister,
    session: AsyncSession = Depends(get_session),
):
    """用户注册接口。

    创建新用户账号，用户名必须唯一。
    成功返回 201 Created，用户名重复返回 400 并附带字段级错误信息。
    """
    result = await auth_usecases.register(session, data)
    if not result.success:
        return HttpResponse.error(
            code=400,
            message=result.error_message,
            data={"field": result.error_field},
        )
    return HttpResponse.success(data=result.data, status_code=201)


# POST /api/v1/users/auth — 用户登录
@router.post("/auth")
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """用户登录接口。

    验证用户名密码，成功签发 JWT Token。
    失败时返回 401 并附带字段级错误信息（用户不存在 / 密码错误）。
    """
    result = await auth_usecases.login(session, data)
    if not result.success:
        return HttpResponse.error(
            code=401,
            message=result.error_message,
            data={"field": result.error_field},
        )
    return HttpResponse.success(data=result.data)


# POST /api/v1/users/auth/logout — 用户登出
@router.post("/auth/logout")
async def logout(
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """用户登出接口。

    从白名单中删除 Token 使其立即失效。
    后台异步更新用户画像数据。
    """
    # 撤销 Token，使其立即失效
    await auth_usecases.logout(session, credentials.credentials)
    # 后台任务：异步更新用户学习画像（不影响响应速度）
    background_tasks.add_task(auth_usecases.upsert_profile_on_logout, current_user.id)
    return HttpResponse.success(message="退出登录成功")


@router.get("/auth/status")
async def check_auth_status(current_user: User = Depends(get_current_user)):
    """轻量级 Token 探活接口。

    用于前端检测当前 Token 是否仍然有效，有效则返回 200。
    """
    return HttpResponse.success(message="Token 有效")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return HttpResponse.success(data=UserRead.model_validate(current_user))


@router.patch("/me")
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """更新当前用户信息（PATCH 语义，只更新提交的字段）。"""
    user = await auth_usecases.update_me(session, current_user.id, data)
    if not user:
        return HttpResponse.error(code=404, message="用户不存在")
    return HttpResponse.success(data=UserRead.model_validate(user))


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """上传用户头像。

    支持 jpg, jpeg, png, gif, webp 格式，最大 2MB。
    文件保存到 static/{username}/avatar/avatar.{ext} 目录。
    """
    # 验证文件类型：只允许常见的图片格式
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        return HttpResponse.error(
            code=400,
            message="不支持的图片格式，仅支持 jpg, png, gif, webp",
        )

    # 读取文件内容并验证大小（最大 2MB）
    content = await file.read()
    max_size = 2 * 1024 * 1024  # 2MB
    if len(content) > max_size:
        return HttpResponse.error(
            code=400,
            message=f"文件大小超过限制（最大 {max_size // (1024 * 1024)}MB）",
        )

    # 确保头像存储目录存在：static/{username}/avatar/
    username = current_user.username
    avatar_dir = user_avatar_dir(username)
    avatar_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名：avatar.{扩展名}
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    filename = f"avatar.{ext}"
    file_path = avatar_dir / filename

    # 将文件内容写入磁盘
    file_path.write_bytes(content)

    # 生成头像访问 URL 并更新用户记录
    avatar_url_str = avatar_url(username, ext)
    user = await auth_usecases.update_me(
        session,
        current_user.id,
        UserUpdate(avatar=avatar_url_str)
    )

    return HttpResponse.success(data={"avatar": avatar_url_str})


@router.get("/avatars/{username}/{filename}")
async def get_avatar(username: str, filename: str):
    """获取用户头像文件。

    根据用户名和文件名返回头像图片，不存在则返回 404。
    """
    from fastapi.responses import FileResponse

    avatar_dir = user_avatar_dir(username)
    file_path = avatar_dir / filename
    if not file_path.exists():
        return HttpResponse.error(code=404, message="头像不存在")
    # 直接返回文件响应（FastAPI 自动处理 Content-Type）
    return FileResponse(file_path)
