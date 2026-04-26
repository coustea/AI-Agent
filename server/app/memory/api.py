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
    - 包含所有画像字段的字典，无画像时返回全 null 字典
    """
    if profile is None:
        return {
            "knowledge_level": None,
            "knowledge_level_score": None,
            "cognitive_style": None,
            "cognitive_style_score": None,
            "error_pattern": None,
            "error_pattern_score": None,
            "learning_goal": None,
            "learning_goal_score": None,
            "learning_history": None,
            "learning_history_score": None,
            "interest_preference": None,
            "interest_preference_score": None,
            "learning_pace": None,
            "learning_pace_score": None,
            "cognitive_level": None,
            "cognitive_level_score": None,
            "profile_summary": None,
            "updated_at": None,
        }
    return profile.model_dump(exclude={"user_id", "created_at"})


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
        "created_at": message.created_at,
    }


@router.get("/profile")
async def get_current_profile(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户画像。  # 返回登录用户的 8 维学习画像

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
    return HttpResponse.success(data=[item.model_dump(exclude={"id", "user_id"}) for item in history])


@router.get("/profile/{user_id}")
async def get_profile_by_user_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """获取指定用户画像。  # 返回指定用户的 8 维学习画像（需权限校验）

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
    return HttpResponse.success(data=[item.model_dump(exclude={"id", "user_id"}) for item in history])


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
