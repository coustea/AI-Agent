"""Memory HTTP routes.  # 记忆层 HTTP 路由

模块职责：
- 暴露记忆层读取接口供前端使用
- 提供用户画像和聊天历史的查询端点
- 处理用户权限校验

设计原则：
- 其他功能模块应继续使用 MemoryLayer 而非直接读取记忆表
- 所有接口需要 JWT 认证
- 用户只能查看自己的数据（通过 _assert_user_scope 校验）

端点列表：
- GET /profile - 获取当前用户画像
- GET /profile/history - 获取当前用户画像历史
- GET /profile/{user_id} - 获取指定用户画像（需权限校验）
- GET /profile/{user_id}/history - 获取指定用户画像历史
- GET /memory/recent-chat - 获取最近聊天记录
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.security import get_current_user
from app.infra.models import User
from app.memory import MemoryLayer
from app.memory._store import MEMORY_COMPRESSION_TOKEN_THRESHOLD
from app.shared.response import HttpResponse

router = APIRouter()


def _assert_user_scope(current_user: User, user_id: int) -> None:
    """校验用户权限。  # 确保当前用户只能访问自己的数据

    参数：
    - current_user: 当前登录用户
    - user_id: 请求的目标用户ID

    抛出：
    - HTTPException(403): 无权访问其他用户数据
    """
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权查看其他用户数据")


def _profile_payload(profile) -> dict:
    """构建画像响应载荷。  # 将 UserProfile 转换为前端友好的字典格式

    参数：
    - profile: UserProfile 实例或 None

    返回：
    - 包含画像 Markdown 的字典，无画像时返回默认值
    """
    if profile is None:
        return {
            "user_id": None,
            "profile_markdown": None,
            "version": None,
            "confidence": None,
            "source_session_ids": None,
            "source_memory_ids": None,
            "updated_reason": None,
            "updated_at": None,
        }
    return {
        "user_id": profile.user_id,
        "profile_markdown": profile.profile_markdown,
        "version": profile.version,
        "confidence": profile.confidence,
        "source_session_ids": profile.source_session_ids,
        "source_memory_ids": profile.source_memory_ids,
        "updated_reason": profile.updated_reason,
        "updated_at": profile.updated_at,
    }


def _chat_memory_payload(message) -> dict:
    """构建聊天消息响应载荷。  # 将 ChatMessage 转换为前端友好的字典格式

    参数：
    - message: ChatMessage 实例

    返回：
    - 包含消息字段的字典
    """
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "attachments": message.attachments,
        "tool_calls": message.tool_calls,
        "diagram": message.diagram,
        "created_at": message.created_at,
    }


def _memory_payload(memory) -> dict:
    """构建长期记忆响应载荷。  # 将 UserMemory 转换为前端友好的字典格式

    参数：
    - memory: UserMemory 实例

    返回：
    - 包含记忆字段的字典
    """
    return {
        "id": memory.id,
        "user_id": memory.user_id,
        "session_id": memory.session_id,
        "module": memory.module,
        "title": memory.title,
        "content_markdown": memory.content_markdown,
        "memory_type": memory.memory_type,
        "dimension": memory.dimension,
        "importance": memory.importance,
        "source": memory.source,
        "source_message_count": memory.source_message_count,
        "expires_at": memory.expires_at,
        "evidence_count": memory.evidence_count,
        "last_seen_at": memory.last_seen_at,
        "attachments": memory.attachments,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }


def _profile_history_payload(history) -> dict:
    """构建画像历史响应载荷。  # 将 UserProfileHistory 转换为前端友好的字典格式

    参数：
    - history: UserProfileHistory 实例

    返回：
    - 包含历史快照字段的字典
    """
    return {
        "id": history.id,
        "user_id": history.user_id,
        "version": history.version,
        "profile_markdown": history.profile_markdown,
        "change_reason": history.change_reason,
        "source_session_ids": history.source_session_ids,
        "source_memory_ids": history.source_memory_ids,
        "created_at": history.created_at,
    }


@router.get("/profile")
async def get_current_profile(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户画像。  # 返回登录用户的 Markdown 画像

    返回：
    - HttpResponse: 包含画像数据的响应
    """
    memory_layer = MemoryLayer(module_name="mentor")
    profile = await memory_layer.get_profile(user_id=current_user.id)
    return HttpResponse.success(data=_profile_payload(profile))


