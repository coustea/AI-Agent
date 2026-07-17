from __future__ import annotations
import zoneinfo
from datetime import datetime, timezone
from typing import Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel, Field

from app.infra.models import LearningEvent, LearningSession

SHANGHAI_TZ = zoneinfo.ZoneInfo("Asia/Shanghai")

class WindowInfo(BaseModel):
    days: int
    start: str
    end: str

class DailyMinutes(BaseModel):
    date: str
    minutes: int

class ModuleCount(BaseModel):
    module: str
    count: int

class ModuleTimeBreakdown(BaseModel):
    module: str
    seconds: int

class ActivityInfo(BaseModel):
    active_days: int
    total_minutes: int
    daily_minutes: list[DailyMinutes]
    module_distribution: list[ModuleCount]
    module_time_breakdown: list[ModuleTimeBreakdown]

class ResourceFeedbackInfo(BaseModel):
    helpful: int
    not_helpful: int

class ResourceUsageInfo(BaseModel):
    generated: int
    viewed: int
    completed: int
    feedback: ResourceFeedbackInfo

class LearningPathInfo(BaseModel):
    nodes_started: int
    nodes_completed: int
    completion_rate: float

class TopicPracticeInfo(BaseModel):
    topic: str
    submitted: int
    correct: int
    accuracy: float
    enough_evidence: bool

class PracticeInfo(BaseModel):
    submitted: int
    correct: int
    accuracy: float
    by_topic: list[TopicPracticeInfo]

class TopicsInfo(BaseModel):
    encountered: list[str]

class DataQualityInfo(BaseModel):
    has_activity: bool
    insufficient_topics: list[str]

class AssessmentFacts(BaseModel):
    window: WindowInfo
    activity: ActivityInfo
    resource_usage: ResourceUsageInfo
    learning_path: LearningPathInfo
    practice: PracticeInfo
    topics: TopicsInfo
    data_quality: DataQualityInfo


