"""Explicit chat-video tasks executed outside the TutorAgent loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from sqlmodel import select

from app.chat.memory.types import extract_content_text
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import static_url, user_chat_video_dir
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession
from app.profile.service import get_profile_service
from app.shared.cartoon import (
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonPipeline,
)
from app.shared.cartoon.models import LessonDepth

logger = get_logger(__name__)


@dataclass(frozen=True)
class _VideoSource:
    assistant_message_id: int
    user_message_id: int
    question: str
    image_urls: tuple[str, ...]
    document_urls: tuple[str, ...]


class ChatVideoService:
    """Persist and execute an explicit video task anchored to a user request."""

    def __init__(self, *, pipeline: CartoonPipeline | None = None) -> None:
        self._pipeline = pipeline or CartoonPipeline()

    async def create_task(
        self,
        *,
        user_id: int,
        session_id: str,
        assistant_message_id: int,
    ) -> dict[str, Any]:
        source = await self._load_source(
            user_id=user_id,
            session_id=session_id,
            assistant_message_id=assistant_message_id,
        )
        task_id = self._task_id(source.assistant_message_id)
        video = {
            "task_id": task_id,
            "status": "queued",
            "topic": source.question,
            "source_user_message_id": source.user_message_id,
        }
        await self._set_video_state(
            user_id=user_id,
            session_id=session_id,
            assistant_message_id=source.assistant_message_id,
            video=video,
            reject_existing=True,
        )
        return {
            "assistant_message_id": source.assistant_message_id,
            "session_id": session_id,
            "video": video,
        }

    async def run_task(
        self,
        *,
        user_id: int,
        username: str,
        session_id: str,
        assistant_message_id: int,
    ) -> None:
        task_id = self._task_id(assistant_message_id)
        await self._set_video_state(
            user_id=user_id,
            session_id=session_id,
            assistant_message_id=assistant_message_id,
            video={"task_id": task_id, "status": "running"},
        )

        try:
            brief = await self._build_cartoon_brief(
                user_id=user_id,
                username=username,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
            )
            await self._set_video_state(
                user_id=user_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
                video={
                    "task_id": task_id,
                    "status": "running",
                    "topic": brief.learning_need,
                    "title": brief.title,
                    "brief": brief.model_dump(),
                },
            )
            artifact = await self._pipeline.generate(
                CartoonBrief(
                    learning_need=brief.learning_need,
                    instruction_context={
                        "entry": "chat",
                        "source_assistant_message_id": assistant_message_id,
                        "teaching_goal": brief.learning_need,
                    },
                    source_materials=brief.source_materials,
                    knowledge_points=brief.knowledge_points,
                    configuration=CartoonGenerationConfig(lesson_depth=LessonDepth.FOCUSED),
                ),
                user_chat_video_dir(username, session_id, assistant_message_id),
            )
            result = {
                "title": artifact.title,
                "video_url": static_url(artifact.video_path),
                "preview_url": static_url(artifact.html_path),
                "captions_url": static_url(artifact.caption_path),
                "duration_seconds": round(artifact.duration_ms / 1_000, 2),
                "scene_count": artifact.scene_count,
                "brief": brief.model_dump(),
            }
        except Exception:
            logger.exception("[ChatVideo] 生成失败: assistant_message_id=%s", assistant_message_id)
            await self._set_video_state(
                user_id=user_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
                video={
                    "task_id": task_id,
                    "status": "failed",
                    "error": "视频生成失败，请重新发起请求。",
                },
            )
            raise

        await self._set_video_state(
            user_id=user_id,
            session_id=session_id,
            assistant_message_id=assistant_message_id,
            video={"task_id": task_id, "status": "completed", **result},
        )

    async def get_task(
        self,
        *,
        user_id: int,
        session_id: str,
        assistant_message_id: int,
    ) -> dict[str, Any] | None:
        async with session_scope() as db:
            message = await self._get_owned_assistant_message(
                db,
                user_id=user_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
            )
            if message is None or not isinstance(message.usage_metadata, dict):
                return None
            video = message.usage_metadata.get("video")
            return dict(video) if isinstance(video, dict) else None

    async def _build_cartoon_brief(
        self,
        *,
        user_id: int,
        username: str,
        session_id: str,
        assistant_message_id: int,
    ) -> "_ResolvedVideoBrief":
        source = await self._load_source(
            user_id=user_id,
            session_id=session_id,
            assistant_message_id=assistant_message_id,
        )
        profile_markdown, attachment_materials = await asyncio.gather(
            self._load_profile_markdown(user_id),
            self._load_attachment_materials(source, username),
        )
        learning_need = source.question.strip()[:500]
        return _ResolvedVideoBrief(
            title=self._title_from_question(learning_need),
            learning_need=learning_need,
            knowledge_points=[learning_need],
            source_materials=tuple(self._source_materials(
                source,
                profile_markdown,
                attachment_materials,
            )),
        )

    async def _load_source(
        self,
        *,
        user_id: int,
        session_id: str,
        assistant_message_id: int,
    ) -> _VideoSource:
        async with session_scope() as db:
            assistant = await self._get_owned_assistant_message(
                db,
                user_id=user_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
            )
            if assistant is None:
                raise ValueError("回答不存在或无权限")
            if assistant.user_message_id is None:
                raise ValueError("该回答没有可追溯的用户问题")

            question_message = (await db.exec(
                select(ChatMessage).where(
                    ChatMessage.id == assistant.user_message_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "user",
                )
            )).first()
            if question_message is None or question_message.id is None:
                raise ValueError("原始用户问题不存在")

            question = extract_content_text(question_message.content).strip()
            if not question or (assistant.usage_metadata or {}).get("response_mode") != "video":
                raise ValueError("视频任务来源无效")

            image_urls: list[str] = []
            document_urls: list[str] = []
            for part in question_message.content if isinstance(question_message.content, list) else []:
                if not isinstance(part, dict):
                    continue
                url = str(part.get("url") or "").strip()
                if not url:
                    continue
                if part.get("type") == "image_url":
                    image_urls.append(url)
                elif part.get("type") == "file":
                    document_urls.append(url)
            return _VideoSource(
                assistant_message_id=assistant_message_id,
                user_message_id=question_message.id,
                question=question,
                image_urls=tuple(image_urls),
                document_urls=tuple(document_urls),
            )

    async def _set_video_state(
        self,
        *,
        user_id: int,
        session_id: str,
        assistant_message_id: int,
        video: dict[str, Any],
        reject_existing: bool = False,
    ) -> None:
        async with session_scope() as db:
            message = await self._get_owned_assistant_message(
                db,
                user_id=user_id,
                session_id=session_id,
                assistant_message_id=assistant_message_id,
            )
            if message is None:
                raise ValueError("视频源回答不存在或无权限")
            metadata = dict(message.usage_metadata or {})
            if reject_existing and isinstance(metadata.get("video"), dict):
                raise ValueError("该回答的视频任务已经创建")
            metadata["video"] = video
            message.usage_metadata = metadata
            db.add(message)
            await db.commit()

    @staticmethod
    async def _get_owned_assistant_message(
        db: Any,
        *,
        user_id: int,
        session_id: str,
        assistant_message_id: int,
    ) -> ChatMessage | None:
        return (await db.exec(
            select(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(
                ChatMessage.id == assistant_message_id,
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatSession.user_id == user_id,
            )
        )).first()

    @staticmethod
    async def _load_profile_markdown(user_id: int) -> str:
        try:
            return (await get_profile_service().build_profile_markdown(user_id=user_id)).strip()
        except Exception as exc:
            logger.warning("[ChatVideo] 读取学习者画像失败: %s", exc)
            return ""

    async def _load_attachment_materials(
        self,
        source: _VideoSource,
        username: str,
    ) -> list[str]:
        """Read this request's attachments without routing video through TutorAgent."""
        materials: list[str] = []
        if source.document_urls:
            try:
                documents = await analyze_documents(
                    current_username=username,
                    file_urls=list(source.document_urls[:5]),
                    question=source.question,
                )
                analysis_text = str(documents.get("analysis_text") or "").strip()
                if documents.get("success") and analysis_text:
                    materials.append(f"附件文档：\n{analysis_text}")
            except Exception as exc:
                logger.warning("[ChatVideo] 文档附件读取失败: %s", exc)

        if source.image_urls:
            try:
                vision = await VisionService().analyze_images(
                    list(source.image_urls[:5]),
                    f"请提取这些图片中与用户视频需求相关的文字、图表和知识点：{source.question}",
                )
                analysis_text = str(vision.get("analysis_text") or "").strip()
                if analysis_text:
                    materials.append(f"图片附件：\n{analysis_text}")
            except Exception as exc:
                logger.warning("[ChatVideo] 图片附件分析失败: %s", exc)
        return materials

    @staticmethod
    def _source_materials(
        source: _VideoSource,
        profile_markdown: str,
        attachment_materials: list[str],
    ) -> list[str]:
        materials = [
            f"学生问题：\n{source.question}",
        ]
        materials.extend(attachment_materials)
        if profile_markdown:
            materials.append(f"学习者画像（仅用于调整教学表达）：\n{profile_markdown}")
        return materials

    @staticmethod
    def _title_from_question(question: str) -> str:
        normalized = " ".join(question.split()).strip("？?。！! ")
        if not normalized:
            return "动画讲解"
        return normalized[:56] + ("…" if len(normalized) > 56 else "")

    @staticmethod
    def _task_id(assistant_message_id: int) -> str:
        return f"chat-video-{assistant_message_id}"


@dataclass(frozen=True)
class _ResolvedVideoBrief:
    title: str
    learning_need: str
    knowledge_points: list[str]
    source_materials: tuple[str, ...]

    def model_dump(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "learning_need": self.learning_need,
            "knowledge_points": self.knowledge_points,
        }


_chat_video_service: ChatVideoService | None = None


def get_chat_video_service() -> ChatVideoService:
    global _chat_video_service
    if _chat_video_service is None:
        _chat_video_service = ChatVideoService()
    return _chat_video_service
