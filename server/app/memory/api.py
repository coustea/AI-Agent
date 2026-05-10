"""Memory HTTP routes — 记忆层 HTTP 路由。

模块职责：
- 暴露记忆层读取接口供前端使用
- 提供用户画像和聊天历史的查询端点
- 处理用户权限校验

端点列表：
- GET /profile - 获取当前用户画像
- GET /profile/history - 获取当前用户画像历史
- GET /long-term - 获取当前用户长期记忆
- GET /sessions/{session_id}/summaries - 获取会话概要
- GET /context-preview - 预览上下文
- POST /profile/rebuild - 手动重建画像
- POST /long-term/rebuild - 手动重建长期记忆
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.auth.security import get_current_user
from app.infra.models import User
from app.memory import MemoryLayer
from app.shared.response import HttpResponse

router = APIRouter()


class ProfileOnboardingUpdate(BaseModel):
    education_level: str = Field(..., min_length=1, max_length=50)
    grade: str = Field(..., min_length=1, max_length=50)
    major: str = Field(..., min_length=1, max_length=100)
    courses: list[str] = Field(..., min_length=1, max_length=20)
    learning_goal: str = Field(..., min_length=1, max_length=500)
    school: str | None = Field(default=None, max_length=100)
    school_level: str | None = Field(default=None, max_length=100)
    preferred_language: str | None = Field(default=None, max_length=50)

    @field_validator("education_level", "grade", "major", "learning_goal")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("字段不能为空")
        return text

    @field_validator("school", "school_level", "preferred_language")
    @classmethod
    def optional_text_is_trimmed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("courses")
    @classmethod
    def courses_must_include_non_empty_item(cls, value: list[str]) -> list[str]:
        courses = []
        seen = set()
        for item in value:
            course = str(item or "").strip()
            if not course or course in seen:
                continue
            seen.add(course)
            courses.append(course)
        if not courses:
            raise ValueError("至少填写一门正在学习的课程")
        return courses


def _assert_user_scope(current_user: User, user_id: int) -> None:
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权查看其他用户数据")


def _profile_payload(profile: Any) -> dict[str, Any]:
    if profile is None:
        return {
            "user_id": None,
            "module": None,
            "profile_json": None,
            "profile_score_json": None,
            "version": None,
            "confidence": None,
            "source_session_ids": None,
            "source_summary_ids": None,
            "source_event_ids": None,
            "updated_reason": None,
            "updated_at": None,
        }
    return {
        "user_id": profile.user_id,
        "module": profile.module,
        "profile_json": profile.profile_json,
        "profile_score_json": profile.profile_score_json,
        "version": profile.version,
        "confidence": profile.confidence,
        "source_session_ids": profile.source_session_ids,
        "source_summary_ids": profile.source_summary_ids,
        "source_event_ids": profile.source_event_ids,
        "updated_reason": profile.updated_reason,
        "updated_at": profile.updated_at,
    }


def _profile_onboarding_payload(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "student_profile": status.get("student_profile") or {},
        "profile_initialized": bool(status.get("profile_initialized")),
    }


def _profile_score_payload(profile: Any) -> dict[str, Any]:
    if profile is None:
        return {
            "user_id": None,
            "module": None,
            "version": None,
            "score": None,
            "confidence": None,
            "metrics": {},
            "missing_sections": [],
            "scored_at": None,
            "updated_at": None,
        }

    score_json = profile.profile_score_json or {}
    return {
        "user_id": profile.user_id,
        "module": profile.module,
        "version": profile.version,
        "score": score_json.get("overall_score"),
        "confidence": score_json.get("confidence", profile.confidence),
        "metrics": {
            "dimension_scores": score_json.get("dimension_scores") or {},
            "section_coverage": score_json.get("section_coverage"),
            "evidence_quality": score_json.get("evidence_quality"),
            "uncertainty_handling": score_json.get("uncertainty_handling"),
            "content_richness": score_json.get("content_richness"),
        },
        "missing_sections": score_json.get("missing_sections") or [],
        "scored_at": score_json.get("scored_at"),
        "updated_at": profile.updated_at,
    }


def _long_term_memory_payload(memory: Any) -> dict[str, Any]:
    if memory is None:
        return {
            "user_id": None,
            "module": None,
            "memory_markdown": None,
            "memory_json": None,
            "version": None,
            "confidence": None,
            "source_session_ids": None,
            "source_summary_ids": None,
            "updated_reason": None,
            "updated_at": None,
        }
    return {
        "user_id": memory.user_id,
        "module": memory.module,
        "memory_markdown": memory.memory_markdown,
        "memory_json": memory.memory_json,
        "version": memory.version,
        "confidence": memory.confidence,
        "source_session_ids": memory.source_session_ids,
        "source_summary_ids": memory.source_summary_ids,
        "updated_reason": memory.updated_reason,
        "updated_at": memory.updated_at,
    }


def _session_summary_payload(summary: Any) -> dict[str, Any]:
    return {
        "id": summary.id,
        "user_id": summary.user_id,
        "session_id": summary.session_id,
        "module": summary.module,
        "summary_markdown": summary.summary_markdown,
        "summary_json": summary.summary_json,
        "summary_type": summary.summary_type,
        "version": summary.version,
        "current_topic": summary.current_topic,
        "current_goal": summary.current_goal,
        "current_status": summary.current_status,
        "next_action": summary.next_action,
        "summarized_message_count": summary.summarized_message_count,
        "created_at": summary.created_at,
    }


def _profile_history_payload(history: Any) -> dict[str, Any]:
    return {
        "id": history.id,
        "user_id": history.user_id,
        "module": history.module,
        "version": history.version,
        "profile_json": history.profile_json,
        "profile_score_json": history.profile_score_json,
        "change_reason": history.change_reason,
        "source_session_ids": history.source_session_ids,
        "source_summary_ids": history.source_summary_ids,
        "source_event_ids": history.source_event_ids,
        "created_at": history.created_at,
    }


def _chat_message_payload(message: Any) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "attachments": message.attachments,
        "tool_calls": message.tool_calls,
        "diagram": message.diagram,
        "created_at": message.created_at,
    }


@router.get("/profile")
async def get_current_profile(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    profile = await memory_layer.get_profile(user_id=current_user.id)
    return HttpResponse.success(data=_profile_payload(profile))


@router.get("/profile/history")
async def get_current_profile_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    history = await memory_layer.list_profile_history(user_id=current_user.id, limit=limit)
    return HttpResponse.success(data=[_profile_history_payload(item) for item in history])


@router.get("/profile/score")
async def get_current_profile_score(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    profile = await memory_layer.get_profile(user_id=current_user.id)
    return HttpResponse.success(data=_profile_score_payload(profile))


@router.get("/profile/onboarding")
async def get_current_profile_onboarding(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    status = await memory_layer.get_onboarding(user_id=current_user.id)
    return HttpResponse.success(data=_profile_onboarding_payload(status))


@router.patch("/profile/onboarding")
async def update_current_profile_onboarding(
    data: ProfileOnboardingUpdate,
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    profile = await memory_layer.update_onboarding(
        user_id=current_user.id,
        student_profile=data.model_dump(),
    )
    return HttpResponse.success(
        data={
            "profile": _profile_payload(profile),
            "onboarding": _profile_onboarding_payload(
                await memory_layer.get_onboarding(user_id=current_user.id)
            ),
        }
    )


@router.get("/profile/{user_id}")
async def get_profile_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module="mentor")
    profile = await memory_layer.get_profile(user_id=user_id)
    return HttpResponse.success(data=_profile_payload(profile))


@router.get("/profile/{user_id}/score")
async def get_profile_score_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module="mentor")
    profile = await memory_layer.get_profile(user_id=user_id)
    return HttpResponse.success(data=_profile_score_payload(profile))


@router.get("/profile/{user_id}/history")
async def get_profile_history_by_user_id(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module="mentor")
    history = await memory_layer.list_profile_history(user_id=user_id, limit=limit)
    return HttpResponse.success(data=[_profile_history_payload(item) for item in history])


@router.get("/long-term")
async def get_long_term_memory(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    memory = await memory_layer.get_long_term_memory(user_id=current_user.id)
    return HttpResponse.success(data=_long_term_memory_payload(memory))


@router.get("/sessions/{session_id}/summaries")
async def get_session_summaries(
    session_id: str,
    limit: int = Query(default=3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    summaries = await memory_layer.get_session_summaries(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
    )
    return HttpResponse.success(data=[_session_summary_payload(s) for s in summaries])


@router.get("/recent-chat")
async def get_recent_chat(
    session_id: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    messages = await memory_layer.list_messages(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
    )
    dialogue_messages = [
        msg for msg in messages
        if msg.role in {"user", "assistant"} and msg.content.strip()
    ]
    return HttpResponse.success(data=[_chat_message_payload(msg) for msg in dialogue_messages])


@router.get("/context-preview")
async def get_context_preview(
    session_id: str = Query(..., min_length=1),
    recent_limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    context_markdown = await memory_layer.build_context_preview(
        user_id=current_user.id,
        session_id=session_id,
        recent_limit=recent_limit,
    )
    return HttpResponse.success(data={"context_markdown": context_markdown})


@router.post("/profile/rebuild")
async def rebuild_profile(
    session_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    success = await memory_layer.build_profile(user_id=current_user.id, session_id=session_id)
    return HttpResponse.success(data={"success": success})


@router.post("/long-term/rebuild")
async def rebuild_long_term_memory(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module="mentor")
    memory = await memory_layer.get_or_create_long_term_memory(user_id=current_user.id)
    return HttpResponse.success(data=_long_term_memory_payload(memory))
