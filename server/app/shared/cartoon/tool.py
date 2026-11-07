"""视频生成的上层工具入口。"""
from pathlib import Path
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field
from app.config import static_url, user_resource_cartoon_dir
from app.shared.cartoon.agent import ProgressCallback, generate
from app.shared.cartoon.schemas import CartoonBrief, CartoonGenerationConfig, CartoonInput
from app.shared.tools.registry import Tool


class GenerateVideoToolArgs(BaseModel):
    topic: str = Field(min_length=2)
    learning_goal: str = Field(min_length=2)
    source_materials: list[str] = Field(default_factory=list)
    voice: str = "teacher"


def build_cartoon_subagent_tool(
    *,
    username: str = "anonymous",
    resource_id: str | None = None,
    session_id: str | None = None,
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> Tool:
    """构造供 chat、resource 等父智能体统一调用的 generate_teaching_video 工具。"""

    async def _run(
        topic: str,
        learning_goal: str,
        source_materials: list[str] | None = None,
        voice: str = "teacher",
    ) -> dict[str, Any]:
        """生成教学动画视频并返回标准化结果字典。"""
        res_key = resource_id or (f"chat_{session_id}" if session_id else uuid4().hex[:12])
        target_dir = output_dir or user_resource_cartoon_dir(username, res_key)
        voice_val = "coach" if voice == "coach" else "teacher"
        brief = CartoonBrief(
            learning_need=f"{topic}：{learning_goal}",
            instruction_context={"topic": topic, "learning_goal": learning_goal},
            source_materials=list(source_materials or [learning_goal])[:8],
            configuration=CartoonGenerationConfig(voice=voice_val),  # type: ignore[arg-type]
        )
        artifact = await generate(CartoonInput(output_dir=target_dir, brief=brief), progress=progress)
        return {
            "status": "ok",
            "title": artifact.title,
            "scene_count": artifact.scene_count,
            "duration_seconds": round(artifact.duration_ms / 1000.0, 2),
            "video_url": static_url(artifact.video_path),
            "preview_url": static_url(artifact.html_path),
            "captions_url": static_url(artifact.caption_path),
        }

    return Tool(
        name="generate_teaching_video",
        description=(
            "Invoke the specialized cartoon video agent (HyperFrames CLI + TTS) "
            "to generate a 1920x1080 narrated MP4 teaching video with synchronized captions."
        ),
        args_model=GenerateVideoToolArgs,
        handler=_run,
    )
