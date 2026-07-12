from datetime import datetime

from app.evaluation.schemas import LearningEventCreate
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.evaluation.service import (
    EvaluationService,
    build_summary_from_events,
)
from app.infra.models import LearningEvent


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
            module="resource",
            event_type="resource_feedback",
            topic="递归",
            event_metadata={"feedback": "希望多给图解"},
            created_at=datetime.now(),
        ),
        LearningEvent(
            id=4,
            user_id=1,
            module="resource",
            event_type="learning_heartbeat",
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
            module="quiz",
            event_type="quiz_submitted",
            path_id=12,
            path_node_id=34,
            node_id="fastapi-intro",
            topic="FastAPI 入门",
            score=58,
            event_metadata={"is_correct": True, "resource_id": 56, "resource_item_id": 78}
        )

        event, _ = await EvaluationService().record_event(session, user_id=1, payload=payload)

        assert event is not None
        assert event.event_metadata.get("resource_item_id") == 78
        session.add.assert_called_once_with(event)

    asyncio.run(run())
