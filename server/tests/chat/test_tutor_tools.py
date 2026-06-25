"""Tool 常量和执行逻辑测试 — 测试 nodes.py 中的工具相关功能。

测试覆盖：
  - TOOL_EVIDENCE_TYPES 常量
  - LONG_TERM_MEMORY_CATEGORY_ALIASES 别名映射
  - ToolExcute 在 chat 中的使用
"""

from __future__ import annotations

import pytest

from app.chat.schemas import TutorTurnContext
from app.infra.tool_excute import Tool, ToolExcute


# ── 工具常量测试 ──


class TestToolConstants:
    def test_evidence_types_include_core_tools(self):
        from app.chat.agent.tools import TOOL_EVIDENCE_TYPES

        # 验证核心工具的 evidence_type 映射
        assert TOOL_EVIDENCE_TYPES["get_learner_profile"] == "learner_profile"
        assert TOOL_EVIDENCE_TYPES["get_long_term_memory"] == "long_term_memory"
        assert TOOL_EVIDENCE_TYPES["search_knowledge_base"] == "knowledge_base"

    def test_evidence_types_include_web_research_tools(self):
        from app.chat.agent.tools import TOOL_EVIDENCE_TYPES, WEB_RESEARCH_TOOL_NAMES

        # 所有 web 研究工具应该映射到 "web_search"
        for name in WEB_RESEARCH_TOOL_NAMES:
            assert TOOL_EVIDENCE_TYPES.get(name) == "web_search"


# ── 长期记忆分类别名测试 ──


class TestLongTermMemoryCategoryAliases:
    def test_goals_progress_alias(self):
        from app.chat.tools.memory import LONG_TERM_MEMORY_CATEGORY_ALIASES

        assert LONG_TERM_MEMORY_CATEGORY_ALIASES["goals_progress"] == "long_term_goals"

    def test_alias_used_in_normalization(self):
        # 验证 _execute_single_tool 使用别名规范化
        from app.chat.tools.memory import LONG_TERM_MEMORY_CATEGORY_ALIASES

        category = "goals_progress"
        normalized = LONG_TERM_MEMORY_CATEGORY_ALIASES.get(category, category)
        assert normalized == "long_term_goals"


# ── ToolExcute 工具执行测试 ──


class TestToolExcuteInChat:
    @pytest.mark.asyncio
    async def test_tool_excute_executes_profile_tool(self, monkeypatch: pytest.MonkeyPatch):
        from app.chat.tools.profile import GetLearnerProfileArgs, make_get_learner_profile

        class FakeProfileService:
            async def get_profile_markdown(self, user_id: int, **_kwargs) -> str:
                assert user_id == 7
                return "画像: 喜欢先看例子"

        import app.chat.tools.profile as profile_mod
        monkeypatch.setattr(profile_mod, "get_profile_service", lambda: FakeProfileService())

        request = TutorTurnContext(user_id=7, session_id="s-1", user_input="结合我的情况讲")
        profile_handler = make_get_learner_profile(request)
        tool_excute = ToolExcute(
            model=None,
            tools=[
                Tool("get_learner_profile", "Read profile.", GetLearnerProfileArgs, profile_handler),
            ],
        )

        result = await tool_excute.execute({
            "name": "get_learner_profile",
            "args": {"dimension": "preferences"},
        })

        assert "画像读取原因" in result or "画像" in result

    @pytest.mark.asyncio
    async def test_tool_excute_executes_memory_tool(self, monkeypatch: pytest.MonkeyPatch):
        from app.chat.tools.memory import GetLongTermMemoryArgs, make_get_long_term_memory

        class FakeMemoryService:
            async def get_memory_markdown(self, user_id: int, category: str | None = None) -> str:
                assert user_id == 7
                return "长期目标: 通过阶段练习追踪进度"

        import app.chat.tools.memory as memory_mod
        monkeypatch.setattr(memory_mod, "get_chat_memory_service", lambda: FakeMemoryService())

        request = TutorTurnContext(user_id=7, session_id="s-1", user_input="看看目标进展")
        memory_handler = make_get_long_term_memory(request)
        tool_excute = ToolExcute(
            model=None,
            tools=[
                Tool("get_long_term_memory", "Read memory.", GetLongTermMemoryArgs, memory_handler),
            ],
        )

        result = await tool_excute.execute({
            "name": "get_long_term_memory",
            "args": {"category": "long_term_goals"},
        })

        assert "长期记忆读取原因" in result or "长期目标" in result


# ── 长期记忆分类测试 ──


def test_long_term_memory_categories_are_canonical() -> None:
    from app.chat.memory.types import LTM_CATEGORIES
    from app.chat.tools.memory import GetLongTermMemoryArgs

    schema = GetLongTermMemoryArgs.model_json_schema()
    category_schema = schema["properties"]["category"]
    enum_values = next(item["enum"] for item in category_schema["anyOf"] if "enum" in item)

    assert enum_values == list(LTM_CATEGORIES)