"""HTTP API for CartoonAgent video generation.

接口：
  POST /generate
  GET  /{task_id}/markdown
  GET  /{task_id}/html
  GET  /{task_id}/video
  GET  /{task_id}/audit

完整路径（通过 routes.py 挂载）：
  POST /api/v1/ai/cartoon/generate
  GET  /api/v1/ai/cartoon/{task_id}/markdown
  GET  /api/v1/ai/cartoon/{task_id}/html
  GET  /api/v1/ai/cartoon/{task_id}/video
  GET  /api/v1/ai/cartoon/{task_id}/audit
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.infra.logging import get_logger
from app.shared.cartoon.cartoon_agent import CartoonGenerationError
from app.shared.cartoon.service import CartoonVideoService

logger = get_logger(__name__)

router = APIRouter(tags=["cartoon-video"])
service = CartoonVideoService()


class CartoonGeneratePayload(BaseModel):
    learning_need: str = Field(min_length=1, description="用户要讲解的知识点或学习问题")
    profile: dict[str, Any] | str | None = Field(default=None, description="用户画像或学习偏好")
    duration: int | None = Field(default=None, ge=60, le=600, description="目标视频时长（秒）")


class CartoonGenerateResult(BaseModel):
    task_id: str
    title: str
    duration: float
    scene_count: int
    markdown_url: str
    html_url: str
    video_url: str
    audit_url: str


@router.post("/generate", response_model=CartoonGenerateResult)
async def generate_cartoon_video(payload: CartoonGeneratePayload) -> CartoonGenerateResult:
    task_id = uuid4().hex

    try:
        result = await service.generate(
            task_id=task_id,
            learning_need=payload.learning_need,
            profile=payload.profile,
            duration=payload.duration,
        )
    except CartoonGenerationError as exc:
        logger.warning("Cartoon 生成失败: task_id=%s error=%s", task_id, exc)
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "problems": exc.audit.problems if exc.audit else [],
            },
        ) from exc
    except Exception as exc:
        logger.exception("Cartoon 生成异常: task_id=%s", task_id)
        raise HTTPException(status_code=500, detail=f"动画视频生成失败: {exc}") from exc

    return CartoonGenerateResult(
        task_id=task_id,
        title=result.title,
        duration=result.duration,
        scene_count=result.scene_count,
        markdown_url=f"/api/v1/ai/cartoon/{task_id}/markdown",
        html_url=f"/api/v1/ai/cartoon/{task_id}/html",
        video_url=f"/api/v1/ai/cartoon/{task_id}/video",
        audit_url=f"/api/v1/ai/cartoon/{task_id}/audit",
    )


@router.get("/{task_id}/markdown")
async def get_cartoon_markdown(task_id: str) -> FileResponse:
    path = service.resolve_markdown(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Markdown 文件不存在")
    return FileResponse(
        path=path,
        filename="cartoon.md",
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/{task_id}/html")
async def get_cartoon_html(task_id: str) -> FileResponse:
    path = service.resolve_html(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="HTML 文件不存在")
    return FileResponse(
        path=path,
        filename="index.html",
        media_type="text/html; charset=utf-8",
    )


@router.get("/{task_id}/video")
async def get_cartoon_video(task_id: str) -> FileResponse:
    path = service.resolve_video(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    return FileResponse(
        path=path,
        filename=path.name,
        media_type="video/mp4",
    )


@router.get("/{task_id}/audit")
async def get_cartoon_audit(task_id: str) -> dict[str, Any]:
    path = service.resolve_audit(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audit 文件不存在")
    return json.loads(path.read_text(encoding="utf-8"))
