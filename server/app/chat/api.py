"""聊天 HTTP 路由。

所有端点挂载在 /api/v1/ai/chat/ 下：
  POST /chat/stream     — SSE 流式对话主入口，前端核心调用
  POST /chat/upload     — 文件上传（预上传场景）
  GET  /chat/uploads/…  — 读取上传文件（带权限校验）
  GET  /chat/files/…    — 读取聊天文件（如图解 PNG）
  GET  /chat/sessions   — 会话列表
  POST /chat/sessions   — 创建会话
  DELETE /chat/sessions/{id} — 软删除（归档）会话
  PATCH /chat/sessions/{id}  — 更新会话标题
  GET  /chat/history    — 获取聊天历史

画像端点（挂载在同一路由器下）：
  GET  /profile                — 获取完整画像
  GET  /profile/score          — 获取画像评分
  GET  /profile/onboarding     — 获取基础信息
  PATCH /profile/onboarding    — 更新首次登录数据
  PATCH /profile/tutoring-update — 应用辅导产生的画像增量

学校搜索（onboarding 流程需要）：
  GET  /schools/search
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.chat.schemas import ChatHistoryMessage
from app.chat.runtime import latest_user_message
from app.chat.service import get_chat_usecases
from app.config import CHAT_DIR
from app.infra.database import engine, get_session
from app.infra.logging import get_logger
from app.infra.models import School, User
from app.infra.response import HttpResponse
from app.profile import BaseInfoData, OnboardingResponse, OnboardingUpdate, StudentProfileData, TutoringProfileUpdate
from app.profile.service import get_profile_service

if TYPE_CHECKING:
    from app.chat.memory.service import ChatMemoryService

# 路由器实例
router = APIRouter()
logger = get_logger(__name__)


def _get_chat_memory_service() -> "ChatMemoryService":
    """获取与 ChatUseCases 共享的 chat memory 单例。"""
    return get_chat_usecases()._memory_service


async def _sse_wrap(events: AsyncIterator) -> AsyncIterator[str]:
    """将 dict 事件转为 SSE 文本格式：event: xxx\\ndata: yyy\\n\\n"""
    async for ev in events:
        etype = ev.get("event", "message")
        data = ev.get("data")
        data_str = json.dumps(data, ensure_ascii=False) if data is not None else ""
        yield f"event: {etype}\ndata: {data_str}\n\n"


@router.post("/chat/stream")
async def mentor_chat_stream(
    message: str | None = Form(default=None),
    history: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    attachments: str | None = Form(default=None),
    need_teaching_diagram: bool = Form(default=False),
    generate_video: bool = Form(default=False),
    enable_web_search: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
):
    """SSE 流式对话主入口。

    附件由前端先上传到 /chat/upload，再通过 attachments 传入。

    Args:
        message: 兼容字段；为空时使用 history 最后一条用户消息。
        history: JSON 编码的历史消息列表。
        session_id: 可选的会话ID。
        attachments: 附件URL字符串（逗号分隔）。
        need_teaching_diagram: 是否生成图解说明。
        generate_video: 是否生成视频。
        enable_web_search: 是否启用联网搜索。
        current_user: 当前登录用户。

    Returns:
        SSE 流式响应。
    """
    uc = get_chat_usecases()

    parsed_attachments = [u.strip() for u in attachments.split(",") if u.strip()] if attachments else []

    parsed_history: list[ChatHistoryMessage] | None = None
    if history:
        try:
            raw_history = json.loads(history)
            if not isinstance(raw_history, list):
                raise ValueError("history must be a list")
            parsed_history = [ChatHistoryMessage(**item) for item in raw_history]
        except Exception as exc:
            return HttpResponse.error(code=400, message=f"history 格式错误: {exc}")

    effective_message = latest_user_message(parsed_history or [])
    if not effective_message:
        effective_message = (message or "").strip()
        if effective_message:
            parsed_history = [ChatHistoryMessage(role="user", content=effective_message)]
    if not effective_message:
        return HttpResponse.error(code=400, message="history 或 message 必须包含一条用户消息")

    effective_session = session_id or uc.default_session_id(current_user.id)

    logger.info(
        "[ChatAPI] 流式对话请求: user_id=%s session_id=%s msg_len=%d attachments=%d",
        current_user.id, effective_session, len(effective_message), len(parsed_attachments),
    )

    # 返回 SSE 流式响应
    return StreamingResponse(
        _sse_wrap(uc.stream_chat(
            user_id=current_user.id,
            user_message=effective_message,
            history=parsed_history,
            session_id=effective_session,
            attachments=parsed_attachments or None,
            need_teaching_diagram=need_teaching_diagram,
            generate_video=generate_video,
            enable_web_search=enable_web_search,
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """独立上传接口。

    前端可先上传文件再发消息，支持预上传场景。

    Args:
        file: 上传的文件。
        session_id: 会话ID。
        current_user: 当前登录用户。

    Returns:
        上传成功响应，包含文件URL等信息。
    """
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    uc = get_chat_usecases()
    content = await file.read()
    logger.info("[ChatAPI] 文件上传: user_id=%s session_id=%s filename=%s size=%d", current_user.id, session_id, file.filename, len(content))
    try:
        saved = await uc.save_upload(
            filename=file.filename,
            content=content,
            user_id=current_user.id,
            session_id=session_id,
        )
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    return HttpResponse.success(data=saved)


@router.get("/chat/uploads/{owner_id}/{session_id}/{filename}")
async def get_uploaded_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """读取上传文件（带权限校验）。

    只允许文件所有者或当前用户访问。

    Args:
        owner_id: 文件所有者ID。
        session_id: 会话ID。
        filename: 文件名。
        current_user: 当前登录用户。

    Returns:
        文件响应。
    """
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_user_id=current_user.id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )
    except PermissionError as exc:
        return HttpResponse.error(code=403, message=str(exc))
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except FileNotFoundError as exc:
        return HttpResponse.error(code=404, message=str(exc))

    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/uploads/{owner_id}/{session_id}/diagrams/{filename}")
async def get_diagram_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """读取图解 PNG 文件（带权限校验）。

    只允许文件所有者访问。

    Args:
        owner_id: 文件所有者ID。
        session_id: 会话ID。
        filename: 图解文件名。
        current_user: 当前登录用户。

    Returns:
        文件响应。
    """
    uc = get_chat_usecases()
    try:
        file_path = uc.resolve_uploaded_file(
            current_user_id=current_user.id,
            owner_id=owner_id,
            session_id=session_id,
            filename=f"diagrams/{filename}",
        )
    except PermissionError as exc:
        return HttpResponse.error(code=403, message=str(exc))
    except ValueError as exc:
        return HttpResponse.error(code=400, message=str(exc))
    except FileNotFoundError as exc:
        return HttpResponse.error(code=404, message=str(exc))

    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/files/{owner_id}/{session_id}/{filename}")
async def get_chat_file(
    owner_id: int,
    session_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """读取聊天文件（如 diagram.png），带权限校验。

    只允许文件所有者访问。

    Args:
        owner_id: 文件所有者ID。
        session_id: 会话ID。
        filename: 文件名（如 diagram.png）。
        current_user: 当前登录用户。

    Returns:
        文件响应。
    """
    # 权限校验：只允许所有者访问
    if current_user.id != owner_id:
        return HttpResponse.error(code=403, message="无权访问此文件")

    file_path = (CHAT_DIR / str(owner_id) / str(session_id) / filename).resolve()
    base_dir = (CHAT_DIR / str(owner_id) / str(session_id)).resolve()
    if not str(file_path).startswith(str(base_dir)):
        return HttpResponse.error(code=400, message="非法文件路径")
    if not file_path.exists():
        return HttpResponse.error(code=404, message="文件不存在")

    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/sessions")
async def get_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取用户的会话列表。

    Args:
        limit: 返回数量限制。
        current_user: 当前登录用户。

    Returns:
        会话列表。
    """
    uc = get_chat_usecases()
    return HttpResponse.success(data=await uc.list_sessions(current_user.id, limit))


