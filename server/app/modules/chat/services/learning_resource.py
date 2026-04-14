"""Shared service for learning resource generation."""

from __future__ import annotations

from app.core.logging import get_logger
from app.modules.resource.agents.content import content_writer
from app.services.memory import memory_service

logger = get_logger(__name__)


class LearningResourceService:
    """Generate learning resources that can be shared by chat and avatar modes."""

    async def _load_profile_dict(self, user_id: int) -> dict:
        profile = await memory_service.get_user_profile(user_id)
        if not profile:
            return {}
        return profile.model_dump(
            exclude_unset=True,
            exclude={"updated_at", "created_at", "id", "user_id"},
        )

    async def generate(
        self,
        current_user_id: int | None,
        resource_type: str,
        topic: str,
        course: str = "",
        gap: str = "",
        need: str = "review",
        reason: str = "",
        extra: str = "",
    ) -> dict:
        if current_user_id is None:
            return self._build_error_response(resource_type, "缺少当前用户上下文，无法生成资源。")

        normalized_type = (resource_type or "").strip().lower()
        user_profile = await self._load_profile_dict(current_user_id)
        shared_memory = {}

        logger.info(
            "[LearningResourceService] user=%s type=%s topic=%s",
            current_user_id,
            normalized_type,
            topic,
        )

        if normalized_type in {"document", "doc", "word", "markdown", "md"}:
            result = await content_writer.generate_content(
                topic=topic,
                course=course,
                gap=gap,
                user_profile=user_profile,
                shared_memory=shared_memory,
            )
            preview_text = (result.get("content") or "")[:1200]
            return {
                "success": bool(result.get("success")),
                "resource_type": "document",
                "title": "文档学习资源",
                "summary": f"已为“{topic}”生成学习总结文档。" if result.get("success") else f"未能为“{topic}”生成学习文档。",
                "preview_text": preview_text,
                "asset_urls": [],
                "file_path": result.get("file_path"),
                "error": result.get("error"),
            }

        return self._build_error_response(normalized_type, f"暂不支持的资源类型: {resource_type}")

    @staticmethod
    def _build_error_response(resource_type: str, error: str) -> dict:
        return {
            "success": False,
            "resource_type": resource_type,
            "title": "学习资源",
            "summary": "",
            "preview_text": "",
            "asset_urls": [],
            "file_path": None,
            "error": error,
        }


learning_resource_service = LearningResourceService()
