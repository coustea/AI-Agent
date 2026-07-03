"""FastAPI routes for cartoon video generation (frontend-facing path planning node endpoint)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.infra.models import User
from app.infra.response import HttpResponse
from app.shared.cartoon.service import CartoonService

router = APIRouter()


class PathCartoonRequest(BaseModel):
    learning_need: str = Field(min_length=1, description="学习需求或要讲解的知识点描述")
    path_id: str = Field(min_length=1, description="学习路径的唯一标识")
    node_id: str = Field(min_length=1, description="路径中具体节点/步骤的唯一标识")
    voice: str = Field(default="zh-CN-XiaoxiaoNeural", description="TTS 配音发音人")
    video_length_seconds: int = Field(default=30, ge=10, le=180, description="预期视频时长（秒）")
    style: Literal["diagram", "minimal", "dark_tech"] = "diagram"
    focus: Literal["concept", "process", "comparison", "practice"] = "concept"


@router.post("/path", summary="为学习路径节点生成讲解动画视频")
async def generate_path_cartoon(
    req: PathCartoonRequest,
    current_user: User = Depends(get_current_user),
):
    """为路径规划模块生成对应的 HyperFrames 动画 HTML 和 MP4 视频。
    
    保存目录：static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/
    """
    service = CartoonService()
    result = await service.generate_path_video(
        username=current_user.username,
        path_id=req.path_id,
        node_id=req.node_id,
        learning_need=req.learning_need,
        voice=req.voice,
        video_length_seconds=req.video_length_seconds,
        style=req.style,
        focus=req.focus,
        user_id=current_user.id,
    )
    return HttpResponse.success(data=result)
