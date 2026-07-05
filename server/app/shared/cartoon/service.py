"""动画服务 — 处理视频生成的内部 Python 调用。

提供 CartoonService 类，封装 CartoonPipeline 供不同模块
（path、resource、chat）使用，提供简化接口和一致的输出目录管理。

Callers: app/shared/cartoon/api.py (PathCartoonRequest route)
Schema: CartoonVideoRequest (style/depth/pace/visuals, no voice/video_length_seconds/focus)
User instruction: "审核代码，删除旧代码和多余冗余的代码" — remove stale voice/video_length_seconds/focus params
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.config import (
    user_path_node_cartoon_dir,
    user_resource_cartoon_dir,
    user_chat_videos_dir,
    resource_cartoon_url,
    path_node_cartoon_url,
    chat_video_url,
)
from app.shared.cartoon.pipeline import CartoonPipeline
from app.shared.cartoon.schemas import CartoonVideoRequest


StyleOption = Literal["diagram", "minimal", "dark_tech", "chalkboard"]
DepthOption = Literal["overview", "standard", "deep"]
PaceOption = Literal["fast", "normal", "slow"]
VisualsOption = Literal["clean", "balanced", "detailed"]


class CartoonService:
    """处理 HyperFrames 动画内部生成的服务。"""

    def __init__(self, pipeline: CartoonPipeline | None = None) -> None:
        self.pipeline = pipeline or CartoonPipeline()

    async def generate_path_video(
        self,
        *,
        username: str,
        path_id: str,
        node_id: str,
        learning_need: str,
        style: StyleOption = "diagram",
        depth: DepthOption = "standard",
        pace: PaceOption = "normal",
        visuals: VisualsOption = "balanced",
        profile: dict[str, Any] | str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Path | str | float]:
        """为学习路径节点生成动画视频。

        输出目录: static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/
        """
        output_dir = user_path_node_cartoon_dir(username, path_id, node_id)

        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=profile or f"用户 {user_id or 0} 学习路径 {path_id} 节点 {node_id}",
            style=style,
            depth=depth,
            pace=pace,
            visuals=visuals,
            output_dir=output_dir,
        )

        artifact = await self.pipeline.generate(req)

        return {
            "title": artifact.brief.title,
            "subject": artifact.brief.subject,
            "total_duration": artifact.brief.total_duration,
            "html_url": path_node_cartoon_url(username, path_id, node_id, "index.html"),
            "video_url": path_node_cartoon_url(username, path_id, node_id, "video.mp4"),
            "html_path": output_dir / "index.html",
            "video_path": artifact.video_path,
        }

    async def generate_resource_video(
        self,
        *,
        username: str,
        resource_id: str,
        learning_need: str,
        style: StyleOption = "diagram",
        depth: DepthOption = "standard",
        pace: PaceOption = "normal",
        visuals: VisualsOption = "balanced",
        profile: dict[str, Any] | str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Path | str | float]:
        """为多智能体资源包生成动画视频。

        输出目录: static/{username}/resources/{resource_id}/cartoon/
        """
        output_dir = user_resource_cartoon_dir(username, resource_id)

        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=profile or f"用户 {user_id or 0} 生成资源 {resource_id}",
            style=style,
            depth=depth,
            pace=pace,
            visuals=visuals,
            output_dir=output_dir,
        )

        artifact = await self.pipeline.generate(req)

        return {
            "title": artifact.brief.title,
            "subject": artifact.brief.subject,
            "total_duration": artifact.brief.total_duration,
            "html_url": resource_cartoon_url(username, resource_id, "index.html"),
            "video_url": resource_cartoon_url(username, resource_id, "video.mp4"),
            "html_path": output_dir / "index.html",
            "video_path": artifact.video_path,
        }

    async def generate_chat_video(
        self,
        *,
        username: str,
        session_id: str,
        message_id: str,
        learning_need: str,
        style: StyleOption = "diagram",
        depth: DepthOption = "standard",
        pace: PaceOption = "normal",
        visuals: VisualsOption = "balanced",
        profile: dict[str, Any] | str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Path | str | float]:
        """在聊天机器人辅导对话中内联生成动画视频。

        输出目录: static/{username}/chat/{session_id}/videos/{message_id}/
        """
        output_dir = user_chat_videos_dir(username, session_id, message_id)

        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=profile or f"用户 {user_id or 0} 在会话 {session_id} 消息 {message_id}",
            style=style,
            depth=depth,
            pace=pace,
            visuals=visuals,
            output_dir=output_dir,
        )

        artifact = await self.pipeline.generate(req)

        return {
            "title": artifact.brief.title,
            "subject": artifact.brief.subject,
            "total_duration": artifact.brief.total_duration,
            "html_url": f"/static/{username}/chat/{session_id}/videos/{message_id}/index.html",
            "video_url": chat_video_url(username, session_id, message_id),
            "html_path": output_dir / "index.html",
            "video_path": artifact.video_path,
        }
