"""FastAPI routes for cartoon video generation.

This router is used by the frontend to generate a HyperFrames-based animated
teaching video for a learning-path node.

The request is intentionally aligned with CartoonVideoRequest:
    style / depth / pace / visuals

Deprecated parameters such as voice, focus and video_length_seconds are removed.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.infra.models import User
from app.infra.response import HttpResponse
from app.shared.cartoon.service import CartoonService

router = APIRouter()


class PathCartoonRequest(BaseModel):
    learning_need: str = Field(
        min_length=1,
        description="学习需求或要讲解的高校计算机理论知识点",
    )
    path_id: str = Field(min_length=1, description="学习路径的唯一标识")
    node_id: str = Field(min_length=1, description="路径中具体节点/步骤的唯一标识")
    style: Literal["diagram", "minimal", "dark_tech", "chalkboard"] = "diagram"
    depth: Literal["overview", "standard", "deep"] = "standard"
    pace: Literal["fast", "normal", "slow"] = "normal"
    visuals: Literal["clean", "balanced", "detailed"] = "balanced"


@router.post("/path", summary="为学习路径节点生成计算机理论知识动画讲解视频")
async def generate_path_cartoon(
    req: PathCartoonRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """为路径规划模块生成 HyperFrames 动画 HTML 和 MP4 视频。

    输出目录：
        static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/

    生成目标：
        面向高校计算机本科理论课程，优先展示机制变化过程，
        例如状态转移、表格变换、结构构建、数据流动、调度时间线。
    """
    service = CartoonService()
    result = await service.generate_path_video(
        username=current_user.username,
        path_id=req.path_id,
        node_id=req.node_id,
        learning_need=req.learning_need,
        style=req.style,
        depth=req.depth,
        pace=req.pace,
        visuals=req.visuals,
        user_id=current_user.id,
    )
    return HttpResponse.success(data=result)