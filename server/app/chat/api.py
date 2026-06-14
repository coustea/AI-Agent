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

# 导入 FastAPI 核心组件：路由、后台任务、依赖注入、文件上传、查询参数
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
# 导入响应类型：FileResponse 用于文件下载，StreamingResponse 用于 SSE 流
from fastapi.responses import FileResponse, StreamingResponse
# SQLAlchemy 核心操作：select 查询、update 更新
from sqlalchemy import select, update
# 异步数据库会话，用于直接数据库操作（如更新用户状态）
from sqlmodel.ext.asyncio.session import AsyncSession

# 认证依赖：get_current_user 从 JWT token 中提取当前用户
from app.auth.security import get_current_user
# 业务逻辑层：get_chat_usecases 获取聊天用例实例，latest_user_message 提取最新用户消息
from app.chat.service import chat, get_chat_usecases
# 聊天文件存储目录，从 config.yaml 中读取
from app.config import CHAT_DIR
# 数据库引擎和会话获取函数，engine 用于直接创建会话，get_session 用于 FastAPI 依赖注入
from app.infra.database import engine, get_session
# 日志工具，按模块名获取 logger 实例
from app.infra.logging import get_logger
# 数据库模型：School（学校）、User（用户）
from app.infra.models import School, User
# 统一响应格式：HttpResponse.success() 和 HttpResponse.error()
from app.infra.response import HttpResponse
# 画像相关的数据模型和请求/响应类型
from app.profile import BaseInfoData, OnboardingResponse, OnboardingUpdate, StudentProfileData, TutoringProfileUpdate
# 画像服务：提供画像创建、更新、评分等功能
from app.profile.service import get_profile_service

# 类型检查时才导入的模块，避免循环依赖
if TYPE_CHECKING:
    from app.chat.memory.service import ChatMemoryService

# 创建 FastAPI 路由器实例，所有端点挂载在 /api/v1/ai/chat/ 下
router = APIRouter()
# 获取当前模块的 logger，用于结构化日志输出
logger = get_logger(__name__)


# 内部辅助函数：获取聊天记忆服务单例
def _get_chat_memory_service() -> "ChatMemoryService":
    """获取与 ChatUseCases 共享的 chat memory 单例。"""
    # ChatUseCases 内部维护了 ChatMemoryService 实例，这里直接访问避免重复创建
    return get_chat_usecases()._memory_service


# SSE（Server-Sent Events）格式转换器
async def _sse_wrap(events: AsyncIterator) -> AsyncIterator[str]:
    """将 dict 事件转为 SSE 文本格式：event: xxx\\ndata: yyy\\n\\n"""
    # 遍历异步事件流，将每个事件转换为 SSE 格式
    async for ev in events:
        # 提取事件类型，默认为 "message"
        etype = ev.get("event", "message")
        # 提取事件数据
        data = ev.get("data")
        # 将数据序列化为 JSON 字符串，保留中文字符（ensure_ascii=False）
        data_str = json.dumps(data, ensure_ascii=False) if data is not None else ""
        # 生成标准 SSE 格式：event 类型 + data 内容 + 空行分隔
        yield f"event: {etype}\ndata: {data_str}\n\n"