@router.post("/chat/sessions")
async def create_session(
    current_user: User = Depends(get_current_user),
):
    """创建新会话。

    Args:
        current_user: 当前登录用户。

    Returns:
        新创建的会话信息。
    """
    uc = get_chat_usecases()
    return HttpResponse.success(data=await uc.create_session(current_user.id), status_code=201)


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """软删除会话。

    标记为归档而非物理删除，保留历史数据。

    Args:
        session_id: 会话ID。
        current_user: 当前登录用户。

    Returns:
        操作结果。
    """
    uc = get_chat_usecases()
    success = await uc.archive_session(current_user.id, session_id)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="会话已归档")


@router.patch("/chat/sessions/{session_id}")
async def update_session(
    session_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """更新会话标题。"""
    title = (payload.get("title") or "").strip()
    if not title:
        return HttpResponse.error(code=400, message="标题不能为空")
    uc = get_chat_usecases()
    success = await uc.update_session_title(current_user.id, session_id, title)
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    return HttpResponse.success(message="标题已更新")


@router.get("/chat/history")
async def chat_history(
    session_id: str | None = Query(default=None, description="指定会话ID"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """获取聊天历史。

    Args:
        session_id: 可选的会话ID，为空则返回最近会话的历史。
        limit: 返回消息数量限制。
        current_user: 当前登录用户。

    Returns:
        消息历史列表。
    """
    uc = get_chat_usecases()
    items = await uc.get_history(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
    )
    return HttpResponse.success(data=[item.model_dump() for item in items])


# ---------------------------------------------------------------------------
# 画像 API
# ---------------------------------------------------------------------------


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户画像。"""
    profile_builder = get_profile_service()
    profile = await profile_builder.get_or_create_profile(user_id=current_user.id)
    profile_json = profile.profile_json or {}
    return HttpResponse.success(data={
        "user_id": profile.user_id,
        "module": profile.module,
        "base_info": profile_json.get("base_info") or {},
        "learning_profile": profile_json.get("learning_profile") or {},
        "knowledge_mastery": profile_json.get("knowledge_mastery") or [],
        "initial_strategy": profile_json.get("initial_strategy") or {},
        "profile_meta": profile_json.get("profile_meta") or {},
        "profile_json": profile.profile_json,
        "profile_score_json": profile.profile_score_json,
        "updated_at": profile.updated_at,
    })


@router.get("/profile/score")
async def get_profile_score(current_user: User = Depends(get_current_user)):
    """获取当前用户画像评分。"""
    profile_builder = get_profile_service()
    profile = await profile_builder.get_or_create_profile(user_id=current_user.id)
    score_json = profile.profile_score_json or {}
    return HttpResponse.success(data={
        "user_id": profile.user_id,
        "module": profile.module,
        "score": score_json.get("overall_score"),
        "metrics": {
            "dimension_scores": score_json.get("dimension_scores") or {},
        },
        "scored_at": score_json.get("scored_at"),
        "updated_at": profile.updated_at,
    })


@router.get("/profile/onboarding")
async def get_profile_onboarding(
    current_user: User = Depends(get_current_user),
):
    """获取用户基础信息（base_info）。"""
    profile_builder = get_profile_service()
    base_info = await profile_builder.get_onboarding(user_id=current_user.id)
    return HttpResponse.success(data=OnboardingResponse(
        base_info=BaseInfoData(**base_info),
        student_profile=StudentProfileData(
            school=base_info.get("school"),
            school_level=base_info.get("school_level"),
            major=base_info.get("major"),
            grade=base_info.get("grade"),
            courses=base_info.get("courses", []),
            learning_goal=base_info.get("global_learning_goal"),
            preferred_language=", ".join(base_info.get("programming_languages", [])),
        ),
        profile_initialized=bool(base_info.get("major")),
    ).model_dump())

@router.patch("/profile/onboarding")
async def update_profile_onboarding(
    payload: OnboardingUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """更新首次登录数据（全局画像）。立即返回，LLM推理在后台进行。"""
    profile_builder = get_profile_service()
    payload_data = payload.model_dump()

    try:
        result = await profile_builder.update_from_onboarding(
            user_id=current_user.id,
            payload=payload_data,
        )

        # 更新用户标志位 — 通过 db session 重新加载，避免 detached 对象的 greenlet 错误
        user = await db.get(User, current_user.id)
        if user:
            user.is_first_login = False
            await db.commit()
        logger.info("[ChatAPI] onboarding complete: user_id=%s", current_user.id)
    except Exception as e:
        logger.warning("[ChatAPI] onboarding update failed: user_id=%s err=%s", current_user.id, e)
        return HttpResponse.error(code=400, message=str(e))

    # 后台异步执行 LLM 推理和评分，不阻塞响应
    background_tasks.add_task(
        profile_builder.run_onboarding_inference, user_id=current_user.id, payload=payload_data
    )

    return HttpResponse.success(data={
        "profile": result,
    })


@router.patch("/profile/tutoring-update")
async def update_profile_from_tutoring(
    payload: TutoringProfileUpdate,
    current_user: User = Depends(get_current_user),
):
    """应用智能辅导产生的画像增量更新（针对课程画像）。"""
    profile_builder = get_profile_service()

    course_name = payload.active_course
    if not course_name:
        return HttpResponse.error(code=400, message="active_course is required")

    try:
        result = await profile_builder.process_tutoring_update(
            user_id=current_user.id,
            course_name=course_name,
            session_id=payload.session_id,
        )
        return HttpResponse.success(data=result)
    except Exception as e:
        logger.warning("[ChatAPI] tutoring profile update failed: user_id=%s err=%s", current_user.id, e)
        return HttpResponse.error(code=400, message=str(e))


@router.get("/profile/history")
async def get_profile_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取画像历史（已废弃，返回空列表）。"""
    return HttpResponse.success(data=[])


# ---------------------------------------------------------------------------
# 学校搜索 API
# ---------------------------------------------------------------------------


async def _resolve_school_level(school_name: str | None) -> str | None:
    """根据学校名称解析院校层次。"""
    school_name = (school_name or "").strip()
    if not school_name:
        return None

    async with AsyncSession(engine, expire_on_commit=False) as session:
        stmt = select(School).where(School.name == school_name).limit(1)
        school = (await session.exec(stmt)).scalars().first()

    return school.level if school and school.level else None


@router.get("/schools/search")
async def search_schools(
    keyword: str = Query(default="", min_length=0, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
):
    """搜索学校。

    Args:
        keyword: 搜索关键词，为空则返回热门学校
        limit: 返回数量限制

    Returns:
        学校列表，包含 id、name、level
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        if keyword:
            stmt = (
                select(School)
                .where(School.name.contains(keyword))
                .order_by(School.name)
                .limit(limit)
            )
        else:
            # 无关键词时返回部分学校（按 ID 倒序，获取最新导入的）
            stmt = select(School).order_by(School.id.desc()).limit(limit)

        schools = (await session.exec(stmt)).scalars().all()

    return HttpResponse.success(data=[
        {
            "id": school.id,
            "name": school.name,
            "level": school.tier or school.level,
            "tier": school.tier,
        }
        for school in schools
    ])