@router.get("/profile/history")
async def get_current_profile_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户画像历史。  # 返回画像变更历史记录

    参数：
    - limit: 返回数量上限（1-100）

    返回：
    - HttpResponse: 包含画像历史列表的响应
    """
    memory_layer = MemoryLayer(module_name="mentor")
    history = await memory_layer.list_profile_history(user_id=current_user.id, limit=limit)
    return HttpResponse.success(data=[_profile_history_payload(item) for item in history])


@router.get("/profile/{user_id}")
async def get_profile_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """获取指定用户画像。  # 返回指定用户的 Markdown 画像（需权限校验）

    参数：
    - user_id: 目标用户ID

    返回：
    - HttpResponse: 包含画像数据的响应
    """
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module_name="mentor")
    profile = await memory_layer.get_profile(user_id=user_id)
    return HttpResponse.success(data=_profile_payload(profile))


@router.get("/profile/{user_id}/history")
async def get_profile_history_by_user_id(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取指定用户画像历史。  # 返回指定用户的画像变更历史（需权限校验）

    参数：
    - user_id: 目标用户ID
    - limit: 返回数量上限（1-100）

    返回：
    - HttpResponse: 包含画像历史列表的响应
    """
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module_name="mentor")
    history = await memory_layer.list_profile_history(user_id=user_id, limit=limit)
    return HttpResponse.success(data=[_profile_history_payload(item) for item in history])


@router.get("/memory/recent-chat")
async def get_recent_chat_memory(
    user_id: int = Query(..., ge=1),
    session_id: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """获取最近聊天记录。  # 返回指定会话的最近对话消息（需权限校验）

    参数：
    - user_id: 用户ID
    - session_id: 会话ID
    - limit: 返回数量上限（1-50）

    返回：
    - HttpResponse: 包含对话消息列表的响应

    设计原则：
    - 只返回 user/assistant 角色的消息
    - 过滤空内容消息
    """
    _assert_user_scope(current_user, user_id)
    memory_layer = MemoryLayer(module_name="mentor")
    messages = await memory_layer.list_short_term_messages(
        user_id=user_id,
        session_id=session_id,
        limit=limit,
    )
    dialogue_messages = [
        message
        for message in messages
        if getattr(message, "role", "") in {"user", "assistant"} and getattr(message, "content", "").strip()
    ]
    return HttpResponse.success(data=[_chat_memory_payload(message) for message in dialogue_messages])


@router.get("/memory/long-term")
async def get_long_term_memories(
    memory_type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取长期记忆列表。  # 返回当前用户的长期记忆

    参数：
    - limit: 返回数量上限（1-100）

    返回：
    - HttpResponse: 包含长期记忆列表的响应
    """
    memory_layer = MemoryLayer(module_name="mentor")
    if memory_type:
        if memory_type == "summary":
            grouped = await memory_layer.store.get_user_context_memories(
                user_id=current_user.id,
                module=memory_layer.module_name,
                memory_types=[memory_type],
                per_type_limits={memory_type: limit},
                source=None,
            )
        else:
            grouped = await memory_layer.query_long_term_memories_by_type(
                user_id=current_user.id,
                memory_types=[memory_type],
                per_type_limits={memory_type: limit},
            )
        memories = grouped.get(memory_type, [])
    else:
        memories = await memory_layer.list_long_term_memories(user_id=current_user.id, limit=limit)
    return HttpResponse.success(data=[_memory_payload(memory) for memory in memories])


@router.get("/memory/context-preview")
async def get_memory_context_preview(
    session_id: str = Query(..., min_length=1),
    recent_limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """预览下一轮聊天会注入的记忆上下文。"""
    memory_layer = MemoryLayer(module_name="mentor")
    context_markdown = await memory_layer.build_context_preview(
        user_id=current_user.id,
        session_id=session_id,
        recent_limit=recent_limit,
    )
    return HttpResponse.success(data={"context_markdown": context_markdown})


@router.post("/memory/extract")
async def extract_memory(
    session_id: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    """手动触发当前用户指定会话的长期记忆提取。"""
    memory_layer = MemoryLayer(module_name="mentor")
    success = await memory_layer.extract_facts(user_id=current_user.id, session_id=session_id)
    return HttpResponse.success(data={"success": success})


@router.post("/memory/rebuild-profile")
async def rebuild_profile(
    session_id: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    """手动重建当前用户画像。"""
    memory_layer = MemoryLayer(module_name="mentor")
    success = await memory_layer.build_profile(user_id=current_user.id, session_id=session_id)
    return HttpResponse.success(data={"success": success})


@router.post("/memory/compress-session")
async def compress_session(
    session_id: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    """手动触发当前用户指定会话的对话压缩。"""
    memory_layer = MemoryLayer(module_name="mentor")
    await memory_layer.store.summarize_and_compress(
        user_id=current_user.id,
        session_id=session_id,
        module=memory_layer.module_name,
        threshold=MEMORY_COMPRESSION_TOKEN_THRESHOLD,
    )
    return HttpResponse.success(data={"success": True})
