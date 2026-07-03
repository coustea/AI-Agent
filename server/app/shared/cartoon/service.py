"""动画服务 — 处理视频生成的内部 Python 调用。

提供 CartoonService 类，封装 CartoonPipeline 供不同模块
（path、resource、chat）使用，提供简化接口和一致的输出目录管理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

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


class CartoonService:
    """处理 HyperFrames 动画内部生成的服务。

    提供模块特定的生成方法，处理输出目录设置并返回标准化的结果字典。

    Attributes:
        pipeline: 用于视频生成的 CartoonPipeline 实例。
    """

    def __init__(self, pipeline: CartoonPipeline | None = None) -> None:
        """初始化服务，支持可选的管道覆盖。

        Args:
            pipeline: CartoonPipeline 实例（默认：新实例）。
        """
        self.pipeline = pipeline or CartoonPipeline()

    async def generate_path_video(
        self,
        *,
        username: str,
        path_id: str,
        node_id: str,
        learning_need: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        video_length_seconds: int = 30,
        style: Literal["diagram", "minimal", "dark_tech"] = "diagram",
        focus: Literal["concept", "process", "comparison", "practice"] = "concept",
        user_id: int | None = None,
    ) -> dict[str, Path | str | float]:
        """为学习路径节点生成动画视频。

        输出目录: static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/

        Args:
            username: 用户名，用于文件路径划分。
            path_id: 学习路径标识符。
            node_id: 路径节点标识符。
            learning_need: 要解释的学习目标。
            voice: TTS 语音标识符。
            video_length_seconds: 目标时长（秒）。
            user_id: 可选的用户标识符，用于画像。

        Returns:
            包含 title、subject、duration、URLs 和 paths 的字典。
        """
        output_dir = user_path_node_cartoon_dir(username, path_id, node_id)

        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=f"用户 {user_id or 0} 学习路径 {path_id} 节点 {node_id}",
            video_length_seconds=video_length_seconds,
            voice=voice,
            style=style,
            focus=focus,
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
        voice: str = "zh-CN-XiaoxiaoNeural",
        video_length_seconds: int = 30,
        style: Literal["diagram", "minimal", "dark_tech"] = "diagram",
        focus: Literal["concept", "process", "comparison", "practice"] = "concept",
        user_id: int | None = None,
    ) -> dict[str, Path | str | float]:
        """为多智能体资源包生成动画视频。

        输出目录: static/{username}/resources/{resource_id}/cartoon/

        Args:
            username: 用户名，用于文件路径划分。
            resource_id: 资源标识符。
            learning_need: 要解释的学习目标。
            voice: TTS 语音标识符。
            video_length_seconds: 目标时长（秒）。
            user_id: 可选的用户标识符，用于画像。

        Returns:
            包含 title、subject、duration、URLs 和 paths 的字典。
        """
        output_dir = user_resource_cartoon_dir(username, resource_id)

        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=f"用户 {user_id or 0} 生成资源 {resource_id}",
            video_length_seconds=video_length_seconds,
            voice=voice,
            style=style,
            focus=focus,
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
        voice: str = "zh-CN-XiaoxiaoNeural",
        video_length_seconds: int = 30,
        style: Literal["diagram", "minimal", "dark_tech"] = "diagram",
        focus: Literal["concept", "process", "comparison", "practice"] = "concept",
        user_id: int | None = None,
    ) -> dict[str, Path | str | float]:
        """在聊天机器人辅导对话中内联生成动画视频。

        输出目录: static/{username}/chat/{session_id}/videos/{message_id}/

        Args:
            username: 用户名，用于文件路径划分。
            session_id: 聊天会话标识符。
            message_id: 聊天消息标识符。
            learning_need: 要解释的学习目标。
            voice: TTS 语音标识符。
            video_length_seconds: 目标时长（秒）。
            user_id: 可选的用户标识符，用于画像。

        Returns:
            包含 title、subject、duration、URLs 和 paths 的字典。
        """
        output_dir = user_chat_videos_dir(username, session_id, message_id)

        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=f"用户 {user_id or 0} 在会话 {session_id} 消息 {message_id}",
            video_length_seconds=video_length_seconds,
            voice=voice,
            style=style,
            focus=focus,
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
