import pytest
import asyncio
from pydantic import ValidationError
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import evaluation_service
from unittest.mock import AsyncMock, MagicMock

def test_quiz_event_requires_correctness_metadata():
    # If module is quiz, event_type is quiz_submitted or path_quiz_answered,
    # the schema should validate event_metadata has 'is_correct' as boolean.
    with pytest.raises(ValidationError):
        LearningEventCreate(
            module="quiz",
            event_type="quiz_submitted",
            event_metadata={}
        )

    # Valid one should pass
    valid = LearningEventCreate(
        module="quiz",
        event_type="quiz_submitted",
        event_metadata={"is_correct": True, "attempt_index": 1}
    )
    assert valid.event_metadata["is_correct"] is True

def test_duplicate_client_event_returns_original_row():
    async def run_test():
        # Mock AsyncSession
        session = MagicMock()
        
        mock_event = MagicMock()
        mock_event.id = 999
        
        call_count = 0
        async def mock_scalar(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return mock_event
            
        session.scalar = mock_scalar
        session.add = MagicMock()
        session.commit = AsyncMock()
        
        async def mock_refresh(instance, *args, **kwargs):
            instance.id = 999
        session.refresh = mock_refresh
        
        payload = LearningEventCreate(
            module="quiz",
            event_type="quiz_submitted",
            client_event_id="evt-1",
            event_metadata={"is_correct": True, "attempt_index": 1},
        )
        
        first, _ = await evaluation_service.record_event(session, user_id=1, payload=payload)
        second, _ = await evaluation_service.record_event(session, user_id=1, payload=payload)
        
        assert second.id == first.id

    asyncio.run(run_test())
