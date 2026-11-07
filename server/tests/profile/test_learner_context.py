import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import User, LearningEvent, LearningSession, WrongQuestion, UserProfile
from app.profile.context import LearnerContext, ProfileScope, load_learner_context


@pytest.mark.asyncio
async def test_learner_context_jit_loading():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        LearningEvent.__table__,
        LearningSession.__table__,
        WrongQuestion.__table__,
        UserProfile.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 1. 插入用户基础数据
        user = User(
            id=10,
            username="student_10",
            password="pwd",
            school="北京邮电大学",
            major="计算机科学与技术",
            grade="大三",
            daily_study_time="2小时",
            global_learning_goal="考研高分上岸",
            foundational_level="entry",
            learning_style="practice_first",
            content_depth="systematic_deep",
            weak_points=["红黑树", "动态规划"],
        )
        session.add(user)

        # 2. 插入错题
        wrong = WrongQuestion(
            user_id=10,
            question_id="q-101",
            subject="图论算法",
            question_type="single_choice",
            content="Dijkstra 算法的时间复杂度？",
            is_archived=False,
        )
        session.add(wrong)

        # 3. 插入测验事件
        now = datetime.now(timezone.utc)
        evt1 = LearningEvent(
            user_id=10,
            module="quiz",
            event_type="quiz_submitted",
            topic="图论算法",
            score=40.0,
            event_metadata={"is_correct": False},
            occurred_at=now - timedelta(days=2),
        )
        evt2 = LearningEvent(
            user_id=10,
            module="quiz",
            event_type="quiz_submitted",
            topic="图论算法",
            score=80.0,
            event_metadata={"is_correct": True},
            occurred_at=now - timedelta(days=1),
        )
        session.add(evt1)
        session.add(evt2)

        # 4. 插入指导策略
        up = UserProfile(
            user_id=10,
            guidance_strategy={
                "conclusion": "数据结构掌握良好，图论与动态规划需重点攻坚",
                "tutoring_style": "案例驱动",
            },
        )
        session.add(up)
        await session.commit()

        # 5. 测试 JIT 装配: Chat Scope
        chat_ctx = await load_learner_context(session, user_id=10, scope=ProfileScope.CHAT)
        assert chat_ctx.user_id == 10
        assert "红黑树" in chat_ctx.weak_topics
        assert "图论算法" in chat_ctx.weak_topics
        assert chat_ctx.recent_accuracy == 0.5

        chat_prompt = chat_ctx.to_prompt_text(ProfileScope.CHAT)
        assert "北京邮电大学" in chat_prompt
        assert "计算机科学与技术" in chat_prompt
        assert "考研高分上岸" in chat_prompt
        assert "自适应导学建议" in chat_prompt

        # 6. 测试 JIT 装配: Resource Scope (带专项主题)
        res_ctx = await load_learner_context(
            session, user_id=10, scope=ProfileScope.RESOURCE, topic="图论算法"
        )
        assert res_ctx.topic_performance["topic"] == "图论算法"
        assert res_ctx.topic_performance["question_count"] == 2
        assert res_ctx.topic_performance["accuracy"] == 0.5

        res_prompt = res_ctx.to_prompt_text(ProfileScope.RESOURCE)
        assert "图论算法" in res_prompt
        assert "掌握较薄弱" in res_prompt

        # 7. 测试 JIT 装配: Path Scope
        path_ctx = await load_learner_context(session, user_id=10, scope=ProfileScope.PATH)
        path_prompt = path_ctx.to_prompt_text(ProfileScope.PATH)
        assert "预期每日学习时长" in path_prompt
        assert "重点攻克薄弱项" in path_prompt
