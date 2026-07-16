import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel, select
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

# Imports that might fail initially
try:
    from app.evaluation.service import evaluation_service
except ImportError:
    evaluation_service = None

try:
    from app.evaluation import reporting
except ImportError:
    reporting = None

from app.infra.models import User, UserProfile, UserProfileDimension, LearningEvent, LearningSession

@pytest.fixture(name="session_setup")
def session_setup_fixture():
    async def run_setup():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Import the tables we need
        from app.infra.models import LearningAssessmentReport
        tables_to_create = [
            User.__table__,
            UserProfile.__table__,
            UserProfileDimension.__table__,
            LearningEvent.__table__,
            LearningSession.__table__,
            LearningAssessmentReport.__table__
        ]
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables_to_create))
            
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            # Create a test user
            user = User(id=1, username="test_service_user", password="pwd")
            session.add(user)
            # Create a default user profile
            profile = UserProfile(
                user_id=1,
                overall_score=85,
                scored_at=datetime.now(timezone.utc),
                guidance_strategy={},
                guidance_updated_at=None,
                last_assessment_report_id=None
            )
            session.add(profile)
            # Create a default dimension
            dim = UserProfileDimension(
                user_id=1,
                dimension_key="style",
                value="Visual",
                score=90
            )
            session.add(dim)
            await session.commit()
            yield session
            
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    generator = run_setup()
    session = loop.run_until_complete(anext(generator))
    yield session
    try:
        loop.run_until_complete(anext(generator))
    except StopAsyncIteration:
        pass
    finally:
        loop.close()

async def load_profile_snapshot(session, user_id):
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None:
        return None
    dims = (await session.exec(
        select(UserProfileDimension).where(UserProfileDimension.user_id == user_id)
    )).all()
    return {
        "guidance_strategy": profile.guidance_strategy,
        "guidance_updated_at": profile.guidance_updated_at,
        "last_assessment_report_id": profile.last_assessment_report_id,
        "overall_score": profile.overall_score,
        "scored_at": profile.scored_at,
        "dimensions": [d.model_dump() for d in dims]
    }

async def fake_markdown_and_strategy(*args, **kwargs):
    markdown = (
        "## 学习概览\n"
        "最近学习很棒！\n"
        "## 做得好的地方\n"
        "- 保持高频活跃\n"
        "## 重点复习\n"
        "- 图的遍历\n"
        "## 学习习惯\n"
        "- 喜欢在早晨学习\n"
        "## 下一步行动\n"
        "- 完成图的练习\n"
        "## 当前辅导建议\n"
        "- 建议多做可视化练习\n"
        "## 数据说明\n"
        "- 数据来自过去 7 天的学习记录\n"
    )
    strategy = {
        "version": 1,
        "focus_topics": ["图"],
        "preferred_resource_types": ["练习"],
        "recommended_session_minutes": 25,
        "weekly_goal": "完成3次图的练习",
        "tutoring_style": "思路提示",
        "reason": "图正确率较低"
    }
    return markdown, strategy

def test_ready_report_updates_only_guidance_fields(session_setup, monkeypatch):
    assert evaluation_service is not None, "evaluation_service should be defined"
    assert hasattr(evaluation_service, "generate_report"), "generate_report method should exist"
    assert reporting is not None, "reporting module should exist"
    
    async def run():
        before = await load_profile_snapshot(session_setup, 1)
        monkeypatch.setattr(reporting, "generate", fake_markdown_and_strategy)
        report = await evaluation_service.generate_report(session_setup, user_id=1, range_days=7)
        after = await load_profile_snapshot(session_setup, 1)
        
        assert report.report_markdown.startswith("## 学习概览")
        assert after["guidance_strategy"] != before["guidance_strategy"]
        assert after["overall_score"] == before["overall_score"]
        assert after["scored_at"] == before["scored_at"]
        assert after["dimensions"] == before["dimensions"]
        
    asyncio.run(run())


def test_report_failure_on_facts_aggregation(session_setup, monkeypatch):
    async def run():
        # Mock build_assessment_facts to throw exception
        from app.evaluation import facts
        def mock_build_fail(*args, **kwargs):
            raise RuntimeError("Mock facts error")
        monkeypatch.setattr(facts, "build_assessment_facts", mock_build_fail)

        with pytest.raises(RuntimeError, match="Mock facts error"):
            await evaluation_service.generate_report(session_setup, user_id=1, range_days=7)

        # Check report row
        from app.infra.models import LearningAssessmentReport
        reports = (await session_setup.exec(select(LearningAssessmentReport).where(LearningAssessmentReport.user_id == 1))).all()
        assert len(reports) == 1
        assert reports[0].status == "failed"
        assert reports[0].failure_code == "facts_aggregation_failed"

    asyncio.run(run())


def test_report_failure_on_llm_generation(session_setup, monkeypatch):
    async def run():
        # Mock reporting.generate to throw exception
        monkeypatch.setattr(reporting, "generate", fake_markdown_and_strategy)
        
        # We want to mock it specifically to fail
        def mock_generate_fail(*args, **kwargs):
            raise RuntimeError("Mock LLM error")
        monkeypatch.setattr(reporting, "generate", mock_generate_fail)

        before = await load_profile_snapshot(session_setup, 1)

        with pytest.raises(RuntimeError, match="Mock LLM error"):
            await evaluation_service.generate_report(session_setup, user_id=1, range_days=7)

        # Check report row
        from app.infra.models import LearningAssessmentReport
        reports = (await session_setup.exec(
            select(LearningAssessmentReport)
            .where(LearningAssessmentReport.user_id == 1)
            # Filter by failed because we might have other reports from previous test if session is shared
            # but wait, session_setup fixture is recreated per test, so there's only one.
        )).all()
        
        # Wait, since the first test or second test might have inserted reports, let's find the failed one
        failed_report = next((r for r in reports if r.status == "failed"), None)
        assert failed_report is not None
        assert failed_report.failure_code == "llm_generation_failed"

        # Strategy must remain untouched
        after = await load_profile_snapshot(session_setup, 1)
        assert after["guidance_strategy"] == before["guidance_strategy"]

    asyncio.run(run())

