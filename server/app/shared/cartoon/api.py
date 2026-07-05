"""FastAPI routes for cartoon video generation (frontend-facing path planning node endpoint).

Callers: app/routes.py mounts this router
Schema: PathCartoonRequest aligned with CartoonVideoRequest (style/depth/pace/visuals)
User instruction: "审核代码，删除旧代码和多余冗余的代码" — remove stale voice/video_length_seconds/focus
"""

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
    style: Literal["diagram", "minimal", "dark_tech", "chalkboard"] = "diagram"
    depth: Literal["overview", "standard", "deep"] = "standard"
    pace: Literal["fast", "normal", "slow"] = "normal"
    visuals: Literal["clean", "balanced", "detailed"] = "balanced"


@router.post("/path", summary="为学习路径节点生成讲解动画视频")
async def generate_path_cartoon(
    req: PathCartoonRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """为路径规划模块生成对应的 HyperFrames 动画 HTML 和 MP4 视频。

    保存目录：static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/
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
