"""Chat entry point for PPT generation."""
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field
from app.config import user_resource_ppt_dir
from app.shared.ppt.agent import PPTAgent, ProgressCallback
from app.shared.ppt.schemas import PPTBrief
from app.shared.tools.registry import Tool


class GeneratePPTArgs(BaseModel):
    topic: str = Field(min_length=2)
    learning_goal: str = Field(min_length=2)
    source_points: list[str] = Field(default_factory=list)


def build_ppt_tool(
    *,
    username: str = "anonymous",
    session_id: str | None = None,
    progress: ProgressCallback | None = None,
) -> Tool:
    """构造供对话等场景调用的 PPT 生成工具。"""

    async def generate(topic: str, learning_goal: str, source_points: list[str]) -> dict[str, Any]:
        """根据主题与要点在目标目录生成 PPT 课件产物。"""
        target = user_resource_ppt_dir(username, f"chat_{session_id}" if session_id else uuid4().hex)
        brief = PPTBrief(title=topic, context=learning_goal + "\n" + "\n".join(source_points))
        artifact = await PPTAgent().generate(brief, target, progress=progress)
        return {"status": "ok", "title": artifact.title, **artifact.metadata()}

    return Tool(
        name="generate_ppt_deck",
        description="生成可编辑的 PPTX 教学课件及逐页图片预览。",
        args_model=GeneratePPTArgs,
        handler=generate,
    )

