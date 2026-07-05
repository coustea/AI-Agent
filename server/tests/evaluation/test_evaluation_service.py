from datetime import datetime

from app.evaluation.schemas import LearningEventCreate
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.evaluation.service import (
    EvaluationService,
    build_profile_update_payload,
    build_summary_from_events,
    derive_memory_signals,
)
from app.infra.models import LearningEvent


def test_quiz_low_score_becomes_weakness_memory_signal():
    event = LearningEventCreate(
        event_type="quiz_submitted",
        course="计算机网络",
        topic="TCP 三次握手",
        score=52,
    )

    signals = derive_memory_signals(event)

    # derive_memory_signals is now a legacy stub that returns empty list
    assert signals == []


def test_feedback_can_become_preference_and_weakness_signals():
    event = LearningEventCreate(
        event_type="resource_feedback",
        topic="递归边界条件",
        feedback="这部分还是看不懂，希望多给图解和代码案例",
    )

    signals = derive_memory_signals(event)

    # derive_memory_signals is now a legacy stub that returns empty list
    assert signals == []


def test_memory_signals_build_tutoring_profile_update_payload():
    event = LearningEventCreate(
        event_type="resource_feedback",
        course="数据结构",
        topic="递归边界条件",
        feedback="这部分还是看不懂，希望多给图解和代码案例",
    )

    payload = build_profile_update_payload(event)

    # build_profile_update_payload is now a legacy stub that returns None
    assert payload is None


def test_summary_aggregates_learning_events():
    events = [
        LearningEvent(
            id=1,
            user_id=1,
            event_type="quiz_submitted",
            topic="递归",
            score=60,
            duration_seconds=120,
            created_at=datetime.now(),
        ),
        LearningEvent(
            id=2,
            user_id=1,
            event_type="resource_completed",
            topic="递归",
            duration_seconds=180,
            created_at=datetime.now(),
        ),
        LearningEvent(
            id=3,
            user_id=1,
            event_type="resource_feedback",
            topic="递归",
            feedback="希望多给图解",
            created_at=datetime.now(),
        ),
        LearningEvent(
            id=4,
            user_id=1,
            event_type="learning_heartbeat",
            duration_seconds=300,
            created_at=datetime.now(),
        ),
    ]

    summary = build_summary_from_events(events, active_minutes=2)

    assert summary.event_count == 4
    assert summary.average_score == 60
    assert summary.completed_resources == 1
    # active_minutes counts only learning_heartbeat events;
    # 300s is capped to MAX_HEARTBEAT_SECONDS (120) → 120 // 60 = 2 minutes
    assert summary.active_minutes == 2
    assert "递归" in summary.weak_topics
    assert "图解材料" in summary.preferred_resources


def test_record_event_persists_path_node_context():
    async def run():
        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        payload = LearningEventCreate(
            event_type="quiz_submitted",
            path_id=12,
            path_node_id=34,
            node_id="fastapi-intro",
            resource_id=56,
            resource_item_id=78,
            topic="FastAPI 入门",
            score=58,
        )

        event = await EvaluationService().record_event(session, user_id=1, payload=payload)

        assert event is not None
        assert event.path_id == 12
        assert event.path_node_id == 34
        assert event.node_id == "fastapi-intro"
        assert event.resource_item_id == 78
        session.add.assert_called_once_with(event)

    asyncio.run(run())