def to_shanghai_date(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(SHANGHAI_TZ).date().isoformat()


async def build_assessment_facts(
    session: AsyncSession, user_id: int, window_start: datetime, window_end: datetime
) -> dict[str, Any]:
    # Query database for events and sessions
    events_stmt = select(LearningEvent).where(
        LearningEvent.user_id == user_id,
        LearningEvent.occurred_at >= window_start,
        LearningEvent.occurred_at < window_end
    )
    events = list((await session.exec(events_stmt)).all())

    sessions_stmt = select(LearningSession).where(
        LearningSession.user_id == user_id,
        LearningSession.started_at >= window_start,
        LearningSession.started_at < window_end
    )
    sessions = list((await session.exec(sessions_stmt)).all())

    # Window calculations
    delta = window_end - window_start
    days = delta.days

    # Active days
    active_dates = set()
    for sess in sessions:
        active_dates.add(to_shanghai_date(sess.started_at))
    for evt in events:
        active_dates.add(to_shanghai_date(evt.occurred_at))

    # Daily minutes
    daily_seconds_map = {}
    for sess in sessions:
        d = to_shanghai_date(sess.started_at)
        daily_seconds_map[d] = daily_seconds_map.get(d, 0) + (sess.duration_seconds or 0)
    
    daily_minutes = []
    for d in sorted(daily_seconds_map.keys()):
        daily_minutes.append(DailyMinutes(date=d, minutes=int(round(daily_seconds_map[d] / 60.0))))

    total_seconds = sum(sess.duration_seconds or 0 for sess in sessions)
    total_minutes = int(round(total_seconds / 60.0))

    # Module distribution (by event count)
    module_counts = {}
    for evt in events:
        m = evt.module
        module_counts[m] = module_counts.get(m, 0) + 1
    module_distribution = [ModuleCount(module=m, count=c) for m, c in module_counts.items()]

    # Module time breakdown (by session source_page → module name)
    SOURCE_PAGE_TO_MODULE = {
        "Tutor": "AI 辅导",
        "chat": "AI 辅导",
        "QuestionBank": "题库练习",
        "quiz": "题库练习",
        "PathNodeStudy": "路径学习",
        "PathPlan": "路径学习",
        "path": "路径学习",
        "ResourceGenerator": "资源生成",
        "ResourceResult": "资源生成",
        "resource": "资源生成",
        "AlgorithmVisualizer": "算法可视化",
        "visualizer": "算法可视化",
    }
    module_time_map: dict[str, int] = {}
    for sess in sessions:
        page = sess.source_page or ""
        module_name = SOURCE_PAGE_TO_MODULE.get(page)
        if module_name is None:
            # 尝试前缀匹配（如 PathPlanDetail 等）
            for prefix, name in SOURCE_PAGE_TO_MODULE.items():
                if page.startswith(prefix):
                    module_name = name
                    break
        if module_name is None:
            module_name = page if page else "其他"
        module_time_map[module_name] = module_time_map.get(module_name, 0) + (sess.duration_seconds or 0)
    module_time_breakdown = [ModuleTimeBreakdown(module=m, seconds=s) for m, s in module_time_map.items()]

    # Resource usage
    generated = sum(1 for e in events if e.event_type == "resource_generated")
    viewed = sum(1 for e in events if e.event_type == "resource_viewed")
    completed = sum(1 for e in events if e.event_type == "resource_completed")
    
    helpful = sum(
        1
        for e in events
        if e.event_type == "resource_feedback"
        and (e.event_metadata or {}).get("feedback") == "helpful"
    )
    not_helpful = sum(
        1
        for e in events
        if e.event_type == "resource_feedback"
        and (e.event_metadata or {}).get("feedback") == "not_helpful"
    )

    # Learning path
    nodes_started = sum(1 for e in events if e.event_type == "path_node_started")
    nodes_completed = sum(1 for e in events if e.event_type == "path_node_completed")
    completion_rate = (nodes_completed / nodes_started) if nodes_started > 0 else 0.0

    # Practice
    practice_events = []
    for e in events:
        if e.event_type in ("quiz_submitted", "path_quiz_answered"):
            meta = e.event_metadata or {}
            if "is_correct" in meta:
                practice_events.append(e)

    submitted = len(practice_events)
    correct = sum(1 for e in practice_events if (e.event_metadata or {}).get("is_correct") is True)
    accuracy = (correct / submitted) if submitted > 0 else 0.0

    # Group practice by topic
    topic_practice_map = {}
    for e in practice_events:
        t = e.topic or e.course or "未分类"
        if t not in topic_practice_map:
            topic_practice_map[t] = []
        topic_practice_map[t].append(e)

    by_topic = []
    insufficient_topics = []
    for topic, evts in topic_practice_map.items():
        sub = len(evts)
        corr = sum(1 for e in evts if (e.event_metadata or {}).get("is_correct") is True)
        acc = (corr / sub) if sub > 0 else 0.0
        
        attempts = set()
        for e in evts:
            attempt_idx = (e.event_metadata or {}).get("attempt_index")
            if attempt_idx is not None:
                attempts.add(attempt_idx)
            else:
                attempts.add(e.id or e.client_event_id or str(e.occurred_at))
                
        enough = (sub >= 5) and (len(attempts) >= 2)
        by_topic.append(TopicPracticeInfo(
            topic=topic,
            submitted=sub,
            correct=corr,
            accuracy=acc,
            enough_evidence=enough
        ))
        if not enough:
            insufficient_topics.append(topic)

    # Topics encountered
    encountered_topics = sorted(list(set(e.topic for e in events if e.topic)))

    has_activity = (len(events) > 0 or len(sessions) > 0)

    facts = AssessmentFacts(
        window=WindowInfo(
            days=days,
            start=window_start.isoformat(),
            end=window_end.isoformat()
        ),
        activity=ActivityInfo(
            active_days=len(active_dates),
            total_minutes=total_minutes,
            daily_minutes=daily_minutes,
            module_distribution=module_distribution,
            module_time_breakdown=module_time_breakdown
        ),
        resource_usage=ResourceUsageInfo(
            generated=generated,
            viewed=viewed,
            completed=completed,
            feedback=ResourceFeedbackInfo(helpful=helpful, not_helpful=not_helpful)
        ),
        learning_path=LearningPathInfo(
            nodes_started=nodes_started,
            nodes_completed=nodes_completed,
            completion_rate=completion_rate
        ),
        practice=PracticeInfo(
            submitted=submitted,
            correct=correct,
            accuracy=accuracy,
            by_topic=by_topic
        ),
        topics=TopicsInfo(
            encountered=encountered_topics
        ),
        data_quality=DataQualityInfo(
            has_activity=has_activity,
            insufficient_topics=insufficient_topics
        )
    )

    return facts.model_dump(mode="json")
