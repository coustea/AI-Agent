from __future__ import annotations

import pytest

from app.chat.schemas import TutorTurnContext


# ── make_get_learner_profile ──


class TestMakeGetLearnerProfile:
    @pytest.mark.asyncio
    async def test_returns_profile(self):
        from app.chat.tools.user_context import make_get_learner_profile

        class FakeProfileService:
            async def build_profile_markdown(self, user_id, course_name=None, dimension=None):
                return "画像：喜欢例题驱动学习。"

        request = TutorTurnContext(user_id=42, session_id="s1")
        impl = make_get_learner_profile(request, profile_service=FakeProfileService())
        result = await impl(dimension="goal", reason="个性化辅导")
        assert "画像" in result
        assert "个性化辅导" in result

    @pytest.mark.asyncio
    async def test_exception_returns_fallback(self):
        from app.chat.tools.user_context import make_get_learner_profile

        class BrokenProfileService:
            async def build_profile_markdown(self, user_id, **kwargs):
                raise RuntimeError("db error")

        request = TutorTurnContext(user_id=1, session_id="s1")
        impl = make_get_learner_profile(request, profile_service=BrokenProfileService())
        result = await impl()
        assert "暂时无法" in result


# ── make_get_long_term_memory ──


class TestMakeGetLongTermMemory:
    @pytest.mark.asyncio
    async def test_returns_memory(self):
        from app.chat.tools.user_context import make_get_long_term_memory

        class FakeMemoryService:
            async def get_memory_markdown(self, user_id, category=None):
                return "长期记忆：目标是考研数学。"

        request = TutorTurnContext(user_id=7, session_id="s1")
        impl = make_get_long_term_memory(request, memory_service=FakeMemoryService())
        result = await impl(category="long_term_goals", reason="了解学习目标")
        assert "长期记忆" in result
        assert "考研" in result

    @pytest.mark.asyncio
    async def test_invalid_category(self):
        from app.chat.tools.user_context import make_get_long_term_memory

        request = TutorTurnContext(user_id=1, session_id="s1")
        impl = make_get_long_term_memory(request, memory_service=object())
        result = await impl(category="nonexistent_category")
        assert "无效" in result

    @pytest.mark.asyncio
    async def test_exception_returns_fallback(self):
        from app.chat.tools.user_context import make_get_long_term_memory

        class BrokenMemoryService:
            async def get_memory_markdown(self, user_id, category=None):
                raise RuntimeError("db error")

        request = TutorTurnContext(user_id=1, session_id="s1")
        impl = make_get_long_term_memory(request, memory_service=BrokenMemoryService())
        result = await impl()
        assert "暂时无法" in result

    @pytest.mark.asyncio
    async def test_empty_category_queries_all(self):
        from app.chat.tools.user_context import make_get_long_term_memory

        class FakeMemoryService:
            async def get_memory_markdown(self, user_id, category=None):
                assert category is None
                return "all memory"

        request = TutorTurnContext(user_id=1, session_id="s1")
        impl = make_get_long_term_memory(request, memory_service=FakeMemoryService())
        result = await impl(category="")
        assert "all memory" in result
