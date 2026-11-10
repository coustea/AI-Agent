"""Profile HTTP 路由。

包含个人中心画像查询/更新端点与首页仪表盘端点。
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import (
    ChatMessage,
    ChatSession,
    GeneratedResource,
    LearningAssessment,
    LearningEvent,
    LearningPath,
    PathNode,
    School,
    User,
)
from app.response import HttpResponse
from app.profile import (
    BaseInfoData,
    OnboardingResponse,
    OnboardingUpdate,
    ProfileUpdate,
    StudentProfileData,
)
from app.profile.service import (
    get_profile_service,
    _user_base_info_dict,
)
from app.profile.types import ALL_DIMENSIONS, DIMENSION_NAMES

logger = get_logger(__name__)
router = APIRouter()


# 获取完整用户画像
@router.get("/profile")
async def get_profile(
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """获取完整用户画像 — 聚合 User.base_info 与即时合成的维度评分。"""
    user_id = get_current_user().id
    current_user = await session.get(User, user_id)
    if not current_user:
        return HttpResponse.error(code=404, message="用户不存在")
    logger.info("GET /profile — user={}", user_id)
    svc = get_profile_service()
    dimensions = await svc.get_dimensions(user_id=user_id, db=session)
    base_info = _user_base_info_dict(current_user)

    # 组装各维度得分映射
    dimension_scores = {
        key: dim.get("score", 0) for key, dim in dimensions.items()
    }
    overall_score = round(sum(dimension_scores.values()) / len(dimension_scores)) if dimension_scores else 0

    return HttpResponse.success(data={
        "user_id": current_user.id,
        "module": "mentor",
        "base_info": BaseInfoData(**base_info).model_dump(),
        "dimensions": dimensions,
        "profile_score_json": {
            "overall_score": overall_score,
            "dimension_scores": dimension_scores,
            "scored_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
        },
        "updated_at": current_user.updated_at,
    })


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """更新个人中心展示的基础资料，不改变 onboarding 完成状态或偏好字段。"""
    user_id = get_current_user().id
    logger.info("[ProfileAPI] 更新基础资料: user_id={}", user_id)
    result = await get_profile_service().save_profile_info(
        user_id=int(user_id),
        payload=payload.model_dump(),
        db=session,
    )
    return HttpResponse.success(data=result)


# 获取 onboarding 基本信息（直接从 User 表读取）
@router.get("/profile/onboarding")
async def get_profile_onboarding(
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """获取 onboarding 基本信息 — 直接从 User 表读取。"""
    user_id = get_current_user().id
    current_user = await session.get(User, user_id)
    if not current_user:
        return HttpResponse.error(code=404, message="用户不存在")
    base_info = _user_base_info_dict(current_user)
    return HttpResponse.success(data=OnboardingResponse(
        base_info=BaseInfoData(**base_info),
        student_profile=StudentProfileData.from_base_info(base_info),
        profile_initialized=bool(current_user.major),
    ).model_dump())


# 更新 onboarding 信息（同步保存到 User 表，即时生效）
@router.patch("/profile/onboarding")
async def update_profile_onboarding(
    payload: OnboardingUpdate,
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """更新 onboarding 信息：同步保存基础信息与基线偏好到 User 表，即刻生效。"""
    payload_data = payload.model_dump()
    user_id = get_current_user().id
    svc = get_profile_service()
    logger.info("[ProfileAPI] onboarding 基础信息提交: user_id={}", user_id)
    await svc.save_onboarding_info(
        user_id=user_id,
        payload=payload_data,
        db=session,
    )
    logger.info("[ProfileAPI] onboarding 基础信息已即时落库: user_id={}", user_id)

    return HttpResponse.success(data={
        "inference_ok": True,
    })


# ---------------------------------------------------------------------------
# 仪表盘端点
# ---------------------------------------------------------------------------

def _text(value: Any, fallback: str = "") -> str:
    """安全提取文本值，空值时返回默认值。"""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def _low_score_dimensions(score_json: dict[str, Any], *, limit: int = 5) -> list[str]:
    """获取低分维度列表（得分低于60分）。"""
    scores = score_json.get("dimension_scores") or {}
    items: list[tuple[str, float]] = []
    for key, value in scores.items():
        if isinstance(value, (int, float)) and 0 < value < 60:
            items.append((key, float(value)))
    items.sort(key=lambda item: item[1])
    return [DIMENSION_NAMES.get(key, key) for key, _ in items[:limit]]


def _status_label(value: str) -> str:
    """将状态值转换为中文标签。"""
    return {
        "pending": "等待中",
        "generating": "生成中",
        "processing": "处理中",
        "completed": "已完成",
        "failed": "失败",
        "active": "进行中",
        "in_progress": "进行中",
        "available": "可开始",
        "ready": "资源就绪",
        "not_started": "未开始",
        "quiz_submitted": "测验提交",
        "resource_viewed": "资源查看",
        "resource_completed": "资源完成",
        "path_feedback": "路径反馈",
        "resource_feedback": "资源反馈",
        "tutor_helpful": "辅导反馈",
    }.get(value, value or "待更新")


def _event_topic(event: LearningEvent | None) -> str:
    """从学习事件中提取主题。"""
    if not event:
        return ""
    return _text(event.topic) or _text(event.course)


def _resource_title(resource: GeneratedResource | None) -> str:
    """获取资源标题。"""
    if not resource:
        return ""
    return _text(resource.topic, "最近生成的资源")


def _current_node(path_nodes: list[PathNode]) -> PathNode | None:
    """获取当前学习路径节点（优先可用状态，其次已完成有缺陷状态）。"""
    for status in ("available", "completed_with_gaps"):
        for node in path_nodes:
            if node.status == status:
                return node
    return path_nodes[0] if path_nodes else None


async def _get_active_paths(session: AsyncSession, user_id: int, limit: int = 5) -> list[LearningPath]:
    """获取用户所有活跃的学习路径列表。"""
    return list((await session.exec(
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.status == "active")
        .order_by(col(LearningPath.updated_at).desc())
        .limit(limit)
    )).all())


async def _get_path_nodes(session: AsyncSession, user_id: int, path_id: int) -> list[PathNode]:
    """获取学习路径的所有节点（按优先级排序）。"""
    return list((await session.exec(
        select(PathNode)
        .where(PathNode.user_id == user_id, PathNode.path_id == path_id)
        .order_by(col(PathNode.priority).asc(), col(PathNode.updated_at).desc())
        .limit(12)
    )).all())


async def _get_recent_events(session: AsyncSession, user_id: int, limit: int = 50) -> list[LearningEvent]:
    """获取用户最近的学习事件列表。"""
    return list((await session.exec(
        select(LearningEvent)
        .where(LearningEvent.user_id == user_id)
        .order_by(col(LearningEvent.created_at).desc())
        .limit(limit)
    )).all())


async def _get_profile_score_json(session: AsyncSession, user_id: int) -> dict[str, Any]:
    """获取用户评分数据（支持 JIT 即时装配评分）。"""
    user = await session.get(User, user_id)
    svc = get_profile_service()
    dimensions = await svc.get_dimensions(user_id=user_id, db=session)
    dim_scores = {k: v.get("score", 0) for k, v in dimensions.items()}
    overall = round(sum(dim_scores.values()) / len(dim_scores)) if dim_scores else 0
    return {
        "overall_score": overall,
        "dimension_scores": dim_scores,
        "scored_at": user.updated_at.isoformat() if user and user.updated_at else None,
    }


def _weak_topics_from_events(events: list[LearningEvent]) -> list[str]:
    """从学习事件中提取薄弱知识点。"""
    counter: Counter[str] = Counter()
    for event in events:
        topic = _event_topic(event)
        if not topic:
            continue
        metadata = event.event_metadata or {}
        if event.event_type == "quiz_submitted" and event.score is not None and event.score < 70:
            counter[topic] += 2
        feedback = (metadata.get("feedback_type") or metadata.get("feedback") or "")
        if isinstance(feedback, str) and any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")):
            counter[topic] += 2
    return [topic for topic, _ in counter.most_common(5)]


@router.get("/dashboard/recommendation")
async def get_recommendation(
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """获取首页推荐内容 — 根据用户状态返回个性化学习建议。"""
    user_id = get_current_user().id
    current_user = await session.get(User, user_id)
    if not current_user:
        return HttpResponse.error(code=404, message="用户不存在")
    logger.info("GET /dashboard/recommendation — user={}", user_id)
    goal = _text(current_user.global_learning_goal)
    courses = current_user.courses or []
    primary_course = courses[0] if courses else ""

    active_paths = await _get_active_paths(session, user_id)
    active_path = active_paths[0] if active_paths else None
    path_nodes = await _get_path_nodes(session, user_id, active_path.id) if active_path else []
    recent_events = await _get_recent_events(session, user_id, limit=20)
    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(GeneratedResource.user_id == user_id)
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(3)
    )).all())
    chat_session_count = (await session.exec(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(False))
    )).one()
    user_message_count = (await session.exec(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == current_user.id, ChatMessage.role == "user")
    )).one()

    has_activity = any((chat_session_count, user_message_count, recent_resources, active_path, recent_events))
    cold_start = not _text(current_user.major) and not has_activity
    weak_topics = _weak_topics_from_events(recent_events)
    node = _current_node(path_nodes)
    latest_event = recent_events[0] if recent_events else None
    latest_resource = recent_resources[0] if recent_resources else None

    if cold_start and not has_activity:
        recommendation = {
            "label": "推荐下一步",
            "title": "先补齐学习画像",
            "text": "首页还没有足够使用信号，先完成画像后再生成更准确的学习入口。",
            "action": "完善学习画像",
            "path": "/profile",
            "icon": "monitor",
        }
    elif latest_event and latest_event.event_type == "quiz_submitted" and latest_event.score is not None and latest_event.score < 70:
        topic = _event_topic(latest_event) or (weak_topics[0] if weak_topics else "最近测验")
        recommendation = {
            "label": "测验信号",
            "title": f"复盘 {topic}",
            "text": f"最近一次测验得分 {latest_event.score:.0f}，适合先讲清错因再进入题库验证。",
            "action": "进入智能辅导",
            "path": "/tutor",
            "icon": "chat",
        }
    elif node:
        recommendation = {
            "label": "今日建议",
            "title": f"继续推进：{node.title}",
            "text": f"继续推进「{node.title}」，完成后再回到题库或资源页形成反馈。",
            "action": "继续学习",
            "path": "/path-planner",
            "icon": "path",
        }
    elif weak_topics:
        fallback_text = goal or f"建议继续围绕「{primary_course}」推进" if primary_course else "建议先补充学习目标和课程信息"
        recommendation = {
            "label": "薄弱信号",
            "title": f"攻坚 {weak_topics[0]}",
            "text": fallback_text,
            "action": "生成资源",
            "path": "/resource-generator",
            "icon": "resource",
        }
    elif latest_resource and latest_resource.status in {"pending", "generating", "processing"}:
        recommendation = {
            "label": "资源进度",
            "title": f"{_resource_title(latest_resource)} 正在处理",
            "text": f"最新资源状态为「{_status_label(latest_resource.status)}」，可以回到资源页查看进度。",
            "action": "查看资源",
            "path": f"/resource-detail/{latest_resource.id}" if latest_resource.id else "/resource-generator",
            "icon": "resource",
        }
    elif latest_resource and latest_resource.id:
        recommendation = {
            "label": "最近资源",
            "title": _resource_title(latest_resource),
            "text": "你最近生成过学习资源，适合回看后再做一轮练习形成反馈。",
            "action": "查看资源",
            "path": f"/resource-detail/{latest_resource.id}",
            "icon": "resource",
        }
    else:
        recommendation = {
            "label": "推荐下一步",
            "title": "生成第一条学习路径",
            "text": "还没有活跃路径记录，先把目标拆成阶段节点，后续首页会按节点和学习事件推荐。",
            "action": "开始规划",
            "path": "/path-planner",
            "icon": "path",
        }

    return HttpResponse.success(data={
        "state": "cold_start" if cold_start else "active",
        "recommendation": recommendation,
    })


@router.get("/dashboard/profile-radar")
async def get_profile_radar(
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """获取用户画像雷达图数据 — 各维度得分。"""
    user_id = get_current_user().id
    logger.info("GET /dashboard/profile-radar — user={}", user_id)
    score_dict = await _get_profile_score_json(session, user_id)

    scores = score_dict.get("dimension_scores") or {}
    dimensions = [
        {
            "key": key,
            "label": DIMENSION_NAMES.get(key, key),
            "score": scores.get(key) if isinstance(scores.get(key), (int, float)) else 0,
        }
        for key in ALL_DIMENSIONS
    ]

    weak_areas = _low_score_dimensions(score_dict)

    return HttpResponse.success(data={
        "score": score_dict.get("overall_score"),
        "dimensions": dimensions,
        "weak_areas": weak_areas,
        "metrics": {"dimension_scores": scores},
        "radar": {
            "path": "/profile",
            "note": "完整画像、课程背景和薄弱点明细已放在个人中心，首页只保留能力趋势信号。",
        },
    })


_RESOURCE_TYPE_LABELS: dict[str, str] = {
    "content": "课程讲解",
    "mindmap": "思维导图",
    "code": "代码实操",
    "quiz": "随堂练习",
    "reading": "拓展阅读",
    "ppt": "演示幻灯",
    "cartoon": "动画讲解",
}


@router.get("/dashboard/recent-resources")
async def get_recent_resources(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """获取用户最近生成的独立教学资源，直接从 GeneratedResource.artifacts 解析。"""
    user_id = get_current_user().id
    logger.info("GET /dashboard/recent-resources — user={} limit={}", user_id, limit)

    records = list((await session.exec(
        select(GeneratedResource)
        .where(GeneratedResource.user_id == user_id)
        .order_by(col(GeneratedResource.id).desc())
        .limit(limit)
    )).all())

    data = []
    for record in records:
        agent_types = [a.get("kind") for a in (record.artifacts or []) if isinstance(a, dict) and a.get("kind")]
        primary = agent_types[0] if agent_types else ""
        data.append({
            "id": record.id or 0,
            "title": record.topic,
            "type": _RESOURCE_TYPE_LABELS.get(primary, primary or "资源包"),
            "agent": "资源生成智能体",
            "created_at": record.created_at,
        })
    return HttpResponse.success(data=data)


@router.get("/dashboard/quick-actions")
async def get_quick_actions(
    session: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """获取快捷操作和今日建议。"""
    user_id = get_current_user().id
    logger.info("GET /dashboard/quick-actions — user={}", user_id)
    recent_events = await _get_recent_events(session, user_id, limit=30)

    chat_session_count = (await session.exec(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(False))
    )).one()
    user_message_count = (await session.exec(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == user_id, ChatMessage.role == "user")
    )).one()
    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(GeneratedResource.user_id == user_id)
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(5)
    )).all())
    active_paths = await _get_active_paths(session, user_id)
    active_path = active_paths[0] if active_paths else None

    weak_topics = _weak_topics_from_events(recent_events)

    assessment_count = (await session.exec(
        select(func.count())
        .select_from(LearningAssessment)
        .where(LearningAssessment.user_id == user_id, LearningAssessment.status == "ready")
    )).one()
    has_ready_report = assessment_count > 0

    action_defs = [
        {
            "key": "tutor",
            "label": "智能辅导",
            "path": "/tutor",
            "icon": "chat",
            "score": 30 + int(user_message_count or 0),
            "description": f"已有 {user_message_count} 条提问记录，继续沿最近问题追问" if user_message_count else "还没有辅导记录，适合作为第一次校准入口",
            "tag": f"{chat_session_count} 个会话" if chat_session_count else "待开始",
        },
        {
            "key": "resource",
            "label": "资源引擎",
            "path": "/resource-generator",
            "icon": "resource",
            "score": 35 + len(recent_resources) * 3 + len(weak_topics) * 2,
            "description": f"围绕 {weak_topics[0]} 生成配套材料" if weak_topics else "把当前学习需求转成课件、导读或练习",
            "tag": f"{len(recent_resources)} 个资源" if recent_resources else "可生成",
        },
        {
            "key": "path",
            "label": "路径规划",
            "path": "/path-planner",
            "icon": "path",
            "score": 45 + ((active_path.overall_progress if active_path else 0) // 5),
            "description": f"当前路径进度 {active_path.overall_progress}%，继续推进节点" if active_path else "还没有活跃路径，先生成阶段计划",
            "tag": "进行中" if active_path else "待规划",
        },
        {
            "key": "practice",
            "label": "学习题库",
            "path": "/question-bank",
            "icon": "practice",
            "score": 25 + sum(1 for event in recent_events if event.event_type == "quiz_submitted") * 4 + len(weak_topics),
            "description": f"用练习验证 {weak_topics[0]}" if weak_topics else "用题目把最近学习收口成反馈",
            "tag": f"{sum(1 for event in recent_events if event.event_type == 'quiz_submitted')} 次测验",
        },
        {
            "key": "assessment",
            "label": "学习评估",
            "path": "/assessment",
            "icon": "assessment",
            "score": 40 + (10 if has_ready_report else 0),
            "description": "查看学习效果评估报告与辅导策略" if has_ready_report else "生成学习效果评估，获取个性化辅导建议",
            "tag": "已有报告" if has_ready_report else "待生成",
        },
    ]

    actions = [
        {key: _text(value) for key, value in item.items() if key != "score"}
        for item in sorted(action_defs, key=lambda value: value["score"], reverse=True)
    ]

    return HttpResponse.success(data={"actions": actions})


@router.get("/schools/search")
async def search_schools(
    keyword: str = Query(default="", min_length=0, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
) -> HttpResponse:
    """按关键词搜索学校列表（无关键词则返回最近学校）。"""
    if keyword:
        stmt = (
            select(School)
            .where(School.name.contains(keyword))
            .order_by(School.name)
            .limit(limit)
        )
    else:
        stmt = select(School).order_by(School.id.desc()).limit(limit)

    schools = list((await db.exec(stmt)).all())

    return HttpResponse.success(data=[
        {
            "id": school.id,
            "name": school.name,
            "level": school.tier or school.level,
            "tier": school.tier,
        }
        for school in schools
    ])
