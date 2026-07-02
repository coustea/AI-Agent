"""Cartoon Service — handles internal Python calls for video generation."""

from __future__ import annotations

from pathlib import Path
from app.config import WORKPLACE_DIR
from app.shared.cartoon.pipeline import CartoonPipeline
from app.shared.cartoon.schemas import CartoonVideoRequest


class CartoonService:
    """Service to handle internal generation of HyperFrames cartoons across modules."""

    def __init__(self, pipeline: CartoonPipeline | None = None) -> None:
        self.pipeline = pipeline or CartoonPipeline()

    async def generate_path_video(
        self,
        *,
        path_id: str,
        node_id: str,
        learning_need: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        video_length_seconds: int = 30,
        user_id: int | None = None,
    ) -> dict:
        """Generate a cartoon video for a learning path node.

        Saves to: static/path/{path_id}/{node_id}/
        """
        output_dir = WORKPLACE_DIR / "path" / path_id / node_id
        
        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=f"User {user_id or 0} learning path {path_id} node {node_id}",
            video_length_seconds=video_length_seconds,
            voice=voice,
            output_dir=output_dir,
        )
        
        artifact = await self.pipeline.generate(req)
        
        return {
            "title": artifact.brief.title,
            "subject": artifact.brief.subject,
            "total_duration": artifact.brief.total_duration,
            "html_url": f"/static/path/{path_id}/{node_id}/index.html",
            "video_url": f"/static/path/{path_id}/{node_id}/video.mp4",
            "html_path": output_dir / "index.html",
            "video_path": artifact.video_path,
        }

    async def generate_resource_video(
        self,
        *,
        resource_id: str,
        learning_need: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        video_length_seconds: int = 30,
        user_id: int | None = None,
    ) -> dict:
        """Generate a cartoon video for a multi-agent learning resource bundle.

        Saves to: static/resource/{resource_id}/
        """
        output_dir = WORKPLACE_DIR / "resource" / resource_id
        
        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=f"User {user_id or 0} generating resource {resource_id}",
            video_length_seconds=video_length_seconds,
            voice=voice,
            output_dir=output_dir,
        )
        
        artifact = await self.pipeline.generate(req)
        
        return {
            "title": artifact.brief.title,
            "subject": artifact.brief.subject,
            "total_duration": artifact.brief.total_duration,
            "html_url": f"/static/resource/{resource_id}/index.html",
            "video_url": f"/static/resource/{resource_id}/video.mp4",
            "html_path": output_dir / "index.html",
            "video_path": artifact.video_path,
        }

    async def generate_chat_video(
        self,
        *,
        session_id: str,
        message_id: str,
        learning_need: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        video_length_seconds: int = 30,
        user_id: int | None = None,
    ) -> dict:
        """Generate a cartoon video inline in a chatbot tutoring conversation.

        Saves to: static/chat/{session_id}/{message_id}/
        """
        output_dir = WORKPLACE_DIR / "chat" / session_id / message_id
        
        req = CartoonVideoRequest(
            learning_need=learning_need,
            profile=f"User {user_id or 0} in session {session_id} message {message_id}",
            video_length_seconds=video_length_seconds,
            voice=voice,
            output_dir=output_dir,
        )
        
        artifact = await self.pipeline.generate(req)
        
        return {
            "title": artifact.brief.title,
            "subject": artifact.brief.subject,
            "total_duration": artifact.brief.total_duration,
            "html_url": f"/static/chat/{session_id}/{message_id}/index.html",
            "video_url": f"/static/chat/{session_id}/{message_id}/video.mp4",
            "html_path": output_dir / "index.html",
            "video_path": artifact.video_path,
        }
