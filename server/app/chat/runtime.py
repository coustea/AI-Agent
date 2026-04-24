"""Runtime preparation helpers for TutorAgent chat turns."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol

from langchain_core.messages import AnyMessage

from app.chat.schemas import TutorState

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


class TutorContextService(Protocol):
    async def build_profile_context(self, user_id: int) -> str:
        ...

    async def build_long_term_memory_context(self, user_id: int) -> str:
        ...

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str],
        file_urls: list[str],
    ) -> tuple[list[AnyMessage], str]:
        ...

    @staticmethod
    def build_file_context(image_urls: list[str], file_urls: list[str]) -> str:
        ...


@dataclass(frozen=True)
class UserMessageRecord:
    content: str
    attachments_json: str | None


@dataclass(frozen=True)
class PreparedTutorTurn:
    session_id: str
    image_urls: list[str]
    file_urls: list[str]
    user_record: UserMessageRecord
    initial_state: TutorState


def resolve_session_id(user_id: int, session_id: str | None) -> str:
    return session_id or f"user-{user_id}-default-mentor"


def build_user_message_record(
    user_message: str,
    *,
    image_urls: list[str],
    file_urls: list[str],
) -> UserMessageRecord:
    content = user_message
    if image_urls:
        content += f" [Attached Images: {', '.join(image_urls)}]"
    if file_urls:
        content += f" [Attached Files: {', '.join(file_urls)}]"

    urls = image_urls + file_urls
    if not urls:
        return UserMessageRecord(content=content, attachments_json=None)

    attachments = [
        {
            "url": url,
            "type": "image" if _is_image_url(url) else "document",
            "name": url.split("/")[-1],
        }
        for url in urls
    ]
    return UserMessageRecord(
        content=content,
        attachments_json=json.dumps(attachments, ensure_ascii=False),
    )


async def prepare_tutor_turn(
    *,
    ctx_service: TutorContextService,
    prompts: dict[str, str],
    user_id: int,
    user_message: str,
    session_id: str | None,
    image_urls: list[str] | None,
    file_urls: list[str] | None,
    enable_search: bool,
    attachment_analysis: dict[str, Any] | None,
) -> PreparedTutorTurn:
    effective_session = resolve_session_id(user_id, session_id)
    normalized_image_urls = image_urls or []
    normalized_file_urls = file_urls or []

    user_record = build_user_message_record(
        user_message,
        image_urls=normalized_image_urls,
        file_urls=normalized_file_urls,
    )

    profile_str, fact_str = await asyncio.gather(
        ctx_service.build_profile_context(user_id),
        ctx_service.build_long_term_memory_context(user_id),
    )
    file_info_str = ctx_service.build_file_context(normalized_image_urls, normalized_file_urls)
    attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()
    initial_messages, recent_chat_context = await ctx_service.build_recent_chat_context(
        user_id=user_id,
        session_id=effective_session,
        user_message=user_message,
        image_urls=normalized_image_urls,
        file_urls=normalized_file_urls,
    )

    analysis_hint = (
        f"\n\n### 附件并行预分析结果\n{attachment_analysis_context}\n"
        if attachment_analysis_context
        else ""
    )
    system_prompt = prompts["direct_system"].format(
        profile_context=profile_str,
        fact_context=fact_str,
        recent_chat_context=recent_chat_context,
    ) + analysis_hint

    initial_state: TutorState = {
        "user_id": user_id,
        "session_id": effective_session,
        "image_urls": normalized_image_urls,
        "file_urls": normalized_file_urls,
        "resource_mode": "none",
        "enable_search": bool(enable_search),
        "route": "",
        "execution_mode": "",
        "profile_context": profile_str,
        "fact_context": fact_str,
        "recent_chat_context": recent_chat_context,
        "file_context": file_info_str,
        "attachment_analysis_context": attachment_analysis_context,
        "attachment_analysis": attachment_analysis or {},
        "system_prompt": system_prompt,
        "messages": initial_messages,
        "answer_text": "",
        "retrieved_docs": [],
        "termination_reason": "",
    }

    return PreparedTutorTurn(
        session_id=effective_session,
        image_urls=normalized_image_urls,
        file_urls=normalized_file_urls,
        user_record=user_record,
        initial_state=initial_state,
    )


def _is_image_url(url: str) -> bool:
    suffix = url.rsplit(".", 1)[-1].lower() if "." in url else ""
    return suffix in IMAGE_EXTENSIONS
