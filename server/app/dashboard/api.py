"""Dashboard HTTP routes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.security import get_current_user
from app.chat.service import get_chat_usecases
from app.infra.database import get_session
from app.infra.models import (
    ChatMessage,
    ChatSession,
    GeneratedResource,
    LearningPath,
    LearningEvent,
    LearningSession,
    PathNode,
    User,
)
from app.infra.response import HttpResponse
from app.memory.types import ALL_DIMENSIONS, DIMENSION_NAMES
from app.resource.service import STANDALONE_RESOURCE_SOURCES

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dataclass(frozen=True)
class HomeUsageSnapshot:
    chat_session_count: int
    user_message_count: int
    recent_sessions: list[ChatSession]
    recent_resources: list[GeneratedResource]
    active_path: LearningPath | None
    path_nodes: list[PathNode]
    recent_events: list[LearningEvent]
    recent_learning_sessions: list[LearningSession]

    @property
    def has_activity(self) -> bool:
        return any((
            self.chat_session_count,
            self.user_message_count,
            self.recent_resources,
            self.active_path,
            self.recent_events,
            self.recent_learning_sessions,
        ))


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def _course_context_name(course: dict[str, Any] | None, fallback: str = "") -> str:
    if not isinstance(course, dict):
        return fallback
    context = course.get("course_context") or {}
    value = context.get("value") if isinstance(context, dict) else context
    if isinstance(value, dict):
        return _text(value.get("course"), fallback)
    return _text(value, fallback)


def _strategy_list(profile_json: dict[str, Any]) -> list[str]:
    strategy = profile_json.get("initial_strategy") or {}
    return [
        _text(strategy.get("strategy_summary")),
        _text(strategy.get("path_planning_strategy")),
        _text(strategy.get("tutor_strategy")),
    ]


def _mastery_items(profile_json: dict[str, Any]) -> list[dict[str, Any]]:
    items = profile_json.get("knowledge_mastery") or []
    return sorted(items, key=lambda item: item.get("mastery_score") or 0)


def _dimension_score_items(score_json: dict[str, Any]) -> list[dict[str, Any]]:
    scores = score_json.get("dimension_scores") or {}
    missing_sections = set(score_json.get("missing_sections") or [])
    items: list[dict[str, Any]] = []
    for key in ALL_DIMENSIONS:
        score = scores.get(key)
        items.append({
            "key": key,
            "label": DIMENSION_NAMES.get(key, key),
            "score": score if isinstance(score, (int, float)) else None,
            "missing": key in missing_sections or score is None,
        })
    return items


def _score_payload(profile: Any) -> dict[str, Any]:
    score_json = profile.profile_score_json or {}
    return {
        "user_id": profile.user_id,
        "module": profile.module,
        "version": profile.version,
        "score": score_json.get("overall_score"),
        "confidence": score_json.get("confidence", profile.confidence),
        "metrics": {
            "dimension_scores": score_json.get("dimension_scores") or {},
            "section_coverage": score_json.get("section_coverage", 0),
            "evidence_quality": score_json.get("evidence_quality", 0),
            "uncertainty_handling": None,
            "content_richness": None,
        },
        "dimensions": _dimension_score_items(score_json),
        "missing_sections": score_json.get("missing_sections") or [],
        "scored_at": score_json.get("scored_at"),
        "updated_at": profile.updated_at,
    }


async def _load_usage_snapshot(session: AsyncSession, user_id: int) -> HomeUsageSnapshot:
    chat_count = (await session.exec(
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(False))
    )).one()
    message_count = (await session.exec(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.role == "user")
    )).one()
    recent_sessions = list((await session.exec(
        select(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(False))
        .order_by(col(ChatSession.updated_at).desc())
        .limit(5)
    )).all())
    recent_resources = list((await session.exec(
        select(GeneratedResource)
        .where(
            GeneratedResource.user_id == user_id,
            col(GeneratedResource.source).in_(STANDALONE_RESOURCE_SOURCES),
        )
        .order_by(col(GeneratedResource.updated_at).desc())
        .limit(5)
    )).all())
    active_path = (await session.exec(
        select(LearningPath)
        .where(LearningPath.user_id == user_id, LearningPath.status == "active")
        .order_by(col(LearningPath.updated_at).desc())
        .limit(1)
    )).first()
    path_nodes: list[PathNode] = []
    if active_path and active_path.id is not None:
        path_nodes = list((await session.exec(
            select(PathNode)
            .where(PathNode.user_id == user_id, PathNode.path_id == active_path.id)
            .order_by(col(PathNode.priority).asc(), col(PathNode.updated_at).desc())
            .limit(12)
        )).all())
    recent_events = list((await session.exec(
        select(LearningEvent)
        .where(LearningEvent.user_id == user_id)
        .order_by(col(LearningEvent.created_at).desc())
        .limit(50)
    )).all())
    recent_learning_sessions = list((await session.exec(
        select(LearningSession)
        .where(LearningSession.user_id == user_id)
        .order_by(col(LearningSession.started_at).desc())
        .limit(30)
    )).all())
    return HomeUsageSnapshot(
        chat_session_count=int(chat_count or 0),
        user_message_count=int(message_count or 0),
        recent_sessions=recent_sessions,
        recent_resources=recent_resources,
        active_path=active_path,
        path_nodes=path_nodes,
        recent_events=recent_events,
        recent_learning_sessions=recent_learning_sessions,
    )


def _event_topic(event: LearningEvent | None) -> str:
    if not event:
        return ""
    return _text(event.topic) or _text(event.course)


def _resource_title(resource: GeneratedResource | None) -> str:
    if not resource:
        return ""
    return _text(resource.learning_need, "最近生成的资源")


def _weak_topics(snapshot: HomeUsageSnapshot, mastery: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in snapshot.recent_events:
        topic = _event_topic(event)
        if not topic:
            continue
        feedback = event.feedback or ""
        if event.event_type == "quiz_submitted" and event.score is not None and event.score < 70:
            counter[topic] += 2
        if any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")):
            counter[topic] += 2
    for item in mastery[:5]:
        topic = _text(item.get("knowledge_point"))
        if topic:
            counter[topic] += 1
    return [topic for topic, _ in counter.most_common(5)]


def _status_label(value: str) -> str:
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


def _quick_actions(snapshot: HomeUsageSnapshot, weak_topics: list[str]) -> list[dict[str, str]]:
    action_defs = [
        {
            "key": "tutor",
            "label": "智能辅导",
            "path": "/tutor",
            "icon": "chat",
            "score": 30 + snapshot.user_message_count,
            "description": f"已有 {snapshot.user_message_count} 条提问记录，继续沿最近问题追问" if snapshot.user_message_count else "还没有辅导记录，适合作为第一次校准入口",
            "tag": f"{snapshot.chat_session_count} 个会话" if snapshot.chat_session_count else "待开始",
        },
        {
            "key": "resource",
            "label": "资源引擎",
            "path": "/resource-generator",
            "icon": "resource",
            "score": 35 + len(snapshot.recent_resources) * 3 + len(weak_topics) * 2,
            "description": f"围绕 {weak_topics[0]} 生成配套材料" if weak_topics else "把当前学习需求转成课件、导读或练习",
            "tag": f"{len(snapshot.recent_resources)} 个资源" if snapshot.recent_resources else "可生成",
        },
        {
            "key": "path",
            "label": "路径规划",
            "path": "/path-planner",
            "icon": "path",
            "score": 45 + ((snapshot.active_path.overall_progress if snapshot.active_path else 0) // 5),
            "description": f"当前路径进度 {snapshot.active_path.overall_progress}%，继续推进节点" if snapshot.active_path else "还没有活跃路径，先生成阶段计划",
            "tag": "进行中" if snapshot.active_path else "待规划",
        },
        {
            "key": "practice",
            "label": "学习题库",
            "path": "/question-bank",
            "icon": "practice",
            "score": 25 + sum(1 for event in snapshot.recent_events if event.event_type == "quiz_submitted") * 4 + len(weak_topics),
            "description": f"用练习验证 {weak_topics[0]}" if weak_topics else "用题目把最近学习收口成反馈",
            "tag": f"{sum(1 for event in snapshot.recent_events if event.event_type == 'quiz_submitted')} 次测验",
        },
    ]
    return [
        {key: _text(value) for key, value in item.items() if key != "score"}
        for item in sorted(action_defs, key=lambda value: value["score"], reverse=True)
    ]


def _current_node(snapshot: HomeUsageSnapshot) -> PathNode | None:
    for status in ("available", "completed_with_gaps"):
        for node in snapshot.path_nodes:
            if node.status == status:
                return node
    return snapshot.path_nodes[0] if snapshot.path_nodes else None


def _recommendation(
    *,
    cold_start: bool,
    snapshot: HomeUsageSnapshot,
    weak_topics: list[str],
    strategies: list[str],
) -> dict[str, str]:
    node = _current_node(snapshot)
    latest_event = snapshot.recent_events[0] if snapshot.recent_events else None
    latest_resource = snapshot.recent_resources[0] if snapshot.recent_resources else None

    if cold_start and not snapshot.has_activity:
        return {
            "label": "推荐下一步",
            "title": "先补齐学习画像",
            "text": "首页还没有足够使用信号，先完成画像后再生成更准确的学习入口。",
            "action": "完善学习画像",
            "path": "/profile",
            "icon": "monitor",
        }
    if latest_event and latest_event.event_type == "quiz_submitted" and latest_event.score is not None and latest_event.score < 70:
        topic = _event_topic(latest_event) or (weak_topics[0] if weak_topics else "最近测验")
        return {
            "label": "测验信号",
            "title": f"复盘 {topic}",
            "text": f"最近一次测验得分 {latest_event.score:.0f}，适合先讲清错因再进入题库验证。",
            "action": "进入智能辅导",
            "path": "/tutor",
            "icon": "chat",
        }
    if node:
        return {
            "label": "今日建议",
            "title": f"继续推进：{node.title}",
            "text": node.recommendation_reason or node.mastery_target or "根据当前路径进度，优先完成这一项，再回到题库或资源页形成反馈。",
            "action": "继续学习",
            "path": "/path-planner",
            "icon": "path",
        }
    if weak_topics:
        return {
            "label": "薄弱信号",
            "title": f"攻坚 {weak_topics[0]}",
            "text": strategies[0] if strategies else "最近画像或学习事件显示这里需要优先补强。",
            "action": "生成资源",
            "path": "/resource-generator",
            "icon": "resource",
        }
    if latest_resource and latest_resource.status in {"pending", "generating", "processing"}:
        return {
            "label": "资源进度",
            "title": f"{_resource_title(latest_resource)} 正在处理",
            "text": f"最新资源状态为「{_status_label(latest_resource.status)}」，可以回到资源页查看进度。",
            "action": "查看资源",
            "path": f"/resource-detail/{latest_resource.id}" if latest_resource.id else "/resource-generator",
            "icon": "resource",
        }
    if latest_resource and latest_resource.id:
        return {
            "label": "最近资源",
            "title": _resource_title(latest_resource),
            "text": "你最近生成过学习资源，适合回看后再做一轮练习形成反馈。",
            "action": "查看资源",
            "path": f"/resource-detail/{latest_resource.id}",
            "icon": "resource",
        }
    return {
        "label": "推荐下一步",
        "title": "生成第一条学习路径",
        "text": "还没有活跃路径记录，先把目标拆成阶段节点，后续首页会按节点和学习事件推荐。",
        "action": "开始规划",
        "path": "/path-planner",
        "icon": "path",
    }


def _build_home_payload(profile: Any, snapshot: HomeUsageSnapshot, recommended_question: Any = None) -> dict[str, Any]:
    """Convert DB signals and profile into frontend-ready dashboard JSON."""
    profile_json = profile.profile_json or {}
    base_info = profile_json.get("base_info") or {}
    mastery = _mastery_items(profile_json)
    strategies = [item for item in _strategy_list(profile_json) if item]
    cold_start = not _text(base_info.get("major")) and not snapshot.has_activity
    weak_topics = _weak_topics(snapshot, mastery)
    actions = _quick_actions(snapshot, weak_topics)
    recommendation = _recommendation(
        cold_start=cold_start,
        snapshot=snapshot,
        weak_topics=weak_topics,
        strategies=strategies,
    )
    recent_quiz_event = next((e for e in snapshot.recent_events if e.event_type == "quiz_submitted"), None)
    latest_resource_obj = snapshot.recent_resources[0] if snapshot.recent_resources else None
    active_path_node = _current_node(snapshot)
    
    recent_modules = {
        "latest_resource": {
            "id": latest_resource_obj.id,
            "title": _resource_title(latest_resource_obj),
            "status": latest_resource_obj.status,
            "created_at": latest_resource_obj.created_at.isoformat() if latest_resource_obj.created_at else None,
        } if latest_resource_obj else None,
        "active_path": {
            "id": snapshot.active_path.id,
            "title": snapshot.active_path.title,
            "overall_progress": snapshot.active_path.overall_progress,
            "current_node_title": active_path_node.title if active_path_node else None,
        } if snapshot.active_path else None,
        "recent_quiz": {
            "topic": _event_topic(recent_quiz_event),
            "score": recent_quiz_event.score,
            "created_at": recent_quiz_event.created_at.isoformat() if recent_quiz_event.created_at else None,
        } if recent_quiz_event else None,
        "recommended_question": {
            "id": recommended_question.question_id,
            "subject": recommended_question.subject,
            "content": recommended_question.content,
            "difficulty": recommended_question.difficulty,
            "type": recommended_question.question_type,
        } if recommended_question else None,
    }

    return {
        "state": "cold_start" if cold_start else "active",
        "recommendation": recommendation,
        "radar": {
            "eyebrow": "画像",
            "title": "用户画像雷达图",
            "link_label": "查看画像",
            "path": "/profile",
            "note": "完整画像、课程背景和薄弱点明细已放在个人中心，首页只保留能力趋势信号。",
        },
        "quick_section": {
            "eyebrow": "功能入口",
            "title": "快速进入功能页面",
            "actions": actions,
        },
        "recent_modules": recent_modules,
        "profile_score": _score_payload(profile),
    }


@router.get("/home")
async def get_home_dashboard(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get dynamic homepage view model for the current user."""
    memory = get_chat_usecases()._memory_service
    profile = await memory.get_or_create_profile(user_id=current_user.id)
    snapshot = await _load_usage_snapshot(session, current_user.id)

    # Calculate target topic for question recommendation
    profile_json = profile.profile_json or {}
    mastery = profile_json.get("knowledge_mastery") or []
    weak_topics = [
        item.get("name") for item in sorted(
            mastery, key=lambda x: x.get("mastery_score", 60)
        ) if item.get("mastery_score", 60) < 60
    ]
    courses = profile_json.get("learning_profile", {}).get("course_profiles", [])
    current_course = _course_context_name(courses[0]) if courses else None
    
    target_topic = weak_topics[0] if weak_topics else current_course

    from app.infra.models import QuizQuestion

    recommended_question = None
    if target_topic:
        stmt = select(QuizQuestion).where(
            QuizQuestion.content.ilike(f"%{target_topic}%") | 
            QuizQuestion.subject.ilike(f"%{target_topic}%")
        ).order_by(func.random()).limit(1)
        recommended_question = (await session.exec(stmt)).first()
        
    if not recommended_question:
        stmt = select(QuizQuestion).order_by(func.random()).limit(1)
        recommended_question = (await session.exec(stmt)).first()

    return HttpResponse.success(data=_build_home_payload(profile, snapshot, recommended_question))
