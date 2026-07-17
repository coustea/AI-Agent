"""Explicit, answer-grounded chat video tasks.

Video rendering is deliberately outside TutorAgent's tool loop: a learner first
receives an answer and explicitly asks to turn that answer into a video.  The
background task then derives a compact teaching brief from the persisted turn
and hands it to the Cartoon pipeline through the project's ToolExcute boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlmodel import select

from app.chat.memory.types import extract_content_text
from app.config import static_url, user_chat_video_dir
from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatAttachmentAnalysis, ChatMessage, ChatSession
from app.infra.prompts import prompts
from app.infra.tool_excute import Tool, ToolExcute
from app.profile.service import get_profile_service
from app.shared.cartoon import (
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonPipeline,
)
from app.shared.cartoon.models import LessonDepth

logger = get_logger(__name__)


class GenerateChatVideoArgs(BaseModel):
    """Arguments accepted by the explicit video execution tool."""

    assistant_message_id: int = Field(gt=0)


class ChatVideoBriefDraft(BaseModel):
    """Small LLM-facing contract; visual planning remains Cartoon-owned."""

    model_config = ConfigDict(extra="forbid")

    title: str
    learning_need: str
    knowledge_points: list[str] = Field(max_length=30)

    @field_validator("title", "learning_need")
    @classmethod
    def require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("brief text must not be blank")
        return normalized

    @field_validator("knowledge_points")
    @classmethod
    def normalize_points(cls, value: list[str]) -> list[str]:
        points: list[str] = []
        for item in value:
            normalized = item.strip()
            if normalized and normalized not in points:
                points.append(normalized)
        return points

    @model_validator(mode="after")
    def require_points(self) -> "ChatVideoBriefDraft":
        if not self.knowledge_points:
            raise ValueError("knowledge_points must contain at least one point")
        return self


@dataclass(frozen=True)
class _VideoSource:
    assistant_message_id: int
    user_message_id: int
    question: str
    answer: str
    attachment_analyses: tuple[str, ...]


class ChatVideoService:
    """Persist and execute a video task anchored to a completed assistant answer."""

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

        async def generate_chat_video(assistant_message_id: int) -> dict[str, Any]:
            brief = await self._build_cartoon_brief(
                user_id=user_id,
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
            return {
                "title": artifact.title,
                "video_url": static_url(artifact.video_path),
                "preview_url": static_url(artifact.html_path),
                "captions_url": static_url(artifact.caption_path),
                "duration_seconds": round(artifact.duration_ms / 1_000, 2),
                "scene_count": artifact.scene_count,
                "brief": brief.model_dump(),
            }

        executor = ToolExcute(tools=[
            Tool(
                name="generate_chat_video",
                description="Generate an educational cartoon video after an explicit user request.",
                args_model=GenerateChatVideoArgs,
                handler=generate_chat_video,
            ),
        ])
        try:
            result = await executor.execute({
                "id": task_id,
                "name": "generate_chat_video",
                "args": {"assistant_message_id": assistant_message_id},
            })
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
        session_id: str,
        assistant_message_id: int,
    ) -> "_ResolvedVideoBrief":
        source = await self._load_source(
            user_id=user_id,
            session_id=session_id,
            assistant_message_id=assistant_message_id,
        )
        profile_markdown = await self._load_profile_markdown(user_id)
        payload = {
            "student_question": source.question,
            "tutor_answer": source.answer,
            "attachment_analyses": list(source.attachment_analyses),
            "learner_profile": profile_markdown or None,
        }
        draft = await get_llm().ainvoke_json(
            ChatVideoBriefDraft,
            [
                SystemMessage(content=prompts.get("chat").get("video_brief")),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ],
            temperature=0.2,
        )
        return _ResolvedVideoBrief(
            title=draft.title,
            learning_need=draft.learning_need,
            knowledge_points=draft.knowledge_points,
            source_materials=tuple(self._source_materials(source, profile_markdown)),
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
            answer = extract_content_text(assistant.content).strip()
            if not question or not answer:
                raise ValueError("只有完整问答才能生成讲解视频")

            analyses = list((await db.exec(
                select(ChatAttachmentAnalysis).where(
                    ChatAttachmentAnalysis.user_message_id == question_message.id,
                    ChatAttachmentAnalysis.status == "completed",
                ).order_by(ChatAttachmentAnalysis.created_at.asc())
            )).all())
            return _VideoSource(
                assistant_message_id=assistant_message_id,
                user_message_id=question_message.id,
                question=question,
                answer=answer,
                attachment_analyses=tuple(
                    str(item.content or "").strip()
                    for item in analyses
                    if str(item.content or "").strip()
                ),
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

    @staticmethod
    def _source_materials(source: _VideoSource, profile_markdown: str) -> list[str]:
        materials = [
            f"学生问题：\n{source.question}",
            f"导师回答：\n{source.answer}",
        ]
        if source.attachment_analyses:
            materials.append("附件分析：\n" + "\n\n".join(source.attachment_analyses))
        if profile_markdown:
            materials.append(f"学习者画像（仅用于调整教学表达）：\n{profile_markdown}")
        return materials

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
