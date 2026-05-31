"""Auth HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import get_current_user
from app.auth.service import auth_usecases
from app.infra.database import get_session
from app.infra.models import User
from app.infra.paths import AVATAR_DIR
from app.infra.response import HttpResponse

router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("")
async def create_user(
    data: UserRegister,
    session: AsyncSession = Depends(get_session),
):
    result = await auth_usecases.register(session, data)
    if not result:
        return HttpResponse.error(code=400, message="用户名已存在")
    return HttpResponse.success(data=result)


@router.post("/auth")
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    result = await auth_usecases.login(session, data)
    if not result:
        return HttpResponse.error(code=401, message="用户名或密码错误")
    return HttpResponse.success(data=result)


@router.delete("/auth")
async def logout(
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await auth_usecases.logout(session, credentials.credentials)
    background_tasks.add_task(auth_usecases.upsert_profile_on_logout, current_user.id)
    return HttpResponse.success(message="退出登录成功")


@router.get("/auth/status")
async def check_auth_status(current_user: User = Depends(get_current_user)):
    """轻量级 Token 探活接口"""
    return HttpResponse.success(message="Token 有效")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return HttpResponse.success(data=UserRead.model_validate(current_user))


@router.patch("/me")
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
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
    """
    # 验证文件类型
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        return HttpResponse.error(
            code=400,
            message="不支持的图片格式，仅支持 jpg, png, gif, webp",
        )

    # 验证文件大小（2MB）
    content = await file.read()
    max_size = 2 * 1024 * 1024
    if len(content) > max_size:
        return HttpResponse.error(
            code=400,
            message=f"文件大小超过限制（最大 {max_size // (1024 * 1024)}MB）",
        )

    # 确保目录存在
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)

    # 生成文件名：{user_id}.{ext}
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    filename = f"{current_user.id}.{ext}"
    file_path = AVATAR_DIR / filename

    # 保存文件
    file_path.write_bytes(content)

    # 生成 URL 并更新用户头像
    avatar_url = f"/api/v1/users/avatars/{filename}"
    user = await auth_usecases.update_me(
        session,
        current_user.id,
        UserUpdate(avatar=avatar_url)
    )

    return HttpResponse.success(data={"avatar": avatar_url})


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    """获取用户头像文件。"""
    from fastapi.responses import FileResponse

    file_path = AVATAR_DIR / filename
    if not file_path.exists():
        return HttpResponse.error(code=404, message="头像不存在")
    return FileResponse(file_path)
