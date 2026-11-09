"""教学动画视频生成工具入口。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import user_resource_cartoon_dir
from app.infra.logging import get_logger
from app.shared.cartoon.agent import CartoonAgent, ProgressCallback
from app.shared.cartoon.schemas import CartoonBrief, CartoonGenerationConfig
from app.shared.tools.registry import Tool

logger = get_logger(__name__)


class GenerateVideoToolArgs(BaseModel):
    """教学动画视频生成工具入参模式。"""

    topic: str = Field(min_length=2, description="教学视频主题")
    learning_goal: str = Field(min_length=2, description="核心教学目标或需求说明")
    source_materials: list[str] = Field(default_factory=list, description="讲义要点或补充材料")
    voice: str = Field(default="teacher", description="旁白音色：teacher 或 coach")


def build_cartoon_tool(
    *,
    username: str = "anonymous",
    resource_id: str | None = None,
    session_id: str | None = None,
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> Tool:
    """构造供 chat、resource 等父智能体统一调用的 generate_teaching_video 工具。"""

    async def generate_teaching_video(
        topic: str,
        learning_goal: str,
        source_materials: list[str] | None = None,
        voice: str = "teacher",
    ) -> dict[str, Any]:
        """调用 CartoonAgent 生成教学动画视频并返回标准化产物元数据。"""
        res_key = resource_id or (f"chat_{session_id}" if session_id else uuid4().hex[:12])
        target_dir = output_dir or user_resource_cartoon_dir(username, res_key)
        voice_val = "coach" if voice == "coach" else "teacher"
        logger.info(
            "[CartoonTool] 收到视频生成请求: topic=%s user=%s voice=%s target=%s",
            topic, username, voice_val, target_dir,
        )
        brief = CartoonBrief(
            title=topic,
            learning_need=learning_goal,
            source_materials=list(source_materials or [learning_goal])[:8],
            configuration=CartoonGenerationConfig(voice=voice_val),
        )
        artifact = await CartoonAgent().generate(brief, target_dir, progress=progress)
        logger.info(
            "[CartoonTool] 视频交付: title=%s duration=%.1fs scenes=%d",
            artifact.title, artifact.duration_seconds, artifact.scene_count,
        )
        return {
            "status": "ok",
            "title": artifact.title,
            **artifact.metadata(),
        }

    return Tool(
        name="generate_teaching_video",
        description="生成 1080p 教学动画视频（含中文语音旁白与同步 WebVTT 字幕）。",
        args_model=GenerateVideoToolArgs,
        handler=generate_teaching_video,
    )


__all__ = ["GenerateVideoToolArgs", "build_cartoon_tool"]
