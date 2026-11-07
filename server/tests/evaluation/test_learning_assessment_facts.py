import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
# Try importing build_assessment_facts
try:
    from app.evaluation.facts import build_assessment_facts
except ImportError:
    build_assessment_facts = None

from app.infra.models import LearningEvent, LearningSession, User

@pytest.fixture(name="db_session")
def db_session_fixture():
    async def run_setup():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        tables_to_create = [User.__table__, LearningEvent.__table__, LearningSession.__table__]
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables_to_create))
            
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            # Create a test user
            user = User(id=1, username="test_facts_user", password="pwd")
            session.add(user)
            await session.commit()
            yield session
            
    # Since pytest fixture without pytest-asyncio loop scope might be tricky,
    # we can run it synchronously via asyncio loop
    loop = asyncio.get_event_loop()
    generator = run_setup()
    session = loop.run_until_complete(anext(generator))
    yield session
    try:
        loop.run_until_complete(anext(generator))
    except StopAsyncIteration:
        pass

def test_facts_use_sessions_not_event_counts_for_minutes():
    assert build_assessment_facts is not None, "build_assessment_facts should be implemented"
    
    async def run():
        # Setup window: last 7 days
        now_utc = datetime.now(timezone.utc)
        window_start = now_utc - timedelta(days=7)
        window_end = now_utc + timedelta(days=1)
        
        loop = asyncio.get_event_loop()
        # Find the fixture via custom run or use local session directly.
        # Wait, inside test we can use a local engine to avoid fixture timezone/loop issues.
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        tables_to_create = [User.__table__, LearningEvent.__table__, LearningSession.__table__]
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables_to_create))
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            # 1. Insert session with 1500 seconds (25 minutes)
            sess = LearningSession(
                user_id=1,
                source_page="resource",
                started_at=now_utc - timedelta(minutes=30),
                ended_at=now_utc - timedelta(minutes=5),
                duration_seconds=1500,
            )
            session.add(sess)
            
            # 2. Insert event (should not count towards duration_seconds)
            evt = LearningEvent(
                user_id=1,
                module="resource",
                event_type="resource_viewed",
                occurred_at=now_utc - timedelta(minutes=15),
            )
            session.add(evt)
            await session.commit()
            
            facts = await build_assessment_facts(session, user_id=1, window_start=window_start, window_end=window_end)
            assert facts["activity"]["total_minutes"] == 25
            
    asyncio.run(run())

def test_topic_is_insufficient_before_five_answers_in_two_attempts():
    assert build_assessment_facts is not None, "build_assessment_facts should be implemented"
    
    async def run():
        now_utc = datetime.now(timezone.utc)
        window_start = now_utc - timedelta(days=7)
        window_end = now_utc + timedelta(days=1)
        
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        tables_to_create = [User.__table__, LearningEvent.__table__, LearningSession.__table__]
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables_to_create))
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            # Insert 4 quiz events for topic "图", attempt_index = 1
            for i in range(4):
                evt = LearningEvent(
                    user_id=1,
                    module="quiz",
                    event_type="quiz_submitted",
                    topic="图",
                    event_metadata={"is_correct": True, "attempt_index": 1},
                    occurred_at=now_utc - timedelta(hours=i),
                )
                session.add(evt)
            await session.commit()
            
            facts = await build_assessment_facts(session, user_id=1, window_start=window_start, window_end=window_end)
            
            # Check by_topic
            by_topic = facts["practice"]["by_topic"]
            topic_fact = next((t for t in by_topic if t["topic"] == "图"), None)
            assert topic_fact is not None
            assert topic_fact["enough_evidence"] is False
            
            # Now add one more event (attempt_index = 2) to make it 5 answers in 2 attempts
            evt5 = LearningEvent(
                user_id=1,
                module="quiz",
                event_type="quiz_submitted",
                topic="图",
                event_metadata={"is_correct": False, "attempt_index": 2},
                occurred_at=now_utc,
            )
            session.add(evt5)
            await session.commit()
            
            facts2 = await build_assessment_facts(session, user_id=1, window_start=window_start, window_end=window_end)
            topic_fact2 = next((t for t in facts2["practice"]["by_topic"] if t["topic"] == "图"), None)
            assert topic_fact2["enough_evidence"] is True

    asyncio.run(run())


def test_polymorphic_learning_session_model():
    now = datetime.now(timezone.utc)
    sess = LearningSession(
        user_id=1,
        source_page="path_study",
        module="path",
        entity_id="42",
        sub_entity_id="node_99",
        started_at=now - timedelta(minutes=10),
        ended_at=now,
        duration_seconds=600,
        metadata_json={"custom_flag": "test"},
    )
    assert sess.module == "path"
    assert sess.entity_id == "42"
    assert sess.sub_entity_id == "node_99"
    assert sess.path_id == 42
    assert sess.resource_id is None

    res_sess = LearningSession(
        user_id=1,
        source_page="resource_view",
        module="resource",
        entity_id="88",
        started_at=now - timedelta(minutes=5),
        ended_at=now,
        duration_seconds=300,
    )
    assert res_sess.module == "resource"
    assert res_sess.resource_id == 88
    assert res_sess.path_id is None

