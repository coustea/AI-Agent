from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import User
from app.path.schemas import CoursePathResponse, GeneratePathRequest
from app.path.service import CoursePathService
from app.utils.response import HttpResponse

router = APIRouter(prefix="/path-plan", tags=["AI Path Planning"])


@router.post("")
async def generate_path(
    request: GeneratePathRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    基于用户请求和当前的画像，生成全新的课程级别学习路径。
    """
    service = CoursePathService(session)
    path = await service.generate_path(user_id=current_user.id, request=request)
    return HttpResponse.success(data=path)


@router.get("")
async def get_active_path(
    module: str = "mentor",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    获取用户当前正在进行的活跃课程路径。如果不存在则返回 null。
    """
    service = CoursePathService(session)
    path = await service.get_active_path(user_id=current_user.id, module=module)
    return HttpResponse.success(data=path)
