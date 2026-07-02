"""仪表盘 HTTP 路由 — 按功能拆分为独立子端点。"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.infra.database import get_session
from app.infra.models import (
    ChatMessage,
    ChatSession,
    GeneratedResource,
    GeneratedResourceItem,
    LearningEvent,
    LearningPath,
    LearningSession,
    PathNode,
    User,
)
from app.infra.response import HttpResponse
from app.profile.service import get_profile_service
from app.profile.types import ALL_DIMENSIONS, DIMENSION_NAMES

# 资源源类型常量
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _text(value: Any, fallback: str = "") -> str:
    """安全提取文本值，空值时返回默认值。"""
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def _course_context_name(course: dict[str, Any] | None, fallback: str = "") -> str:
    """从课程上下文字典中提取课程名称。"""
    if not isinstance(course, dict):
        return fallback
    context = course.get("course_context") or {}
    value = context.get("value") if isinstance(context, dict) else context
    if isinstance(value, dict):
        return _text(value.get("course"), fallback)
    return _text(value, fallback)


def _score_json(profile_json_or_score: dict[str, Any]) -> dict[str, Any]:
    """将评分数据转换为字典格式，非字典类型返回空字典。"""
    return profile_json_or_score if isinstance(profile_json_or_score, dict) else {}


def _low_score_dimensions(score_json: dict[str, Any], *, limit: int = 5) -> list[str]:
    """获取低分维度列表（得分低于60分）。"""
    scores = _score_json(score_json).get("dimension_scores") or {}
    items: list[tuple[str, float]] = []
    for key, value in scores.items():
        if isinstance(value, (int, float)) and value > 0 and value < 60:
            items.append((key, float(value)))
    items.sort(key=lambda item: item[1])
    return [DIMENSION_NAMES.get(key, key) for key, _ in items[:limit]]


def _score_evidence(score_json: dict[str, Any], key: str, *, limit: int = 3) -> list[str]:
    """获取指定维度的评分证据列表。"""
    evidence = _score_json(score_json).get("dimension_evidence") or {}
    values = evidence.get(key) or []
    return [str(item) for item in values[:limit] if str(item).strip()]


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
    return _text(resource.learning_need, "最近生成的资源")


def _current_node(path_nodes: list[PathNode]) -> PathNode | None:
    """获取当前学习路径节点（优先可用状态，其次已完成有缺陷状态）。"""
    for status in ("available", "completed_with_gaps"):
        for node in path_nodes:
            if node.status == status:
                return node
    return path_nodes[0] if path_nodes else None


# ---------------------------------------------------------------------------
# 共享轻量级查询
# ---------------------------------------------------------------------------

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


async def _get_profile_json(session: AsyncSession, user_id: int) -> dict[str, Any]:
    """获取用户画像数据。"""
    profile = await get_profile_service().get_profile(user_id=user_id, db=session)
    return profile.profile_json or {}


async def _get_profile_score_json(session: AsyncSession, user_id: int) -> dict[str, Any]:
    """获取用户评分数据。"""
    profile = await get_profile_service().get_profile(user_id=user_id, db=session)
    return profile.profile_score_json or {}


def _weak_topics_from_events(
    events: list[LearningEvent],
) -> list[str]:
    """从学习事件中提取薄弱知识点。"""
    counter: Counter[str] = Counter()
    for event in events:
        topic = _event_topic(event)
        if not topic:
            continue
        feedback = event.feedback or ""
        if event.event_type == "quiz_submitted" and event.score is not None and event.score < 70:
            counter[topic] += 2
        if any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")):
            counter[topic] += 2
    return [topic for topic, _ in counter.most_common(5)]


# ---------------------------------------------------------------------------
# 1. 获取推荐内容
# ---------------------------------------------------------------------------

@router.get("/recommendation")
async def get_recommendation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取首页推荐内容 — 根据用户状态返回个性化学习建议。"""
    profile_json = await _get_profile_json(session, current_user.id)
    base_info = profile_json.get("base_info") or {}
    goal = _text(base_info.get("global_learning_goal"))
    courses = base_info.get("courses") or []
    primary_course = courses[0] if courses else ""

    active_paths = await _get_active_paths(session, current_user.id)
    active_path = active_paths[0] if active_paths else None
    path_nodes = await _get_path_nodes(session, current_user.id, active_path.id) if active_path else []
    recent_events = await _get_recent_events(session, current_user.id, limit=20)
    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(
            GeneratedResource.user_id == current_user.id,
        )
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(3)
    )).all())
    chat_session_count = (await session.exec(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == current_user.id, ChatSession.is_archived.is_(False))
    )).one()
    user_message_count = (await session.exec(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == current_user.id, ChatMessage.role == "user")
    )).one()

    has_activity = any((chat_session_count, user_message_count, recent_resources, active_path, recent_events))
    cold_start = not _text(base_info.get("major")) and not has_activity
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