@router.post("/chat/stream")
async def mentor_chat_stream(
    user_input: str = Form(default=""),
    session_id: str | None = Form(default=None),
    attachments: str | None = Form(default=None),
    need_teaching_diagram: bool = Form(default=False),
    enable_web_search: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
):
    """SSE 流式对话主入口。

    前端只传 user_input，历史由后端从数据库构建。

    Args:
        user_input: 用户当前输入。
        session_id: 可选的会话ID。
        attachments: 附件URL字符串（逗号分隔）。
        need_teaching_diagram: 是否生成图解说明。
        enable_web_search: 是否启用联网搜索。
        current_user: 当前登录用户。

    Returns:
        SSE 流式响应。
    """
    uc = get_chat_usecases()
    parsed_attachments = [u.strip() for u in attachments.split(",") if u.strip()] if attachments else []
    effective_session = session_id or uc.default_session_id(current_user.id)
    effective_message = (user_input or "").strip()

    if not effective_message:
        return HttpResponse.error(code=400, message="请输入您的问题")

    logger.info(
        "[ChatAPI] 流式对话请求: user_id=%s session_id=%s msg_len=%d attachments=%d",
        current_user.id, effective_session, len(effective_message), len(parsed_attachments),
    )

    return StreamingResponse(
        _sse_wrap(chat(
            user_id=current_user.id,
            session_id=effective_session,
            user_input=effective_message,
            attachments=parsed_attachments or None,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_teaching_diagram,
        )),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/upload")
# 文件上传端点，支持预上传场景
async def upload_file(
    # File(...) 表示必填文件参数
    file: UploadFile = File(...),  # 上传的文件对象，包含 filename 和 file 数据
    session_id: str = Form(...),  # 必填：文件所属的会话ID
    current_user: User = Depends(get_current_user),  # JWT 认证
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
    # 校验文件名不能为空
    if not file.filename:
        return HttpResponse.error(code=400, message="文件名不能为空")
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    # 读取文件内容到内存（注意：大文件应考虑流式处理）
    content = await file.read()
    # 记录上传日志：用户ID、会话ID、文件名、文件大小
    logger.info("[ChatAPI] 文件上传: user_id=%s session_id=%s filename=%s size=%d", current_user.id, session_id, file.filename, len(content))
    try:
        # 调用业务逻辑层保存文件，返回保存后的文件信息（如URL）
        saved = await uc.save_upload(
            filename=file.filename,  # 原始文件名
            content=content,  # 文件二进制内容
            user_id=current_user.id,  # 文件所有者ID
            session_id=session_id,  # 文件所属会话ID
        )
    except ValueError as exc:
        # 业务逻辑层抛出的验证错误（如文件类型不支持、大小超限）
        return HttpResponse.error(code=400, message=str(exc))
    # 返回成功响应，包含保存后的文件信息
    return HttpResponse.success(data=saved)


@router.get("/chat/uploads/{owner_id}/{session_id}/{filename}")
# 读取上传文件端点，带权限校验
async def get_uploaded_file(
    owner_id: int,  # 文件所有者ID，从URL路径中提取
    session_id: str,  # 会话ID，从URL路径中提取
    filename: str,  # 文件名，从URL路径中提取
    current_user: User = Depends(get_current_user),  # JWT 认证：当前登录用户
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
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    try:
        # 解析文件路径并进行权限校验
        # resolve_uploaded_file 会验证：当前用户是否为文件所有者，文件是否存在，路径是否合法
        file_path = uc.resolve_uploaded_file(
            current_user_id=current_user.id,  # 当前登录用户ID
            owner_id=owner_id,  # 文件所有者ID
            session_id=session_id,  # 文件所属会话ID
            filename=filename,  # 文件名
        )
    except PermissionError as exc:
        # 权限错误：当前用户不是文件所有者，返回 403
        return HttpResponse.error(code=403, message=str(exc))
    except ValueError as exc:
        # 参数错误：文件名非法或路径不合法，返回 400
        return HttpResponse.error(code=400, message=str(exc))
    except FileNotFoundError as exc:
        # 文件不存在，返回 404
        return HttpResponse.error(code=404, message=str(exc))

    # 返回文件响应，浏览器会自动下载或显示
    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/uploads/{owner_id}/{session_id}/diagrams/{filename}")
# 读取图解 PNG 文件端点，图解是 AI 生成的教学图示
async def get_diagram_file(
    owner_id: int,  # 文件所有者ID
    session_id: str,  # 会话ID
    filename: str,  # 图解文件名（不含 diagrams/ 前缀）
    current_user: User = Depends(get_current_user),  # JWT 认证
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
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    try:
        # 解析图解文件路径，注意添加 "diagrams/" 前缀
        # 图解文件存储在子目录 diagrams/ 中，与普通上传文件分开存放
        file_path = uc.resolve_uploaded_file(
            current_user_id=current_user.id,
            owner_id=owner_id,
            session_id=session_id,
            filename=f"diagrams/{filename}",  # 拼接完整相对路径
        )
    except PermissionError as exc:
        # 权限错误：当前用户不是文件所有者
        return HttpResponse.error(code=403, message=str(exc))
    except ValueError as exc:
        # 参数错误：文件名非法
        return HttpResponse.error(code=400, message=str(exc))
    except FileNotFoundError as exc:
        # 图解文件不存在
        return HttpResponse.error(code=404, message=str(exc))

    # 返回 PNG 文件响应
    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/files/{owner_id}/{session_id}/{filename}")
# 读取聊天文件端点（如 diagram.png），带路径遍历防护
async def get_chat_file(
    owner_id: int,  # 文件所有者ID
    session_id: str,  # 会话ID
    filename: str,  # 文件名（如 diagram.png）
    current_user: User = Depends(get_current_user),  # JWT 认证
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
    # 权限校验：只允许文件所有者访问，防止越权访问
    if current_user.id != owner_id:
        return HttpResponse.error(code=403, message="无权访问此文件")

    # 构建完整文件路径：CHAT_DIR / owner_id / session_id / filename
    # 使用 .resolve() 将路径解析为绝对路径，处理符号链接和相对路径
    file_path = (CHAT_DIR / str(owner_id) / str(session_id) / filename).resolve()
    # 构建基础目录路径，用于路径遍历攻击防护
    base_dir = (CHAT_DIR / str(owner_id) / str(session_id)).resolve()
    # 路径遍历防护：确保解析后的文件路径仍在基础目录内
    # 防止通过 ../../etc/passwd 等方式访问任意文件
    if not str(file_path).startswith(str(base_dir)):
        return HttpResponse.error(code=400, message="非法文件路径")
    # 检查文件是否存在
    if not file_path.exists():
        return HttpResponse.error(code=404, message="文件不存在")

    # 返回文件响应
    return FileResponse(path=str(file_path), filename=filename)


@router.get("/chat/sessions")
# 获取会话列表端点，返回用户的所有聊天会话
async def get_sessions(
    # Query 参数：限制返回数量，最小1，最大100，默认20
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """获取用户的会话列表。

    Args:
        limit: 返回数量限制。
        current_user: 当前登录用户。

    Returns:
        会话列表。
    """
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    # 调用业务逻辑层获取会话列表，按更新时间倒序
    return HttpResponse.success(data=await uc.list_sessions(current_user.id, limit))


@router.post("/chat/sessions")
# 创建新会话端点
async def create_session(
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """创建新会话。

    Args:
        current_user: 当前登录用户。

    Returns:
        新创建的会话信息。
    """
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    # 创建新会话并返回，HTTP 201 表示资源创建成功
    return HttpResponse.success(data=await uc.create_session(current_user.id), status_code=201)


@router.delete("/chat/sessions/{session_id}")
# 软删除会话端点，标记为归档而非物理删除
async def delete_session(
    session_id: str,  # 要删除的会话ID
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """软删除会话。

    标记为归档而非物理删除，保留历史数据。

    Args:
        session_id: 会话ID。
        current_user: 当前登录用户。

    Returns:
        操作结果。
    """
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    # 调用归档方法，返回是否成功
    success = await uc.archive_session(current_user.id, session_id)
    # 归档失败（会话不存在或无权操作）返回 404
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    # 归档成功返回成功消息
    return HttpResponse.success(message="会话已归档")


@router.patch("/chat/sessions/{session_id}")
# 更新会话标题端点，使用 PATCH 方法部分更新
async def update_session(
    session_id: str,  # 要更新的会话ID
    payload: dict,  # 请求体，包含 title 字段
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """更新会话标题。"""
    # 提取并清理标题：去除首尾空白，空标题返回 400 错误
    title = (payload.get("title") or "").strip()
    if not title:
        return HttpResponse.error(code=400, message="标题不能为空")
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    # 更新会话标题，返回是否成功
    success = await uc.update_session_title(current_user.id, session_id, title)
    # 更新失败（会话不存在或无权操作）返回 404
    if not success:
        return HttpResponse.error(code=404, message="会话不存在或无权操作")
    # 更新成功返回成功消息
    return HttpResponse.success(message="标题已更新")


@router.get("/chat/history")
# 获取聊天历史端点，返回指定会话或最近会话的消息记录
async def chat_history(
    # Query 参数：可选会话ID，为空则返回最近会话的历史
    session_id: str | None = Query(default=None, description="指定会话ID"),
    # Query 参数：限制返回消息数量，最大200条
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """获取聊天历史。

    Args:
        session_id: 可选的会话ID，为空则返回最近会话的历史。
        limit: 返回消息数量限制。
        current_user: 当前登录用户。

    Returns:
        消息历史列表。
    """
    # 获取聊天业务逻辑用例实例
    uc = get_chat_usecases()
    # 获取聊天历史，支持按会话ID筛选和数量限制
    items = await uc.get_history(
        user_id=current_user.id,  # 用户ID
        session_id=session_id,  # 可选会话ID
        limit=limit,  # 返回数量限制
    )
    # 将 ChatMessageItem 对象列表转换为字典列表，便于 JSON 序列化
    return HttpResponse.success(data=[item.model_dump() for item in items])


# ---------------------------------------------------------------------------
# 画像 API —— 用户学习画像的 CRUD 接口
# ---------------------------------------------------------------------------


@router.get("/profile")
# 获取用户完整学习画像端点
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户画像。"""
    # 获取画像服务实例，提供画像创建、查询、更新等功能
    profile_builder = get_profile_service()
    # 获取或创建用户画像：如果用户没有画像则自动创建
    profile = await profile_builder.get_or_create_profile(user_id=current_user.id)
    # 从画像中提取 JSON 数据，为空则使用空字典
    profile_json = profile.profile_json or {}
    # 返回完整的画像数据，包含多个维度
    return HttpResponse.success(data={
        "user_id": profile.user_id,  # 用户ID
        "module": profile.module,  # 学习模块
        "base_info": profile_json.get("base_info") or {},  # 基础信息（学校、年级等）
        "learning_profile": profile_json.get("learning_profile") or {},  # 学习风格画像
        "knowledge_mastery": profile_json.get("knowledge_mastery") or [],  # 知识掌握度列表
        "initial_strategy": profile_json.get("initial_strategy") or {},  # 初始学习策略
        "profile_meta": profile_json.get("profile_meta") or {},  # 画像元数据
        "profile_json": profile.profile_json,  # 完整画像 JSON
        "profile_score_json": profile.profile_score_json,  # 画像评分 JSON
        "updated_at": profile.updated_at,  # 最后更新时间
    })


@router.get("/profile/score")
# 获取用户画像评分端点，返回综合评分和维度分数
async def get_profile_score(current_user: User = Depends(get_current_user)):
    """获取当前用户画像评分。"""
    # 获取画像服务实例
    profile_builder = get_profile_service()
    # 获取或创建用户画像
    profile = await profile_builder.get_or_create_profile(user_id=current_user.id)
    # 提取评分 JSON 数据
    score_json = profile.profile_score_json or {}
    # 返回评分数据，包含总分和各维度分数
    return HttpResponse.success(data={
        "user_id": profile.user_id,  # 用户ID
        "module": profile.module,  # 学习模块
        "score": score_json.get("overall_score"),  # 综合评分
        "metrics": {
            "dimension_scores": score_json.get("dimension_scores") or {},  # 各维度分数
        },
        "scored_at": score_json.get("scored_at"),  # 评分时间
        "updated_at": profile.updated_at,  # 画像最后更新时间
    })


@router.get("/profile/onboarding")
# 获取用户 onboarding 基础信息端点，用于首次登录流程
async def get_profile_onboarding(
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """获取用户基础信息（base_info）。"""
    # 获取画像服务实例
    profile_builder = get_profile_service()
    # 获取用户的 onboarding 数据（学校、年级、专业等）
    base_info = await profile_builder.get_onboarding(user_id=current_user.id)
    # 构建 onboarding 响应对象，包含基础信息和学生画像
    return HttpResponse.success(data=OnboardingResponse(
        # 基础信息：直接使用 base_info 字典构建 BaseInfoData 对象
        base_info=BaseInfoData(**base_info),
        # 学生画像：从 base_info 中提取并转换为 StudentProfileData 对象
        student_profile=StudentProfileData(
            school=base_info.get("school"),  # 学校名称
            school_level=base_info.get("school_level"),  # 院校层次（如985、211）
            major=base_info.get("major"),  # 专业
            grade=base_info.get("grade"),  # 年级
            courses=base_info.get("courses", []),  # 课程列表
            learning_goal=base_info.get("global_learning_goal"),  # 全局学习目标
            # 编程语言列表转换为逗号分隔的字符串
            preferred_language=", ".join(base_info.get("programming_languages", [])),
        ),
        # 画像是否已初始化：通过检查 major 字段是否存在来判断
        profile_initialized=bool(base_info.get("major")),
    ).model_dump())

@router.patch("/profile/onboarding")
# 更新用户 onboarding 数据端点，立即返回，LLM 推理在后台异步执行
async def update_profile_onboarding(
    payload: OnboardingUpdate,  # 请求体：onboarding 更新数据
    background_tasks: BackgroundTasks,  # FastAPI 后台任务管理器
    current_user: User = Depends(get_current_user),  # JWT 认证
    db: AsyncSession = Depends(get_session),  # 数据库会话依赖注入
):
    """更新首次登录数据（全局画像）。立即返回，LLM推理在后台进行。"""
    # 获取画像服务实例
    profile_builder = get_profile_service()
    # 将请求体转换为字典，便于传递给业务逻辑层
    payload_data = payload.model_dump()
    user_id = int(current_user.id)

    try:
        # 调用业务逻辑层更新 onboarding 数据
        result = await profile_builder.update_from_onboarding(
            user_id=user_id,  # 用户ID
            payload=payload_data,  # 更新数据
        )

        # 更新用户表：标记为非首次登录
        # is_first_login 字段用于前端判断是否显示 onboarding 引导
        await db.exec(
            update(User)
            .where(User.id == user_id)  # 条件：当前用户
            .values(is_first_login=False)  # 设置为 False，表示已完成首次登录
        )
        # 提交数据库事务
        await db.commit()
        logger.info("[ChatAPI] onboarding complete: user_id=%s", user_id)
    except Exception as e:
        # 更新失败时记录警告日志并返回错误
        logger.warning("[ChatAPI] onboarding update failed: user_id=%s err=%s", user_id, e)
        return HttpResponse.error(code=400, message=str(e))

    # 后台异步执行 LLM 推理和评分，不阻塞响应
    # 这是关键的异步设计：onboarding 数据更新后立即返回，
    # LLM 推理（如学习风格分析、策略生成）在后台执行，避免用户等待
    background_tasks.add_task(
        profile_builder.run_onboarding_inference, user_id=user_id, payload=payload_data
    )

    # 立即返回成功响应，不等待后台任务完成
    return HttpResponse.success(data={
        "profile": result,
    })


@router.patch("/profile/tutoring-update")
# 智能辅导产生的画像增量更新端点，针对课程画像
async def update_profile_from_tutoring(
    payload: TutoringProfileUpdate,  # 请求体：辅导更新数据
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """应用智能辅导产生的画像增量更新（针对课程画像）。"""
    # 获取画像服务实例
    profile_builder = get_profile_service()

    # 提取当前活跃课程名称
    course_name = payload.active_course
    # 校验课程名称不能为空
    if not course_name:
        return HttpResponse.error(code=400, message="active_course is required")

    try:
        logger.info("[ChatAPI] 收到画像更新请求: user_id=%s", current_user.id)
        result = await profile_builder.process_tutoring_update(
            user_id=current_user.id,
            course_name=course_name,
            session_id=payload.session_id,
        )
        logger.info("[ChatAPI] 画像更新完成: user_id=%s", current_user.id)
        return HttpResponse.success(data=result)
    except Exception as e:
        logger.warning("[ChatAPI] tutoring profile update failed: user_id=%s err=%s", current_user.id, e)
        return HttpResponse.error(code=400, message=str(e))


@router.get("/profile/history")
# 获取画像历史端点（已废弃，保留兼容性）
async def get_profile_history(
    limit: int = Query(default=20, ge=1, le=100),  # 保留参数，但未使用
    current_user: User = Depends(get_current_user),  # JWT 认证
):
    """获取画像历史（已废弃，返回空列表）。"""
    # 已废弃的接口，返回空列表以保持向后兼容
    return HttpResponse.success(data=[])


# ---------------------------------------------------------------------------
# 学校搜索 API —— onboarding 流程中用于搜索学校
# ---------------------------------------------------------------------------


# 内部辅助函数：根据学校名称查询院校层次
async def _resolve_school_level(school_name: str | None) -> str | None:
    """根据学校名称解析院校层次。"""
    # 清理学校名称：去除首尾空白，空名称返回 None
    school_name = (school_name or "").strip()
    if not school_name:
        return None

    # 创建独立的数据库会话（不使用 FastAPI 依赖注入，因为这是内部函数）
    # expire_on_commit=False 防止提交后对象属性访问报错
    async with AsyncSession(engine, expire_on_commit=False) as session:
        # 查询学校表，按名称精确匹配，限制返回1条
        stmt = select(School).where(School.name == school_name).limit(1)
        # 执行查询并获取第一个结果
        school = (await session.exec(stmt)).scalars().first()

    # 返回学校层次（如 985、211、双一流），不存在则返回 None
    return school.level if school and school.level else None


@router.get("/schools/search")
# 搜索学校端点，用于 onboarding 流程中的学校选择
async def search_schools(
    # Query 参数：搜索关键词，最小长度0（允许空字符串），最大长度50
    keyword: str = Query(default="", min_length=0, max_length=50),
    # Query 参数：返回数量限制
    limit: int = Query(default=20, ge=1, le=100),
):
    """搜索学校。

    Args:
        keyword: 搜索关键词，为空则返回热门学校
        limit: 返回数量限制

    Returns:
        学校列表，包含 id、name、level
    """
    # 创建独立的数据库会话
    async with AsyncSession(engine, expire_on_commit=False) as session:
        if keyword:
            # 有关键词时：模糊搜索学校名称，按名称排序
            # School.name.contains(keyword) 生成 LIKE '%keyword%' 查询
            stmt = (
                select(School)
                .where(School.name.contains(keyword))  # 模糊匹配
                .order_by(School.name)  # 按名称字母顺序排序
                .limit(limit)  # 限制返回数量
            )
        else:
            # 无关键词时：返回部分学校（按 ID 倒序，获取最新导入的）
            # 这样用户打开搜索框时会看到最近添加的学校
            stmt = select(School).order_by(School.id.desc()).limit(limit)

        # 执行查询并获取所有结果
        schools = (await session.exec(stmt)).scalars().all()

    # 返回学校列表，每个学校包含 id、name、level、tier 字段
    # level 和 tier 可能指向不同字段，优先使用 tier
    return HttpResponse.success(data=[
        {
            "id": school.id,  # 学校ID
            "name": school.name,  # 学校名称
            "level": school.tier or school.level,  # 院校层次：优先使用 tier，fallback 到 level
            "tier": school.tier,  # 院校层次（原始字段）
        }
        for school in schools
    ])
