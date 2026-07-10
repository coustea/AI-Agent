"""HTTP API for theory animation video generation."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.infra.logging import get_logger
from app.shared.cartoon import CartoonGenerationError
from app.shared.cartoon.service import CartoonVideoService

logger = get_logger(__name__)

router = APIRouter(tags=["cartoon-video"])
service = CartoonVideoService()


class CartoonGeneratePayload(BaseModel):
    learning_need: str = Field(min_length=1, description="用户要讲解的计算机理论知识点或学习问题")
    profile: dict[str, Any] = Field(default_factory=dict, description="用户画像或学习偏好")
    duration: int | None = Field(default=None, ge=60, le=420, description="目标视频时长，单位秒")
    render_mp4: bool = Field(default=True, description="是否立即渲染 MP4；false 时只生成 HTML 预览")


class CartoonGenerateResult(BaseModel):
    task_id: str
    title: str
    duration: float
    scene_count: int
    markdown_url: str
    html_url: str
    video_url: str | None
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
            render_mp4=payload.render_mp4,
        )
    except CartoonGenerationError as exc:
        logger.warning("Cartoon video 生成失败: task_id=%s error=%s", task_id, exc)
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "problems": exc.audit.problems if exc.audit else [],
            },
        ) from exc
    except Exception as exc:
        logger.exception("Cartoon video 生成异常: task_id=%s", task_id)
        raise HTTPException(status_code=500, detail=f"理论动画视频生成失败: {exc}") from exc

    return CartoonGenerateResult(
        task_id=task_id,
        title=result.title,
        duration=result.duration,
        scene_count=result.scene_count,
        markdown_url=f"/api/v1/ai/cartoon/{task_id}/markdown",
        html_url=f"/api/v1/ai/cartoon/{task_id}/html",
        video_url=f"/api/v1/ai/cartoon/{task_id}/video" if result.video_path else None,
        audit_url=f"/api/v1/ai/cartoon/{task_id}/audit",
    )


@router.get("/{task_id}/markdown")
async def get_theory_markdown(task_id: str) -> FileResponse:
    path = service.resolve_markdown(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Markdown 文件不存在")
    return FileResponse(path=path, filename="theory_video.md", media_type="text/markdown; charset=utf-8")


@router.get("/{task_id}/html")
async def get_theory_html(task_id: str) -> FileResponse:
    path = service.resolve_html(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="HTML 文件不存在")
    return FileResponse(path=path, filename="index.html", media_type="text/html; charset=utf-8")


@router.get("/{task_id}/video")
async def get_theory_video(task_id: str) -> FileResponse:
    path = service.resolve_video(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="视频文件不存在；可能本次生成设置了 render_mp4=false")
    return FileResponse(path=path, filename=path.name, media_type="video/mp4")


@router.get("/{task_id}/audit")
async def get_theory_audit(task_id: str) -> dict[str, Any]:
    path = service.resolve_audit(task_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audit 文件不存在")
    return json.loads(path.read_text(encoding="utf-8"))