# ---------------------------------------------------------------------------
# 2. 获取用户画像雷达图
# ---------------------------------------------------------------------------

@router.get("/profile-radar")
async def get_profile_radar(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取用户画像雷达图数据 — 各维度得分和证据。"""
    profile = await get_profile_service().get_profile(user_id=current_user.id, db=session)
    score_json = profile.profile_score_json or {}

    scores = score_json.get("dimension_scores") or {}
    evidence = score_json.get("dimension_evidence") or {}
    dimensions: list[dict[str, Any]] = []
    for key in ALL_DIMENSIONS:
        score = scores.get(key)
        evidence_items = evidence.get(key) or []
        dimensions.append({
            "key": key,
            "label": DIMENSION_NAMES.get(key, key),
            "score": score if isinstance(score, (int, float)) else 0,
            "evidence": evidence_items,
            "missing": not evidence_items,
        })

    weak_areas = _low_score_dimensions(score_json)

    return HttpResponse.success(data={
        "user_id": profile.user_id,
        "module": profile.module,
        "score": score_json.get("overall_score"),
        "dimensions": dimensions,
        "weak_areas": weak_areas,
        "metrics": {
            "dimension_scores": scores,
            "dimension_evidence": evidence,
        },
        "radar": {
            "eyebrow": "画像",
            "title": "用户画像雷达图",
            "link_label": "查看画像",
            "path": "/profile",
            "note": "完整画像、课程背景和薄弱点明细已放在个人中心，首页只保留能力趋势信号。",
        },
        "scored_at": score_json.get("scored_at"),
        "updated_at": profile.updated_at,
    })


# ---------------------------------------------------------------------------
# 3. 获取继续学习数据
# ---------------------------------------------------------------------------

@router.get("/continue-learning")
async def get_continue_learning(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取继续学习数据 — 每条活跃路径的当前节点（一条路径只显示一个节点）。"""
    active_paths = await _get_active_paths(session, current_user.id)

    if not active_paths:
        return HttpResponse.success(data={"active_paths": []})

    result = []
    for path in active_paths:
        # 获取每条路径的节点
        path_nodes = await _get_path_nodes(session, current_user.id, path.id)
        current_node = _current_node(path_nodes)

        # 获取该路径的最后学习时间
        last_learned_at: datetime | None = None
        last_event = (await session.exec(
            select(LearningEvent)
            .where(
                LearningEvent.user_id == current_user.id,
                LearningEvent.path_id == path.id,
            )
            .order_by(col(LearningEvent.created_at).desc())
            .limit(1)
        )).first()
        if last_event:
            last_learned_at = last_event.created_at

        result.append({
            "id": path.id,
            "title": path.title,
            "overall_progress": path.overall_progress,
            "current_node_title": current_node.title if current_node else None,
            "current_node_id": current_node.node_id if current_node else None,
            "updated_at": path.updated_at.isoformat() if path.updated_at else None,
            "last_learned_at": last_learned_at.isoformat() if last_learned_at else None,
        })

    return HttpResponse.success(data={"active_paths": result})


# ---------------------------------------------------------------------------
# 4. 获取快捷操作
# ---------------------------------------------------------------------------

@router.get("/quick-actions")
async def get_quick_actions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取快捷操作和今日建议。"""
    profile_json = await _get_profile_json(session, current_user.id)
    recent_events = await _get_recent_events(session, current_user.id, limit=30)

    chat_session_count = (await session.exec(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == current_user.id, ChatSession.is_archived.is_(False))
    )).one()
    user_message_count = (await session.exec(
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == current_user.id, ChatMessage.role == "user")
    )).one()
    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(
            GeneratedResource.user_id == current_user.id,
        )
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(5)
    )).all())
    active_paths = await _get_active_paths(session, current_user.id)
    active_path = active_paths[0] if active_paths else None

    weak_topics = _weak_topics_from_events(recent_events)

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
    ]
    actions = [
        {key: _text(value) for key, value in item.items() if key != "score"}
        for item in sorted(action_defs, key=lambda value: value["score"], reverse=True)
    ]

    # 今日建议
    path_nodes = await _get_path_nodes(session, current_user.id, active_path.id) if active_path else []
    suggestions: list[dict[str, str]] = []
    tones = ["blue", "amber", "green", "indigo"]

    if active_path:
        node = _current_node(path_nodes)
        title = f"继续推进「{node.title}」" if node else "继续当前学习路径"
        reason = f"路径进度 {active_path.overall_progress}%，优先完成当前节点再进入下一阶段"
        suggestions.append({"title": title, "reason": reason, "path": "/path-planner", "tone": tones[0]})

    if weak_topics:
        topic = weak_topics[0]
        strategy_hint = f"「{topic}」维度偏弱，需要通过专项练习巩固"
        suggestions.append({
            "title": f"完成「{topic}」专项练习",
            "reason": strategy_hint,
            "path": "/question-bank",
            "tone": tones[1],
        })

    low_quiz = next(
        (e for e in recent_events
         if e.event_type == "quiz_submitted" and e.score is not None and e.score < 70),
        None,
    )
    if low_quiz:
        topic = _event_topic(low_quiz) or "最近测验"
        suggestions.append({
            "title": f"复盘「{topic}」错题",
            "reason": f"最近测验得分 {low_quiz.score:.0f}，先讲清错因再回到题库验证",
            "path": "/question-bank?tab=wrong",
            "tone": tones[2],
        })

    latest_resource = recent_resources[0] if recent_resources else None
    if latest_resource and latest_resource.status == "completed":
        suggestions.append({
            "title": "复习最近生成资料",
            "reason": "用错题和资源回顾保持知识稳定度",
            "path": f"/resource-detail/{latest_resource.id}" if latest_resource.id else "/resource-generator",
            "tone": tones[3],
        })

    fallbacks = [
        {"title": "生成新的学习资源", "reason": "把当前学习需求转成课件、导读或练习", "path": "/resource-generator", "tone": "blue"},
        {"title": "规划下一阶段路径", "reason": "将目标拆成阶段节点，系统会按节点持续推荐", "path": "/path-planner", "tone": "amber"},
    ]
    for fb in fallbacks:
        if len(suggestions) >= 3:
            break
        if not any(s["path"] == fb["path"] for s in suggestions):
            suggestions.append(fb)

    return HttpResponse.success(data={
        "actions": actions,
        "today_suggestions": suggestions[:3],
    })


# ---------------------------------------------------------------------------
# 5. 获取最近资源
# ---------------------------------------------------------------------------

@router.get("/recent-resources")
async def get_recent_resources(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取最近生成的学习资源列表。"""
    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(
            GeneratedResource.user_id == current_user.id,
        )
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(5)
    )).all())

    result: list[dict[str, Any]] = []
    for r in recent_resources[:4]:
        first_item = (await session.exec(
            select(GeneratedResourceItem)
            .where(GeneratedResourceItem.resource_id == r.id)
            .limit(1)
        )).first()
        result.append({
            "id": r.id,
            "title": _resource_title(r),
            "type": first_item.agent_type if first_item else _status_label(r.status),
            "agent": first_item.agent_type or "资源生成智能体" if first_item else "资源生成智能体",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return HttpResponse.success(data=result)


# ---------------------------------------------------------------------------
# 6. 获取学习统计
# ---------------------------------------------------------------------------

@router.get("/study-stats")
async def get_study_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """获取学习统计 — 本周天数、总时长、待完成节点等。"""
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    weekly_days = (await session.exec(
        select(func.count(func.distinct(func.date(col(LearningSession.started_at)))))
        .where(LearningSession.user_id == current_user.id, LearningSession.started_at >= week_start)
    )).one() or 0

    total_seconds = (await session.exec(
        select(func.coalesce(func.sum(LearningSession.duration_seconds), 0))
        .where(LearningSession.user_id == current_user.id)
    )).one() or 0
    total_hours = math.ceil(int(total_seconds) / 3600)

    active_paths = await _get_active_paths(session, current_user.id)
    active_path = active_paths[0] if active_paths else None
    pending_nodes = 0
    if active_path:
        pending_nodes = (await session.exec(
            select(func.count())
            .select_from(PathNode)
            .where(
                PathNode.user_id == current_user.id,
                PathNode.path_id == active_path.id,
                col(PathNode.status).in_(["available", "locked"]),
            )
        )).one() or 0

    recent_events_count = (await session.exec(
        select(func.count())
        .select_from(LearningEvent)
        .where(LearningEvent.user_id == current_user.id)
    )).one() or 0
    recent_resources_count = (await session.exec(
        select(func.count())
        .select_from(GeneratedResource)
        .where(
            GeneratedResource.user_id == current_user.id,
        )
    )).one() or 0
    today_suggestion_count = sum([
        1 if active_path else 0,
        1 if recent_events_count else 0,
        1 if recent_resources_count else 0,
        1,
    ])

    return HttpResponse.success(data={
        "weekly_days": int(weekly_days),
        "total_hours": int(total_hours),
        "pending_nodes": int(pending_nodes),
        "today_suggestions": int(today_suggestion_count),
    })
