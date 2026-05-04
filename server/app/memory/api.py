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

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.security import get_current_user
from app.infra.models import User
from app.memory import MemoryLayer
from app.shared.response import HttpResponse

router = APIRouter()


def _assert_user_scope(current_user: User, user_id: int) -> None:
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权查看其他用户数据")


def _profile_payload(profile) -> dict:
    if profile is None:
        return {
            "user_id": None,
            "module": None,
            "profile_markdown": None,
            "profile_json": None,
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
        "profile_markdown": profile.profile_markdown,
        "profile_json": profile.profile_json,
        "version": profile.version,
        "confidence": profile.confidence,
        "source_session_ids": profile.source_session_ids,
        "source_summary_ids": profile.source_summary_ids,
        "source_event_ids": profile.source_event_ids,
        "updated_reason": profile.updated_reason,
        "updated_at": profile.updated_at,
    }


def _profile_score_payload(profile) -> dict:
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

    profile_json = profile.profile_json or {}
    snapshot_score = profile_json.get("snapshot_score") or {}
    return {
        "user_id": profile.user_id,
        "module": profile.module,
        "version": profile.version,
        "score": snapshot_score.get("overall_score"),
        "confidence": snapshot_score.get("confidence", profile.confidence),
        "metrics": {
            "section_coverage": snapshot_score.get("section_coverage"),
            "evidence_quality": snapshot_score.get("evidence_quality"),
            "uncertainty_handling": snapshot_score.get("uncertainty_handling"),
            "content_richness": snapshot_score.get("content_richness"),
        },
        "missing_sections": snapshot_score.get("missing_sections") or [],
        "scored_at": snapshot_score.get("scored_at"),
        "updated_at": profile.updated_at,
    }


def _long_term_memory_payload(memory) -> dict:
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


def _session_summary_payload(summary) -> dict:
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


def _profile_history_payload(history) -> dict:
    return {
        "id": history.id,
        "user_id": history.user_id,
        "module": history.module,
        "version": history.version,
        "profile_markdown": history.profile_markdown,
        "profile_json": history.profile_json,
        "change_reason": history.change_reason,
        "source_session_ids": history.source_session_ids,
        "source_summary_ids": history.source_summary_ids,
        "source_event_ids": history.source_event_ids,
        "created_at": history.created_at,
    }


def _chat_message_payload(message) -> dict:
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
    memory_layer = MemoryLayer(module_name="mentor")
    profile = await memory_layer.get_profile(user_id=current_user.id)
    return HttpResponse.success(data=_profile_payload(profile))


@router.get("/profile/history")
async def get_current_profile_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module_name="mentor")
    history = await memory_layer.list_profile_history(user_id=current_user.id, limit=limit)
    return HttpResponse.success(data=[_profile_history_payload(item) for item in history])


@router.get("/profile/score")
async def get_current_profile_score(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module_name="mentor")
    profile = await memory_layer.get_profile(user_id=current_user.id)
    return HttpResponse.success(data=_profile_score_payload(profile))


@router.get("/profile/{user_id}")
async def get_profile_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module_name="mentor")
    profile = await memory_layer.get_profile(user_id=user_id)
    return HttpResponse.success(data=_profile_payload(profile))


@router.get("/profile/{user_id}/score")
async def get_profile_score_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module_name="mentor")
    profile = await memory_layer.get_profile(user_id=user_id)
    return HttpResponse.success(data=_profile_score_payload(profile))


@router.get("/profile/{user_id}/history")
async def get_profile_history_by_user_id(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module_name="mentor")
    history = await memory_layer.list_profile_history(user_id=user_id, limit=limit)
    return HttpResponse.success(data=[_profile_history_payload(item) for item in history])


@router.get("/long-term")
async def get_long_term_memory(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module_name="mentor")
    memory = await memory_layer.get_long_term_memory(user_id=current_user.id)
    return HttpResponse.success(data=_long_term_memory_payload(memory))


@router.get("/sessions/{session_id}/summaries")
async def get_session_summaries(
    session_id: str,
    limit: int = Query(default=3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module_name="mentor")
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
    memory_layer = MemoryLayer(module_name="mentor")
    messages = await memory_layer.list_short_term_messages(
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
    memory_layer = MemoryLayer(module_name="mentor")
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
    memory_layer = MemoryLayer(module_name="mentor")
    success = await memory_layer.build_profile(user_id=current_user.id, session_id=session_id)
    return HttpResponse.success(data={"success": success})


@router.post("/long-term/rebuild")
async def rebuild_long_term_memory(
    current_user: User = Depends(get_current_user),
):
    memory_layer = MemoryLayer(module_name="mentor")
    memory = await memory_layer.get_or_create_long_term_memory(user_id=current_user.id)
    return HttpResponse.success(data=_long_term_memory_payload(memory))
